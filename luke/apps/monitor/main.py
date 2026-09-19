"""Luke System Monitor — reads real data from /proc and /proc/mounts."""

import os
from lukeui import LukeWindow, start, show_error
from gi.repository import Gtk, GLib

INTERVAL_MS = 1500


def _cpu_jiffies(line):
    parts = [int(x) for x in line.split()[1:]]
    if len(parts) < 4:
        return 0, 0
    idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
    total = sum(parts[:7])
    return idle, total


def read_cpu():
    """Return (overall_usage, [per_core_usage]) needing one prior sample."""
    overall = None
    cores = []
    with open("/proc/stat") as fh:
        for line in fh:
            if line.startswith("cpu "):
                overall = _cpu_jiffies(line)
            elif line.startswith("cpu") and line[3].isdigit():
                cores.append(_cpu_jiffies(line))
    return overall, cores


def read_mem():
    info = {}
    with open("/proc/meminfo") as fh:
        for line in fh:
            for key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
                if line.startswith(key + ":"):
                    info[key] = int(line.split()[1]) * 1024
    return info


def read_load():
    with open("/proc/loadavg") as fh:
        parts = fh.read().split()
    return tuple(float(x) for x in parts[:3]), parts[-2], parts[-1]


def read_uptime():
    with open("/proc/uptime") as fh:
        secs = int(float(fh.read().split()[0]))
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    bits = []
    if d:
        bits.append("%dd" % d)
    bits.append("%dh" % h)
    bits.append("%dm" % m)
    return " ".join(bits)


def disks():
    result = []
    with open("/proc/mounts") as fh:
        for line in fh:
            fields = line.split()
            if len(fields) < 3:
                continue
            src, mnt = fields[0], fields[1]
            if not src.startswith("/dev/"):
                continue
            if mnt.startswith(("/proc", "/sys", "/dev", "/run", "/snap")):
                continue
            try:
                st = os.statvfs(mnt)
            except OSError:
                continue
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            result.append((mnt, total, free))
    return result


class Monitor(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "System Monitor", width=760, height=520)
        self._prev = None
        self._last_load = "—", "—"

        self.cpu_bar = self._bar()
        self.cpu_label = Gtk.Label(label="…", xalign=1)
        self.cpu_label.get_style_context().add_class("luke-sub")
        self.core_bars = []

        self.mem_bar = self._bar()
        self.mem_label = Gtk.Label(label="…", xalign=1)
        self.mem_label.get_style_context().add_class("luke-sub")

        self.swap_bar = self._bar()
        self.swap_label = Gtk.Label(label="…", xalign=1)
        self.swap_label.get_style_context().add_class("luke-sub")

        self.load_label = Gtk.Label(label="…")
        self.uptime_label = Gtk.Label(label="…")
        self.disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main.set_margin_top(18)
        main.set_margin_bottom(18)
        main.set_margin_start(22)
        main.set_margin_end(22)

        main.pack_start(self._card(
            "Processor", self.cpu_bar, self.cpu_label,
            "All cores"), False, False, 0)
        main.pack_start(self._card("Memory", self.mem_bar, self.mem_label, "RAM"), False, False, 0)
        main.pack_start(self._card("Swap", self.swap_bar, self.swap_label, "swap"), False, False, 0)
        main.pack_start(self._card("Storage", None, None, "filesystems", body=self.disk_box), False, False, 0)

        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        load_title = Gtk.Label(label="Load average  ")
        load_title.get_style_context().add_class("luke-sub")
        foot.pack_start(load_title, False, False, 0)
        foot.pack_start(self.load_label, False, False, 0)
        uptime_title = Gtk.Label(label="Uptime  ")
        uptime_title.get_style_context().add_class("luke-sub")
        foot.pack_start(uptime_title, False, False, 0)
        foot.pack_start(self.uptime_label, False, False, 0)
        main.pack_start(foot, False, False, 0)

        self.core_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        main.pack_start(self.core_box, True, True, 0)

        self.body.pack_start(main, True, True, 0)

        cores = self._core_count()
        for _ in range(cores):
            bar = self._bar()
            self.core_bars.append(bar)
        self._refresh()
        GLib.timeout_add(INTERVAL_MS, self._refresh)

    @staticmethod
    def _core_count():
        try:
            with open("/proc/stat") as fh:
                return sum(1 for l in fh if l.startswith("cpu") and l[3].isdigit())
        except OSError:
            return 1

    def _bar(self):
        bar = Gtk.ProgressBar()
        bar.set_show_text(False)
        return bar

    def _card(self, title, bar, label, unit, body=None):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.get_style_context().add_class("luke-card")
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        box.set_margin_start(12)
        box.set_margin_end(12)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(14)
        inner.set_margin_end(14)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        t = Gtk.Label(label=title, xalign=0)
        t.get_style_context().add_class("luke-card-title")
        inner.pack_start(t, False, False, 0)
        if bar is not None:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.pack_start(bar, True, True, 0)
            if label is not None:
                row.pack_start(label, False, False, 0)
            inner.pack_start(row, False, False, 0)
        if body is not None:
            inner.pack_start(body, True, True, 0)
        box.pack_start(inner, True, True, 0)
        return box

    def _refresh(self):
        overall, cores = read_cpu()
        mem = read_mem()
        load, running, last_pid = read_load()

        if self._prev is not None:
            prev_o, prev_c = self._prev
            use = self._usage(prev_o, overall)
            self.cpu_bar.set_fraction(use / 100.0)
            if use > 85:
                self.cpu_bar.get_style_context().add_class("red")
                self.cpu_bar.get_style_context().remove_class("yellow")
            elif use > 60:
                self.cpu_bar.get_style_context().add_class("yellow")
                self.cpu_bar.get_style_context().remove_class("red")
            self.cpu_label.set_text("%.0f%%" % use)
            for i, (pb, cc) in enumerate(zip(self.core_bars, cores)):
                if i < len(prev_c):
                    pb.set_fraction(self._usage(prev_c[i], cc) / 100.0)
            if "MemTotal" in mem and "MemAvailable" in mem:
                tot, av = mem["MemTotal"], mem["MemAvailable"]
                frac = (tot - av) / tot
                self.mem_bar.set_fraction(frac)
                used_mb = (tot - av) / 1048576
                tot_mb = tot / 1048576
                self.mem_label.set_text("%.0f / %.0f MB" % (used_mb, tot_mb))
            if "SwapTotal" in mem and mem["SwapTotal"]:
                frac = (mem["SwapTotal"] - mem["SwapFree"]) / mem["SwapTotal"]
                self.swap_bar.set_fraction(frac)
                self.swap_label.set_text("%.0f / %.0f MB" % (
                    (mem["SwapTotal"] - mem["SwapFree"]) / 1048576,
                    mem["SwapTotal"] / 1048576))
            else:
                self.swap_bar.set_fraction(0)
                self.swap_label.set_text("no swap")
        self._prev = (overall, cores)

        self.load_label.set_text("%s  (running: %s)" % (", ".join("%.2f" % x for x in load), running))
        self.uptime_label.set_text(read_uptime())

        for child in self.disk_box.get_children():
            self.disk_box.remove(child)
        for path, total, free in disks():
            used = total - free
            frac = used / total if total else 0
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            name = Gtk.Label(label=path, xalign=0)
            name.set_hexpand(True)
            bar = self._bar()
            bar.set_fraction(frac)
            pct = Gtk.Label(label="%.0f%%" % (frac * 100))
            detail = Gtk.Label(
                label="%.1fG of %.1fG free" % (free / (1 << 30), total / (1 << 30)),
                xalign=1)
            detail.get_style_context().add_class("luke-sub")
            row.pack_start(name, False, False, 0)
            row.pack_start(bar, True, True, 0)
            row.pack_start(pct, False, False, 0)
            row.pack_start(detail, False, False, 0)
            self.disk_box.pack_start(row, False, False, 0)
        if not self.disk_box.get_children():
            note = Gtk.Label(label="No block devices found", xalign=0)
            note.get_style_context().add_class("luke-sub")
            self.disk_box.pack_start(note, False, False, 0)
        self.disk_box.show_all()
        return True

    @staticmethod
    def _usage(prev, curr):
        p_idle, p_tot = prev
        c_idle, c_tot = curr
        d_total = c_tot - p_tot
        if d_total <= 0:
            return 0.0
        return max(0.0, min(100.0, (d_total - (c_idle - p_idle)) * 100.0 / d_total))


if __name__ == "__main__":
    start(Monitor)