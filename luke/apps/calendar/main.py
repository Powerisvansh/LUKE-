"""Luke — Calendar: month grid with navigation and a today summary."""

import calendar as _cal
from datetime import datetime
from lukeui import LukeWindow, start
from gi.repository import Gtk

WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


class Calendar(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Calendar", width=560, height=520)
        self._y = datetime.now().year
        self._m = datetime.now().month

        self.head_label = Gtk.Label(label="", xalign=0)
        self.head_label.get_style_context().add_class("luke-title")

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prev = Gtk.Button(label="←")
        next_ = Gtk.Button(label="→")
        today = Gtk.Button(label="Today")
        prev.connect("clicked", self._move, -1)
        next_.connect("clicked", self._move, 1)
        today.connect("clicked", self._nudge)
        nav.pack_start(prev, False, False, 0)
        nav.pack_start(next_, False, False, 0)
        nav.pack_start(today, False, False, 0)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        head.pack_start(self.head_label, True, True, 0)
        head.pack_start(nav, False, False, 0)

        self.grid = Gtk.Grid()
        self.grid.set_row_spacing(6)
        self.grid.set_column_spacing(8)
        self.grid.set_hexpand(True)

        self.sel_date_label = Gtk.Label(label="", xalign=0)
        self.sel_date_label.get_style_context().add_class("luke-sub")
        self.sel_count_label = Gtk.Label(label="", xalign=0)
        self.sel_count_label.get_style_context().add_class("luke-sub")

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        info.get_style_context().add_class("luke-card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        inner.set_margin_top(14)
        inner.set_margin_bottom(14)
        info_title = Gtk.Label(label="Today", xalign=0)
        info_title.get_style_context().add_class("luke-card-title")
        inner.pack_start(info_title, False, False, 0)
        inner.pack_start(self.sel_date_label, False, False, 0)
        inner.pack_start(self.sel_count_label, False, False, 0)
        info.pack_start(inner, True, True, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.get_style_context().add_class("luke-card")

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main.set_margin_start(24)
        main.set_margin_end(24)
        main.set_margin_top(18)
        main.set_margin_bottom(18)

        grad = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        grad.set_margin_start(16)
        grad.set_margin_end(16)
        grad.set_margin_top(12)
        grad.set_margin_bottom(12)
        grad.pack_start(self.grid, True, True, 0)
        grad.pack_start(info, False, False, 0)
        card.pack_start(grad, True, True, 0)

        main.pack_start(head, False, False, 0)
        main.pack_start(card, True, True, 0)
        self.body.pack_start(main, True, True, 0)

        self._draw()

    def _nudge(self, _w):
        self._y = datetime.now().year
        self._m = datetime.now().month
        self._draw()

    def _move(self, _w, delta):
        self._m += delta
        if self._m < 1:
            self._m, self._y = 12, self._y - 1
        elif self._m > 12:
            self._m, self._y = 1, self._y + 1
        self._draw()

    def _draw(self):
        for child in self.grid.get_children():
            self.grid.remove(child)
        self.head_label.set_text(datetime(self._y, self._m, 1).strftime("%B %Y"))

        for col, name in enumerate(WEEKDAYS):
            lbl = Gtk.Label(label=name)
            lbl.get_style_context().add_class("luke-sub")
            self.grid.attach(lbl, col, 0, 1, 1)

        today = datetime.now().date()
        cal = _cal.Calendar()
        row = 1
        for week in cal.monthdatescalendar(self._y, self._m):
            for col, d in enumerate(week):
                cell = Gtk.Button(label=str(d.day))
                cell.get_style_context().add_class("cal-cell")
                if d.month != self._m:
                    cell.get_style_context().add_class("cal-other")
                if d == today:
                    cell.get_style_context().add_class("cal-today")
                    cell.set_tooltip_text("Today")
                cell.set_border_width(0)
                self.grid.attach(cell, col, row, 1, 1)
            row += 1

        self.sel_date_label.set_text(today.strftime("%A, %d %B, %Y"))
        days = self._days_in()
        self.sel_count_label.set_text("%d days in %s — today is day %d" % (
            days, datetime(self._y, self._m, 1).strftime("%B %Y"), today.day))
        self.grid.show_all()

    def _days_in(self):
        return _cal.monthrange(self._y, self._m)[1]


if __name__ == "__main__":
    start(Calendar)