"""Luke — About: real system information from the running OS."""

import os
import platform
import socket

from lukeui import LukeWindow, start
import lukeassets
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib


def os_release(path="/etc/os-release"):
    data = {}
    try:
        with open(path) as fh:
            for line in fh:
                if "=" in line:
                    k, _, v = line.partition("=")
                    data[k.strip()] = v.strip().strip('"')
    except OSError:
        pass
    return data


def cpu_info():
    model, cores = "Unknown", 1
    try:
        with open("/proc/cpuinfo") as fh:
            names = [l.split(":", 1)[1].strip() for l in fh if l.startswith("model name")]
        if names:
            model = names[0]
            cores = len(names)
    except OSError:
        pass
    return model, cores


def mem_total_mb():
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except OSError:
        pass
    return 0


def disk_summary():
    best = None
    for mnt in ("/", "/home", "/media/aman/LUKE-DATA"):
        try:
            st = os.statvfs(mnt)
        except OSError:
            continue
        best = (mnt, st.f_blocks * st.f_frsize, st.f_bavail * st.f_frsize)
        break
    if best is None:
        return "unknown"
    path, total, free = best
    return "%.1fG free of %.1fG (%s)" % (free / (1 << 30), total / (1 << 30), path)


def brand_image(size=96):
    path = lukeassets.brand_mark() or lukeassets.wordmark()
    if not path:
        return Gtk.Label(label="L")
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
        return Gtk.Image.new_from_pixbuf(pb)
    except GLib.Error:
        return Gtk.Label(label="L")


class About(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "About Luke", width=520, height=360, resizable=False)

        rel = os_release()
        name = rel.get("PRETTY_NAME") or "Luke"
        version = rel.get("VERSION") or rel.get("VERSION_ID", "1.0")
        kernel = platform.release()
        arch = platform.machine()
        model, cores = cpu_info()

        img = brand_image(96)
        img.set_margin_top(20)

        title = Gtk.Label(label=name, xalign=0)
        title.get_style_context().add_class("luke-title")
        title.set_margin_top(6)

        sub = Gtk.Label(label="Version %s  ·  %s  ·  %s" % (version, arch, socket.gethostname()), xalign=0)
        sub.get_style_context().add_class("luke-sub")

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("luke-card")
        card.set_margin_start(20)
        card.set_margin_end(20)
        card.set_margin_top(10)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        inner.set_margin_start(14)
        inner.set_margin_end(14)
        inner.set_margin_top(14)
        inner.set_margin_bottom(14)

        with open("/proc/uptime") as fh:
            up = int(float(fh.read().split()[0]))
        d, rem = divmod(up, 86400)
        h, m = divmod(rem, 3600)
        uptime = "%d h %d m" % (h, m // 60)
        if d:
            uptime = "%d d " % d + uptime

        rows = [
            ("Operating system", name),
            ("Version", version),
            ("Kernel", kernel),
            ("Processor", model),
            ("Cores", "%d" % cores),
            ("Memory", "%d MB" % mem_total_mb()),
            ("Storage", disk_summary()),
            ("Hostname", socket.gethostname()),
            ("Uptime", uptime),
        ]
        for key, value in rows:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            k = Gtk.Label(label=key, xalign=0)
            k.get_style_context().add_class("luke-sub")
            k.set_size_request(140, -1)
            v = Gtk.Label(label=value, xalign=0)
            v.set_line_wrap(True)
            box.pack_start(k, False, False, 0)
            box.pack_start(v, True, True, 0)
            inner.pack_start(box, False, False, 0)
        card.pack_start(inner, True, True, 0)

        btn_copy = Gtk.Button(label="Copy system info")
        btn_copy.connect("clicked", lambda _w: self._copy(rows, name))

        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        foot.set_margin_start(20)
        foot.set_margin_end(20)
        foot.set_margin_top(12)
        foot.set_margin_bottom(16)
        foot.pack_end(btn_copy, False, False, 0)

        col = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        col.set_margin_start(20)
        col.set_margin_top(16)
        col.pack_start(img, False, False, 0)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left.pack_start(title, False, False, 0)
        left.pack_start(sub, False, False, 0)
        col.pack_start(left, True, True, 0)

        self.body.pack_start(col, False, False, 0)
        self.body.pack_start(card, True, True, 0)
        self.body.pack_start(foot, False, False, 0)

    def _copy(self, rows, name):
        text = "\n".join("%s: %s" % (k, v) for k, v in rows)
        text = "%s\n%s" % (name, text)
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(text, -1)
        self.title_label.set_text("About Luke — copied to clipboard")


if __name__ == "__main__":
    start(About)