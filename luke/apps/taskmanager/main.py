"""Luke Task Manager — live list of real processes from /proc."""

import os
import pwd
import re
import signal
import time
from lukeui import LukeWindow, start, show_error
from gi.repository import Gtk, GLib

INTERVAL_MS = 1500
CLOCK_TICKS = 100.0


def _stat_fields(pid):
    try:
        with open("/proc/%d/stat" % pid) as fh:
            raw = fh.read()
    except OSError:
        return None
    name, _, rest = raw.rpartition(")")
    parts = rest.split()
    if len(parts) < 15:
        return None
    comm = name.split(" ", 1)[-1] if " " in name else name
    state = parts[0]
    utime = int(parts[11])
    stime = int(parts[12])
    ppid = int(parts[1]) if len(parts) > 1 else -1
    return {
        "pid": pid, "comm": comm[:32], "state": state, "ppid": ppid,
        "utime": utime, "stime": stime,
    }


def _username(pid):
    try:
        with open("/proc/%d/status" % pid) as fh:
            for line in fh:
                if line.startswith("Uid:"):
                    uid = int(line.split()[1])
                    try:
                        return pwd.getpwuid(uid).pw_name
                    except KeyError:
                        return str(uid)
    except (OSError, ValueError, IndexError):
        pass
    return "?"


def _rss_mb(pid):
    try:
        with open("/proc/%d/status" % pid) as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def _pids():
    out = []
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            out.append(int(entry))
    return out


class TaskManager(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Task Manager", width=780, height=540)
        self._prev = {}
        self._prev_time = time.monotonic()

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Search processes…")
        self.search.connect("search-changed", self._on_search)

        self.count_label = Gtk.Label(label="")
        self.count_label.get_style_context().add_class("luke-sub")

        btn_kill = Gtk.Button(label="End Task")
        btn_kill.get_style_context().add_class("destructive-action")
        btn_kill.connect("clicked", self._on_kill)
        btn_refresh = Gtk.Button(label="Refresh")
        btn_refresh.connect("clicked", lambda _w: self._refresh())

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top.set_margin_top(14)
        top.set_margin_bottom(4)
        top.set_margin_start(18)
        top.set_margin_end(18)
        top.pack_start(self.search, True, True, 0)
        top.pack_start(btn_refresh, False, False, 0)
        top.pack_start(btn_kill, False, False, 0)

        self.store = Gtk.ListStore(int, str, str, int, float)
        self.store.set_sort_column_id(3, Gtk.SortType.DESCENDING)

        self.filter = self.store.filter_new()
        self.filter.set_visible_func(self._visible)

        self.view = Gtk.TreeView(model=self.filter)
        self.view.set_headers_clickable(True)
        cols = [
            ("PID", 0, 60),
            ("Name", 1, 220),
            ("User", 2, 90),
            ("CPU %", 3, 70),
            ("Mem (MB)", 4, 90),
        ]
        for title, idx, width in cols:
            col = Gtk.TreeViewColumn(title)
            renderer = Gtk.CellRendererText()
            col.pack_start(renderer, True)
            col.add_attribute(renderer, "text", idx)
            col.set_min_width(width)
            col.set_sort_column_id(idx)
            self.view.append_column(col)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.view)

        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        foot.set_margin_start(18)
        foot.set_margin_end(18)
        foot.set_margin_top(6)
        foot.set_margin_bottom(12)
        foot.pack_start(self.count_label, False, False, 0)

        self.body.pack_start(top, False, False, 0)
        self.body.pack_start(scroller, True, True, 0)
        self.body.pack_start(foot, False, False, 0)

        self.count_label.set_text("Loading…")
        self._refresh()
        GLib.timeout_add(INTERVAL_MS, self._refresh)

    def _visible(self, model, it, _data):
        if not self.search.get_text().strip():
            return True
        return self.search.get_text().lower() in model.get_value(it, 1).lower()

    def _on_search(self, _w):
        self.filter.refilter()

    def _refresh(self):
        now = time.monotonic()
        dt = max(0.2, now - self._prev_time)
        snap = {}
        rows = []
        for pid in _pids():
            info = _stat_fields(pid)
            if info is None:
                continue
            snap[pid] = (info["utime"], info["stime"])
            prev = self._prev.get(pid)
            if prev is not None and prev != (0, 0):
                cpu = max(0.0, ((info["utime"] + info["stime"]) - sum(prev)) / dt)
            else:
                cpu = 0.0
            rows.append((pid, info["comm"], _username(pid),
                         int(round(min(cpu, 999.0))), _rss_mb(pid)))
        self._prev = snap
        self._prev_time = now

        rows.sort(key=lambda r: r[3], reverse=True)
        self.store.clear()
        for pid, comm, user, cpu, rss in rows:
            self.store.append([pid, comm, user, cpu, rss])
        self.count_label.set_text(
            "Processes: %d   CPU sorted, updating every 1.5s" % len(rows))
        return True

    def _on_kill(self, _w):
        path, _col = self.view.get_cursor()
        if path is None:
            return
        model_it = self.filter.get_iter(path)
        if model_it is None:
            return
        pid = self.filter.get_value(model_it, 0)
        name = self.filter.get_value(model_it, 1)

        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text="End the task %s (PID %d)?" % (name, pid))
        dlg.format_secondary_text(
            "The process will be asked to shut down cleanly.")
        resp = dlg.run()
        dlg.destroy()
        if resp != Gtk.ResponseType.YES:
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            show_error(self, "The process has already finished.")
        except PermissionError:
            show_error(self, "Ending this task needs more permissions.\nUse the terminal: sudo kill %d" % pid)


if __name__ == "__main__":
    start(TaskManager)