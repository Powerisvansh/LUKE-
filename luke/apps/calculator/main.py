"""Luke Calculator — GTK front end for calc_core."""
from lukeui import LukeWindow, start
import calc_core
from gi.repository import Gtk, Gdk


class Calculator(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Calculator", width=340, height=500, resizable=False)
        self.expr = ""
        self.history = ""

        self.entry = Gtk.Entry()
        self.entry.set_editable(False)
        self.entry.set_alignment(1.0)
        self.entry.get_style_context().add_class("luke-big")
        self.entry.set_margin_top(10)
        self.entry.set_margin_bottom(0)
        self.entry.set_margin_start(12)
        self.entry.set_margin_end(12)

        self.status = Gtk.Label(label="")
        self.status.set_xalign(1.0)
        self.status.get_style_context().add_class("luke-sub")
        self.status.set_margin_start(12)
        self.status.set_margin_end(12)
        self.status.set_margin_bottom(4)

        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.set_halign(Gtk.Align.FILL)

        rows = [
            (0, 0, "C"), (0, 1, "("), (0, 2, ")"), (0, 3, "⌫"),
            (1, 0, "7"), (1, 1, "8"), (1, 2, "9"), (1, 3, "÷"),
            (2, 0, "4"), (2, 1, "5"), (2, 2, "6"), (2, 3, "×"),
            (3, 0, "1"), (3, 1, "2"), (3, 2, "3"), (3, 3, "−"),
            (4, 0, "±"), (4, 1, "0"), (4, 2, "."), (4, 3, "+"),
            (5, 0, "√"), (5, 1, "x²"), (5, 2, "%"), (5, 3, "="),
        ]
        for r, c, label in rows:
            grid.attach(self._button(label), c, r, 1, 1)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(self.entry, False, False, 0)
        box.pack_start(self.status, False, False, 0)
        box.pack_start(grid, True, True, 10)
        self.body.pack_start(box, True, True, 0)
        self.connect("key-press-event", self._on_key)
        self.entry.set_text("0")
        self._refresh()

    def _button(self, label):
        btn = Gtk.Button(label=label)
        btn.set_can_focus(False)
        if label in ("÷", "×", "−", "+"):
            btn.get_style_context().add_class("flat")
        elif label == "=":
            btn.get_style_context().add_class("suggested-action")
        elif label == "C":
            btn.get_style_context().add_class("destructive-action")
        btn.set_hexpand(True)
        btn.set_size_request(-1, 46)
        btn.connect("clicked", lambda _w: self._press(label))
        return btn

    def _press(self, key):
        if key == "C":
            self.expr = ""
            self.history = ""
        elif key == "⌫":
            self.expr = self.expr[:-1]
        elif key == "=":
            self._eval()
        elif key == "√":
            self._eval(sqrt=True)
        elif key == "x²":
            self._eval(square=True)
        elif key == "±":
            self.expr = calc_core.negate_trailing(self.expr)
        else:
            mapping = {"×": "*", "÷": "/", "−": "-"}
            self.expr += mapping.get(key, key)
        if self.expr == "":
            self.expr = "0"
        self._refresh()

    def _eval(self, sqrt=False, square=False):
        raw = self.expr
        try:
            result = float(calc_core.evaluate(raw if raw not in ("", "0") else "0"))
            if sqrt:
                result = result ** 0.5
            elif square:
                result = result * result
            self.history = "%s =" % raw
            self.expr = calc_core._fmt(result)
            self.status.set_text("")
        except ValueError as err:
            self.status.set_text(str(err))
            if not sqrt and not square:
                self.expr = raw
        self._refresh()

    def _refresh(self):
        self.entry.set_text(self.expr)
        if self.history:
            self.status.set_text("%s  →  %s" % (self.history, self.expr))

    def _on_key(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        keys = {
            "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
            "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
            "period": ".", "comma": ".", "KP_0": "0",
            "plus": "+", "minus": "-", "asterisk": "*",
            "slash": "/", "equal": "=", "Return": "=",
            "KP_Enter": "=", "BackSpace": "⌫", "Escape": "C",
            "parenleft": "(", "parenright": ")",
        }
        if key == "x":
            self._press("×")
            return True
        if key in keys:
            self._press(keys[key])
            return True
        return False


if __name__ == "__main__":
    start(Calculator)