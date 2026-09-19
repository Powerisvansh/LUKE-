"""Luke — Clock: live clock plus a working stopwatch."""

import time
from datetime import datetime
from lukeui import LukeWindow, start
from gi.repository import Gtk, GLib

TICK_MS = 200


class Clock(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Clock", width=620, height=460)

        self._running = False
        self._stamp = 0.0
        self._elapsed = 0.0
        self._lap_base = 0.0
        self._laps = []

        self.time_label = Gtk.Label(label="--:--")
        self.time_label.get_style_context().add_class("luke-big")
        self.time_label.set_size_request(0, 70)

        self.date_label = Gtk.Label(label="")
        self.date_label.get_style_context().add_class("luke-sub")

        clock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        clock_box.get_style_context().add_class("luke-card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_start(20)
        inner.set_margin_end(20)
        inner.set_margin_top(26)
        inner.set_margin_bottom(22)
        inner.pack_start(self.time_label, True, True, 0)
        inner.pack_start(self.date_label, False, False, 0)
        clock_box.pack_start(inner, True, True, 0)

        stop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        stop.get_style_context().add_class("luke-card")

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        t = Gtk.Label(label="Stopwatch", xalign=0)
        t.get_style_context().add_class("luke-card-title")
        head.pack_start(t, True, True, 0)
        self.stop_label = Gtk.Label(label="00:00.0", xalign=1)
        self.stop_label.get_style_context().add_class("mono")
        head.pack_start(self.stop_label, True, True, 0)

        rows = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.btn_start = Gtk.Button(label="Start")
        self.btn_start.connect("clicked", self._on_start)
        self.btn_lap = Gtk.Button(label="Lap")
        self.btn_lap.set_sensitive(False)
        self.btn_lap.connect("clicked", self._on_lap)
        self.btn_reset = Gtk.Button(label="Reset")
        self.btn_reset.set_sensitive(False)
        self.btn_reset.connect("clicked", self._on_reset)
        rows.pack_start(self.btn_start, True, True, 0)
        rows.pack_start(self.btn_lap, True, True, 0)
        rows.pack_start(self.btn_reset, True, True, 0)

        self.lap_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.get_style_context().add_class("luke-card")
        scroll.add(self.lap_list)

        stop_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        stop_inner.set_margin_start(14)
        stop_inner.set_margin_end(14)
        stop_inner.set_margin_top(14)
        stop_inner.set_margin_bottom(14)
        stop_inner.pack_start(head, False, False, 0)
        stop_inner.pack_start(rows, False, False, 0)
        stop.pack_start(stop_inner, False, False, 0)
        stop.pack_start(scroll, True, True, 0)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main.set_margin_start(22)
        main.set_margin_end(22)
        main.set_margin_top(18)
        main.set_margin_bottom(18)
        main.pack_start(clock_box, True, True, 0)
        main.pack_start(stop, True, True, 0)

        self.body.pack_start(main, True, True, 0)

        self._update()
        GLib.timeout_add(TICK_MS, self._tick)

    def _tick(self):
        if self._running:
            self._elapsed = self._stamp + (time.time() - self._lap_base)
        self._update()
        return True

    def _update(self):
        now = datetime.now()
        self.time_label.set_text(now.strftime("%H:%M"))
        self.date_label.set_text(now.strftime("%A, %d %B %Y"))
        self.stop_label.set_text(self._fmt(self._elapsed))

    @staticmethod
    def _fmt(secs):
        m, s = divmod(int(secs * 10), 600)
        return "%02d:%02d.%d" % (m, s // 10, s % 10)

    def _on_start(self, _w):
        if self._running:
            self._running = False
            self._stamp = self._elapsed
            self.btn_start.set_label("Start")
            self.btn_lap.set_sensitive(False)
        else:
            self._running = True
            self._lap_base = time.time()
            self._stamp = self._elapsed
            self.btn_start.set_label("Stop")
            self.btn_lap.set_sensitive(True)
            self.btn_reset.set_sensitive(True)

    def _on_lap(self, _w):
        self._laps.append(self._elapsed)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        n = Gtk.Label(label="Lap %d" % len(self._laps), xalign=0)
        t = Gtk.Label(label=self._fmt(self._elapsed), xalign=1)
        t.get_style_context().add_class("mono")
        row.pack_start(n, True, True, 0)
        row.pack_start(t, True, True, 0)
        self.lap_list.pack_start(row, False, False, 0)
        self.lap_list.show_all()

    def _on_reset(self, _w):
        self._running = False
        self._stamp = 0.0
        self._elapsed = 0.0
        self._laps = []
        self.btn_start.set_label("Start")
        self.btn_lap.set_sensitive(False)
        self.btn_reset.set_sensitive(False)
        for child in self.lap_list.get_children():
            self.lap_list.remove(child)
        self.stop_label.set_text("00:00.0")


if __name__ == "__main__":
    start(Clock)