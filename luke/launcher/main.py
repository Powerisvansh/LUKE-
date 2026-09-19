"""Luke App Launcher — full-screen application drawer.
Search, categories, favorites and recent apps over the real app registry.
Launching marks the app as recently used; nothing here is fake."""

import os
import sys

sys.path.insert(0, os.path.expanduser("~/.luke/framework"))

import lukeapps
from lukeui import ensure_css
from gi.repository import Gtk, Gdk, GLib

APP_SIZE = 44


def _app_tile(app):
    btn = Gtk.Button()
    btn.get_style_context().add_class("luke-tile")
    btn.set_tooltip_text(app.desc or app.name)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.set_halign(Gtk.Align.CENTER)
    img = Gtk.Image.new_from_icon_name(app.icon_name(), Gtk.IconSize.DIALOG)
    img.set_pixel_size(APP_SIZE)
    path = app.icon_path(APP_SIZE)
    if path:
        img.set_from_file(path)
    name = Gtk.Label(label=app.name)
    name.get_style_context().add_class("luke-tile-name")
    name.set_line_wrap(True)
    name.set_justify(Gtk.Justification.CENTER)
    meta = Gtk.Label(label=app.category)
    meta.get_style_context().add_class("luke-sub")
    meta.set_ellipsize(3)
    box.pack_start(img, False, False, 0)
    box.pack_start(name, False, False, 0)
    box.pack_start(meta, False, False, 0)
    btn.add(box)
    btn.luke_app = app
    btn.connect("clicked", lambda w: _launch(w.luke_app))
    return btn


def _launch(app):
    if lukeapps.launch(app):
        Launcher.instance.hide()
    else:
        from lukeui import show_error
        show_error(Launcher.instance,
                   "The application could not be started.\n%s" % " ".join(app.exec))


class Launcher(Gtk.Window):
    instance = None

    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        Launcher.instance = self
        ensure_css()
        self.set_decorated(False)
        self.get_style_context().add_class("luke")
        self.get_style_context().add_class("launcher")
        self.fullscreen()
        self.set_title("Apps")
        self._all = lukeapps.load_apps()
        self._filter = ""

        self.search = Gtk.Entry()
        self.search.set_placeholder_text("Search applications…")
        self.search.get_style_context().add_class("launcher-search")
        self.search.set_size_request(480, -1)
        self.search.connect("changed", self._on_search)
        self.search.connect("activate", self._on_enter)

        close = Gtk.Button(label="✕")
        close.get_style_context().add_class("flat")
        close.set_tooltip_text("Close launcher (Esc)")
        close.connect("clicked", lambda _w: self.hide())

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        top.set_halign(Gtk.Align.CENTER)
        top.pack_start(self.search, False, False, 0)
        top.pack_start(close, False, False, 0)

        self.cats = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.cats.set_halign(Gtk.Align.CENTER)
        self.cat_buttons = {}

        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow.set_max_children_per_line(100)
        self.flow.set_min_children_per_line(1)
        self.flow.set_homogeneous(False)
        self.flow.set_row_spacing(4)
        self.flow.set_column_spacing(4)
        self.flow.set_valign(Gtk.Align.START)

        self.recents_label = Gtk.Label(label="")
        self.recents_label.get_style_context().add_class("launcher-section-label")
        self.recents_label.set_halign(Gtk.Align.START)
        self.favs_label = Gtk.Label(label="")
        self.favs_label.get_style_context().add_class("launcher-section-label")
        self.favs_label.set_halign(Gtk.Align.START)

        self.recents_box = Gtk.FlowBox()
        self.recents_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.recents_box.set_valign(Gtk.Align.START)
        self.recents_box.set_halign(Gtk.Align.START)
        self.favs_box = Gtk.FlowBox()
        self.favs_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.favs_box.set_valign(Gtk.Align.START)
        self.favs_box.set_halign(Gtk.Align.START)
        self._build_cats()

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        content.set_margin_start(60)
        content.set_margin_end(60)
        content.set_margin_top(54)
        content.set_margin_bottom(40)
        content.pack_start(top, False, False, 0)
        content.pack_start(self.cats, False, False, 0)
        content.pack_start(self.recents_label, False, False, 0)
        content.pack_start(self.recents_box, False, False, 0)
        content.pack_start(self.favs_label, False, False, 0)
        content.pack_start(self.favs_box, False, False, 0)
        content.pack_start(self.flow, True, True, 0)

        self.add(content)
        self.connect("key-press-event", self._on_key)
        self.refresh()

    # ---- content ----------------------------------------------------------
    def _build_cats(self):
        chips = [("All", None)] + [(c, c) for c, _ in lukeapps.categories()]
        for label, value in chips:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("luke-chip")
            btn.luke_cat = value
            btn.connect("clicked", self._pick_cat)
            self.cats.pack_start(btn, False, False, 0)
            self.cat_buttons[label] = btn
        self._pick_cat(self.cat_buttons["All"])

    def _pick_cat(self, btn):
        self._filter = btn.luke_cat or ""
        for other in self.cat_buttons.values():
            other.get_style_context().remove_class("selected")
        btn.get_style_context().add_class("selected")
        self.search.set_text("")
        self.refresh()

    def _on_search(self, _w):
        self.refresh()

    def refresh(self):
        query = self.search.get_text().strip()
        apps = lukeapps.apps(query=query or None, category=self._filter or None)
        self._fill(self.flow, apps, section=None)

        query = self.search.get_text().strip()
        if query:
            self.recents_label.set_text("")
            self.favs_label.set_text("Search results")
            for child in self.recents_box.get_children():
                self.recents_box.remove(child)
            for child in self.favs_box.get_children():
                self.favs_box.remove(child)
            self.recents_box.hide()
            self.favs_box.hide()
            if not apps:
                self.recents_label.set_text("Nothing matches “%s”" % query)
            return

        recents = lukeapps.recents()
        favs = lukeapps.favorites()
        self.recents_label.set_text("Recent" if recents else "")
        self._fill(self.recents_box, [lukeapps.get_app(i) for i in recents if lukeapps.get_app(i)], section="recents")
        self.favs_label.set_text("Favorites" if favs else "")
        self._fill(self.favs_box, [lukeapps.get_app(i) for i in favs if lukeapps.get_app(i)], section="favs")
        self.recents_box.show()
        self.favs_box.show()
        self.show_all()

    def _fill(self, flowbox, apps, section=None):
        for child in flowbox.get_children():
            flowbox.remove(child)
        for app in apps:
            flowbox.add(_app_tile(app))
        flowbox.show_all()

    # ---- keyboard ----------------------------------------------------------
    def _on_key(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape":
            self.hide()
            return True
        if key in ("Down", "Up", "Right", "Left") and self.search.has_focus():
            children = self.flow.get_children()
            if children:
                self.flow.child_focus(Gtk.DirectionType.DOWN if key in ("Down", "Right")
                                      else Gtk.DirectionType.UP)
            return True
        return False

    def _on_enter(self, _w):
        for child in self.flow.get_children():
            tile = child.get_child() if child.get_child() else None
            if tile is not None and getattr(tile, "luke_app", None):
                _launch(tile.luke_app)
                return

    def show_launcher(self):
        self.refresh()
        self.search.set_text("")
        self.set_opacity(0.0)
        self.show_all()
        self.fullscreen()
        self.present()
        GLib.timeout_add(150, lambda: self.search.grab_focus())
        GLib.timeout_add(16, self._step_fade)

    def hide(self):
        Gtk.Window.hide(self)
        GLib.idle_add(Gtk.main_quit)

    def _step_fade(self):
        opaque = self.get_opacity() + 0.10
        self.set_opacity(min(1.0, opaque))
        return opaque < 1.0


def main():
    win = Launcher()
    win.show_launcher()
    Gtk.main()


if __name__ == "__main__":
    main()