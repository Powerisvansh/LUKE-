"""Luke UI framework: the single design system all apps and the shell share.

Original, reimplemented for the Luke OS rebuild. Components render through
GTK3 + the luke.css design tokens. Glyphs are drawn on DrawingAreas from the
`cr` passed by GTK, so no python-cairo module is required on the target.
"""

import os
import subprocess

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from lukepaths import ROOT

ASSETS = os.path.join(ROOT, "design", "assets")
PROVIDER_PRIORITY = Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION


class _Css:
    loaded = False


def ensure_css():
    if _Css.loaded:
        return True
    candidates = [
        os.path.join(ROOT, "framework", "luke.css"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "luke.css"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                css = Gtk.CssProvider()
                css.load_from_path(path)
                screen = Gdk.Screen.get_default()
                if screen is not None:
                    Gtk.StyleContext.add_provider_for_screen(screen, css,
                                                             PROVIDER_PRIORITY)
                    _Css.loaded = True
                    return True
            except GLib.Error:
                return False
    return False


def set_dark():
    s = Gtk.Settings.get_default()
    if s is not None:
        s.set_property("gtk-application-prefer-dark-theme", True)
        s.set_property("gtk-cursor-theme-name", "Adwaita")
        s.set_property("gtk-icon-theme-name", "Papirus-Dark")
        s.set_property("gtk-font-name", "Noto Sans 10")


def asset(path):
    return os.path.join(ASSETS, *path.split("/"))


def load_surface(name, size=96):
    p = asset(f"icons/{name}-{size}.png")
    if not os.path.exists(p):
        p = asset(f"icons/app-{size}.png")
    try:
        pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(p, size, size, True)
        return Gtk.Image.new_from_pixbuf(pb)
    except GLib.Error:
        return Gtk.Image.new_from_icon_name("application-x-executable",
                                            Gtk.IconSize.MENU)


class Glyph(Gtk.DrawingArea):
    """Draws a vector glyph from a callback using GTK's cr. No cairo import."""

    def __init__(self, draw, data=None, size=22):
        Gtk.DrawingArea.__init__(self)
        self._draw = draw
        self._data = data
        self.set_size_request(size, size)
        self.connect("draw", self._render)
        self.set_can_focus(False)

    def _render(self, _w, cr):
        s = min(self.get_allocated_width(), self.get_allocated_height())
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cr.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cr.OPERATOR_OVER)
        self._draw(cr, s, self._data)


def _stroke(cr, x0, y0, x1, y1, width, s):
    cr.set_source_rgba(0.918, 0.941, 0.973, 0.92)
    cr.set_line_width(width)
    cr.set_line_cap(cr.LINE_CAP_ROUND)
    cr.move_to(x0, y0)
    cr.line_to(x1, y1)
    cr.stroke()


def glyph_min(cr, s, _d):
    _stroke(cr, s * 0.25, s * 0.5, s * 0.75, s * 0.5, s * 0.1, s)


def glyph_max(cr, s, _d):
    m = s * 0.26
    r = s * 0.76 - m
    cr.set_source_rgba(0.918, 0.941, 0.973, 0.92)
    cr.set_line_width(s * 0.1)
    cr.set_line_cap(cr.LINE_CAP_SQUARE)
    cr.rectangle(m, m, r, r)
    cr.stroke()


def glyph_close(cr, s, _d):
    _stroke(cr, s * 0.28, s * 0.28, s * 0.72, s * 0.72, s * 0.1, s)
    _stroke(cr, s * 0.72, s * 0.28, s * 0.28, s * 0.72, s * 0.1, s)


def glyph_back(cr, s, _d):
    _stroke(cr, s * 0.62, s * 0.2, s * 0.3, s * 0.5, s * 0.1, s)
    _stroke(cr, s * 0.3, s * 0.5, s * 0.62, s * 0.8, s * 0.1, s)


class LukeWindow(Gtk.Window):
    """Original CSD application window with a shared header design."""

    def __init__(self, title="Luke", subtitle=None, width=920, height=600,
                 resizable=True, icon=None):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        ensure_css()
        set_dark()
        self.set_title(title)
        self.set_default_size(width, height)
        if not resizable:
            self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        try:
            p = asset("brand/luke-mark-512.png")
            if os.path.exists(p):
                self.set_icon_from_file(p)
        except GLib.Error:
            pass

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.get_style_context().add_class("luke-root")
        self.add(root)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(False)
        hb.set_decoration_layout("")
        hb.props.custom_title = self._title_box(title, subtitle)
        hb.connect("button-press-event", self._drag_press)
        root.pack_start(hb, False, False, 0)

        for glyph, name in ((glyph_min, "min"), (glyph_max, "max"),
                            (glyph_close, "close")):
            b = Gtk.Button()
            b.add(Glyph(glyph, size=18))
            b.get_style_context().add_class(name)
            if name == "close":
                b.get_style_context().add_class("close")
                b.connect("clicked", lambda _w: self.destroy())
            elif name == "min":
                b.connect("clicked", lambda _w: self.iconify())
            else:
                b.connect("clicked", self._on_maximize)
            hb.pack_end(b, False, False, 0)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.pack_start(self.body, True, True, 0)
        self.body.set_margin_top(6)

    def _title_box(self, title, subtitle):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_halign(Gtk.Align.START)
        lab = Gtk.Label(label=title or "Luke")
        lab.get_style_context().add_class("title")
        lab.set_halign(Gtk.Align.START)
        box.pack_start(lab, False, False, 0)
        if subtitle:
            sub = Gtk.Label(label=subtitle)
            sub.get_style_context().add_class("subtitle")
            sub.set_halign(Gtk.Align.START)
            box.pack_start(sub, False, False, 0)
        return box

    def _drag_press(self, _w, ev):
        if ev.button == 1:
            self.begin_move_drag(1, int(ev.x_root), int(ev.y_root), ev.time)
            return True
        return False

    def _on_maximize(self, _w):
        if self.get_window() is None:
            return
        if self.is_maximized():
            self.unmaximize()
        else:
            self.maximize()


def show_error(parent, message, title="Something went wrong"):
    dlg = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dlg.format_secondary_text(message)
    dlg.run()
    dlg.destroy()


def run_default_background(cmd):
    """Start a detached process, ignoring failure quietly."""
    try:
        subprocess.Popen(cmd, start_new_session=True)
    except OSError:
        pass


def start(window_class, *args, **kwargs):
    ensure_css()
    win = window_class(*args, **kwargs)
    win.show_all()
    Gtk.main()