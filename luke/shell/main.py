"""LukeShell — the fullscreen home surface of the Luke operating system.

A single, always-available window with:
  * a header: brand, live clock, network / volume / battery status
  * a home view: greeting, launcher entry, favourites and recents
  * a launcher overlay: search + categories + the full app grid
  * a quick-settings sheet: Wi-Fi, volume, brightness, battery, power
  * a dock of favourites and controls

Every control is real: launching goes through the registry, Wi-Fi through
nmcli, volume through pactl, brightness through xrandr, power through
systemd-logind. The shell sinks below fullscreen apps (keep-below) and is
recalled with Super/Home or the dock.

Runs user-level from ~/.luke; no root required.
"""

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.expanduser("~/.luke/framework"))

from lukepaths import ROOT, p  # noqa: E402
import lukeassets  # noqa: E402
import lukeapps  # noqa: E402
from lukeui import ensure_css, show_error  # noqa: E402

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf  # noqa: E402

STATE = p("state")
SOCK = os.path.join(STATE, "lukeshell.sock")
MODES = ("home", "launcher", "quick")


def run(args):
    try:
        return subprocess.run(
            args, capture_output=True, text=True, timeout=4).stdout
    except Exception:
        return ""


class ShellWindow(Gtk.Window):
    def __init__(self, mode="home"):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.get_style_context().add_class("luke")
        self.get_style_context().add_class("shell")
        self.set_decorated(False)
        self.fullscreen()
        self.set_title("Luke")
        self._apps = lukeapps.load_apps()
        self._wm_sink = True
        self._toast_timer = 0
        self._hide_timer = 0
        self._cat = ""

        try:
            os.makedirs(STATE, exist_ok=True)
        except OSError:
            pass

        overlay = Gtk.Overlay()

        self.backdrop = Gtk.DrawingArea()
        self.backdrop.connect("draw", self._draw_bg)
        overlay.add(self.backdrop)

        self.home = self._build_home()
        overlay.add_overlay(self.home)

        self.launcher_ov = self._build_launcher()
        self.launcher_ov.set_visible(False)
        self.launcher_ov._fade_timer = 0
        overlay.add_overlay(self.launcher_ov)

        self.quick_ov = self._build_quick()
        self.quick_ov.set_visible(False)
        self.quick_ov._fade_timer = 0
        overlay.add_overlay(self.quick_ov)

        self.toast = Gtk.Label(label="")
        self.toast.get_style_context().add_class("shell-toast")
        self.toast.set_halign(Gtk.Align.CENTER)
        self.toast.set_valign(Gtk.Align.END)
        self.toast.set_margin_bottom(96)
        self.toast.set_no_show_all(True)
        overlay.add_overlay(self.toast)

        self.add(overlay)
        self._all = overlay  # keep a handle

        self._refresh_status()
        GLib.timeout_add(1000, self._tick)
        GLib.timeout_add(5000, self._refresh_status)

        self.connect("key-press-event", self._on_key)
        self.connect("focus-in-event", self._on_focus_in)
        self.connect("focus-out-event", self._on_focus_out)
        self.connect("destroy", Gtk.main_quit)

        self.set_keep_below(True)

        if mode == "launcher":
            self.show_launcher()
        elif mode == "quick":
            self.show_quick()

    # ------------------------------------------------------------- building
    def _hdr(self, label, size="h3"):
        lbl = Gtk.Label(label=label, xalign=0)
        lbl.get_style_context().add_class("sec-label-" + size)
        return lbl

    def _section_label(self, text, icon=None):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_halign(Gtk.Align.START)
        title = Gtk.Label(label=text, xalign=0)
        title.get_style_context().add_class("sec-label-h2")
        box.pack_start(title, False, False, 0)
        return box

    def _build_home(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.get_style_context().add_class("home")

        # ---- header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.set_margin_start(28)
        header.set_margin_end(28)
        header.set_margin_top(20)
        header.get_style_context().add_class("shell-statusbar")

        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mark = Gtk.Image()
        mpath = lukeassets.brand_mark()
        if os.path.exists(mpath):
            try:
                mark.set_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_size(mpath, 26, 26))
                mark.set_size_request(26, 26)
            except GLib.Error:
                mark = Gtk.Label(label="L")
                mark.get_style_context().add_class("wordmark")
        brand.pack_start(mark, False, False, 0)
        word = Gtk.Label()
        word.set_markup('<span letter_spacing="2400">LUKE</span>')
        word.get_style_context().add_class("wordmark")
        brand.pack_start(word, False, False, 0)
        header.pack_start(brand, False, False, 0)

        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        status.set_halign(Gtk.Align.END)

        self.wifi_btn = self._status_button(
            "network-wireless", "Wi-Fi", lambda _w: self._toggle_wifi())
        self.vol_btn = self._status_button(
            "audio-volume-high", "Volume", lambda _w: self.show_quick())
        self.bat_btn = self._status_button(
            "battery-good", "Battery", lambda _w: self.show_quick())
        self.tm_label = Gtk.Label(label="")
        self.tm_label.get_style_context().add_class("clock-label")
        self.dt_label = Gtk.Label(label="")
        self.dt_label.get_style_context().add_class("date-label")
        time_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        time_box.set_halign(Gtk.Align.END)
        time_box.pack_end(self.tm_label, False, False, 0)
        time_box.pack_end(self.dt_label, False, False, 0)

        status.pack_end(time_box, False, False, 0)
        status.pack_end(self.bat_btn, False, False, 0)
        status.pack_end(self.vol_btn, False, False, 0)
        status.pack_end(self.wifi_btn, False, False, 0)
        header.pack_end(status, False, False, 0)
        root.pack_start(header, False, False, 0)

        # ---- centre content
        mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        mid.set_halign(Gtk.Align.CENTER)
        mid.set_valign(Gtk.Align.CENTER)
        mid.get_style_context().add_class("home-mid")

        self.greet_label = Gtk.Label(label="")
        self.greet_label.get_style_context().add_class("greet-label")
        mid.pack_start(self.greet_label, False, False, 0)

        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        entry_row.set_margin_top(18)
        entry_row.set_margin_bottom(6)
        self.launch_entry = Gtk.Entry()
        self.launch_entry.set_placeholder_text("Search applications…")
        self.launch_entry.set_size_request(470, -1)
        self.launch_entry.get_style_context().add_class("launcher-entry")
        self.launch_entry.connect("focus-in-event", lambda *_a: self.show_launcher())
        self.launch_entry.connect("activate", self._entry_enter)
        go_btn = Gtk.Button(label="Apps")
        go_btn.get_style_context().add_class("suggested-action")
        go_btn.connect("clicked", lambda _w: self.show_launcher())
        entry_row.pack_start(self.launch_entry, False, False, 0)
        entry_row.pack_start(go_btn, False, False, 0)
        mid.pack_start(entry_row, False, False, 0)

        favs_lbl = self._section_label("Favorites")
        favs_lbl.set_margin_top(30)
        self.favs_box = Gtk.FlowBox()
        self.favs_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.favs_box.set_homogeneous(False)
        self.favs_box.set_row_spacing(0)
        self.favs_box.set_column_spacing(0)
        mid.pack_start(favs_lbl, False, False, 0)
        mid.pack_start(self.favs_box, False, False, 0)

        rec_lbl = self._section_label("Recent")
        rec_lbl.set_margin_top(22)
        self.rec_box = Gtk.FlowBox()
        self.rec_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.rec_box.set_homogeneous(False)
        self.rec_box.set_row_spacing(0)
        self.rec_box.set_column_spacing(0)
        mid.pack_start(rec_lbl, False, False, 0)
        mid.pack_start(self.rec_box, False, False, 0)

        self.blank_footer = Gtk.Label(label=" ")
        self.blank_footer.set_margin_top(26)
        mid.pack_start(self.blank_footer, False, False, 0)
        root.pack_start(mid, True, True, 0)

        # ---- dock
        dock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dock.set_halign(Gtk.Align.CENTER)
        dock.set_margin_bottom(18)
        dock.get_style_context().add_class("shell-dock")
        self.dock_box = Gtk.FlowBox()
        self.dock_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.dock_box.set_homogeneous(False)
        self.dock_box.set_max_children_per_line(20)
        self.dock_box.set_row_spacing(0)
        self.dock_box.set_column_spacing(2)
        dock.pack_start(self.dock_box, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(10)
        sep.set_margin_end(10)
        dock.pack_start(sep, False, False, 0)

        launcher_btn = self._status_button(
            "view-app-grid-symbolic", "All apps", lambda _w: self.show_launcher())
        launcher_btn.get_style_context().add_class("dock-ctrl")
        quick_btn = self._status_button(
            "preferences-system-symbolic", "Quick settings",
            lambda _w: self.show_quick())
        quick_btn.get_style_context().add_class("dock-ctrl")
        power_btn = self._status_button(
            "system-shutdown-symbolic", "Power", lambda _w: self.show_quick())
        power_btn.get_style_context().add_class("dock-ctrl")
        dock.pack_start(launcher_btn, False, False, 0)
        dock.pack_start(quick_btn, False, False, 0)
        dock.pack_start(power_btn, False, False, 0)
        root.pack_end(dock, False, False, 0)

        self._fill_dock()
        self._fill_home_rows()
        return root

    def _status_button(self, icon_name, tip, handler):
        btn = Gtk.Button()
        btn.set_tooltip_text(tip)
        try:
            img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            btn.set_image(img)
        except Exception:
            btn.set_label("•")
        btn.get_style_context().add_class("status-btn")
        btn.connect("clicked", handler)
        return btn

    def _build_launcher(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.get_style_context().add_class("launcher-surface")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top.set_halign(Gtk.Align.CENTER)
        top.set_margin_top(34)
        self.search = Gtk.Entry()
        self.search.set_placeholder_text("Search applications…")
        self.search.set_size_request(460, -1)
        self.search.get_style_context().add_class("launcher-search")
        self.search.connect("changed", lambda _w: self._refresh_launcher())
        self.search.connect("activate", self._launcher_enter)
        close = Gtk.Button(label="Close")
        close.get_style_context().add_class("chip")
        close.connect("clicked", lambda _w: self.hide_launcher())
        top.pack_start(self.search, False, False, 0)
        top.pack_start(close, False, False, 0)
        box.pack_start(top, False, False, 0)

        self.cats = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.cats.set_halign(Gtk.Align.CENTER)
        self.cats.set_margin_top(16)
        self.cat_buttons = {}
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow.set_max_children_per_line(100)
        self.flow.set_homogeneous(True)
        self.flow.set_min_children_per_line(8)
        self.flow.set_row_spacing(6)
        self.flow.set_column_spacing(6)
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_halign(Gtk.Align.CENTER)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.flow)
        box.pack_start(self.cats, False, False, 0)
        box.pack_start(sw, True, True, 0)

        self._build_cats()
        self._pick_cat(self.cat_buttons["All"])
        self._refresh_launcher()
        return box

    def _build_quick(self):
        sheet = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        sheet.get_style_context().add_class("quick-sheet")
        sheet.set_size_request(320, -1)
        sheet.set_halign(Gtk.Align.END)
        sheet.set_margin_start(18)
        sheet.set_margin_end(18)
        sheet.set_margin_top(90)
        sheet.set_margin_bottom(20)

        head = self._section_label("Quick Settings")
        sheet.pack_start(head, False, False, 0)

        # Wi-Fi
        wifi_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.wifi_sw = Gtk.Switch()
        self.wifi_sw.set_active(self._wifi_radio())
        self.wifi_sw.connect("notify::active", self._on_wifi_toggle)
        self.ssid_label = Gtk.Label(label="")
        self.ssid_label.get_style_context().add_class("dim")
        wifi_row.pack_start(Gtk.Label(label="Wi-Fi"), False, False, 0)
        wifi_row.pack_start(self.ssid_label, True, True, 0)
        wifi_row.pack_end(self.wifi_sw, False, False, 0)
        sheet.pack_start(wifi_row, False, False, 0)

        # Volume
        sheet.pack_start(self._slider_row(
            "Volume", self._get_volume_pct, self._set_volume), False, False, 0)

        # Brightness
        sheet.pack_start(self._slider_row(
            "Brightness", self._get_brightness, self._set_brightness),
            False, False, 0)

        # Battery
        bat_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.bat_label = Gtk.Label(label="")
        self.bat_lvl = Gtk.LevelBar()
        self.bat_lvl.set_min_value(0)
        self.bat_lvl.set_max_value(100)
        self.bat_lvl.set_size_request(120, -1)
        bat_row.pack_start(Gtk.Label(label="Battery"), False, False, 0)
        bat_row.pack_end(self.bat_label, False, False, 0)
        bat_row.pack_end(self.bat_lvl, False, False, 0)
        sheet.pack_start(bat_row, False, False, 0)

        sep = Gtk.Separator()
        sheet.pack_start(sep, False, False, 0)

        # Power row
        pw = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lock = Gtk.Button(label="Lock")
        lock.connect("clicked", lambda _w: self._power("lock"))
        restart = Gtk.Button(label="Restart")
        restart.connect("clicked", lambda _w: self._power("restart"))
        shutdown = Gtk.Button(label="Shut Down")
        shutdown.connect("clicked", lambda _w: self._power("shutdown"))
        pw.pack_start(lock, True, True, 0)
        pw.pack_start(restart, True, True, 0)
        pw.pack_start(shutdown, True, True, 0)
        sheet.pack_end(pw, False, False, 0)

        self._tick_status()
        return sheet

    def _slider_row(self, label, getter, setter):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        scale.set_range(0, 100)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_size_request(200, -1)
        scale.set_value(getter() * 100)
        scale.connect("value-changed", lambda s: setter(s.get_value() / 100.0))
        box.pack_start(Gtk.Label(label=label), False, False, 0)
        box.pack_end(scale, True, True, 0)
        return box

    # ------------------------------------------------------- home / tiles
    def _tile(self, app, compact=False):
        btn = Gtk.Button()
        btn.get_style_context().add_class("shell-tile")
        if compact:
            btn.set_size_request(58, 58)
        btn.set_tooltip_text(app.desc or app.name)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_halign(Gtk.Align.CENTER)
        img = Gtk.Image()
        path = app.icon_path(40 if compact else 56)
        if path:
            img.set_from_file(path)
        else:
            img.set_from_icon_name(app.icon_name(), Gtk.IconSize.DIALOG)
            img.set_pixel_size(40 if compact else 56)
        box.pack_start(img, False, False, 0)
        if not compact:
            name = Gtk.Label(label=app.name)
            name.get_style_context().add_class("tile-name")
            box.pack_start(name, False, False, 0)
        btn.add(box)
        btn.luke_app = app
        btn.connect("clicked", self._launch)
        return btn

    def _launch(self, btn):
        app = btn.luke_app
        if lukeapps.launch(app):
            self._toast(app.name)
            GLib.idle_add(self._sink)
        elif app.id == "quicksettings":
            self.show_quick()
        else:
            show_error(self, "The application could not be started.\n%s"
                       % " ".join(app.exec))

    def _fill_dock(self):
        for child in self.dock_box.get_children():
            self.dock_box.remove(child)
        for fav in lukeapps.favorites():
            app = lukeapps.get_app(fav)
            if app:
                self.dock_box.add(self._tile(app, compact=True))
        self.dock_box.show_all()

    def _fill_home_rows(self):
        for child in self.favs_box.get_children():
            self.favs_box.remove(child)
        for child in self.rec_box.get_children():
            self.rec_box.remove(child)
        for fav in lukeapps.favorites():
            app = lukeapps.get_app(fav)
            if app:
                self.favs_box.add(self._tile(app))
        for rid in lukeapps.recents():
            app = lukeapps.get_app(rid)
            if app and app.id not in lukeapps.favorites():
                self.rec_box.add(self._tile(app))

    # ---------------------------------------------------------- launcher
    def _build_cats(self):
        chips = [("All", None)] + [(c, c) for c, _ in lukeapps.categories()]
        for label, value in chips:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("chip")
            btn.luke_cat = value
            btn.connect("clicked", self._pick_cat)
            self.cats.pack_start(btn, False, False, 0)
            self.cat_buttons[label] = btn

    def _pick_cat(self, btn):
        self._cat = btn.luke_cat or ""
        for other in self.cat_buttons.values():
            other.get_style_context().remove_class("checked")
        btn.get_style_context().add_class("checked")
        self._refresh_launcher()

    def _refresh_launcher(self):
        query = self.search.get_text().strip()
        for child in self.flow.get_children():
            self.flow.remove(child)
        for app in lukeapps.apps(query=query or None, category=self._cat or None):
            self.flow.add(self._launcher_tile(app))
        self.flow.show_all()

    def _launcher_tile(self, app):
        btn = Gtk.Button()
        btn.get_style_context().add_class("luke-tile")
        btn.set_tooltip_text(app.desc or app.name)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_halign(Gtk.Align.CENTER)
        img = Gtk.Image()
        path = app.icon_path(40)
        if path:
            img.set_from_file(path)
        else:
            img.set_from_icon_name(app.icon_name(), Gtk.IconSize.DIALOG)
            img.set_pixel_size(40)
        name = Gtk.Label(label=app.name)
        name.get_style_context().add_class("tile-name")
        box.pack_start(img, False, False, 0)
        box.pack_start(name, False, False, 0)
        btn.add(box)
        btn.luke_app = app
        btn.connect("clicked", self._launch)
        return btn

    def show_launcher(self):
        self._raise_shell()
        self.hide_quick(instant=True)
        self.search.set_text("")
        self._cat = ""
        for other in self.cat_buttons.values():
            other.get_style_context().remove_class("checked")
        self.cat_buttons["All"].get_style_context().add_class("checked")
        self._refresh_launcher()
        self._fade(self.launcher_ov, True)
        GLib.timeout_add(240, lambda: self.search.grab_focus())

    def hide_launcher(self, instant=False):
        if instant:
            self.launcher_ov.set_visible(False)
        else:
            self._fade(self.launcher_ov, False)
        GLib.timeout_add(200, self.launch_entry.grab_focus)

    def toggle_launcher(self):
        if self.launcher_ov.get_visible():
            self.hide_launcher()
        else:
            self.show_launcher()

    def _launcher_enter(self, _w):
        for child in self.flow.get_children():
            tile = child.get_child()
            if tile is not None and getattr(tile, "luke_app", None):
                self._launch(tile)
                return

    def _entry_enter(self, _w):
        self.show_launcher()

    # -------------------------------------------------------- quick panel
    def show_quick(self):
        self._raise_shell()
        self.hide_launcher(instant=True)
        self._tick_status()
        self._fade(self.quick_ov, True)

    def hide_quick(self, instant=False):
        if instant:
            self.quick_ov.set_visible(False)
        else:
            self._fade(self.quick_ov, False)

    def toggle_quick(self):
        if self.quick_ov.get_visible():
            self.hide_quick()
        else:
            self.show_quick()

    def _fade(self, widget, show):
        """Show/hide an overlay with a short opacity fade."""
        if widget._fade_timer:
            GLib.source_remove(widget._fade_timer)
            widget._fade_timer = 0
        if show:
            widget.set_opacity(0.0)
            widget.show()
            widget._fade_dir = 1
        else:
            widget._fade_dir = -1
        widget._fade_timer = GLib.timeout_add(16, self._fade_step, widget)
        return False

    def _fade_step(self, widget):
        op = widget.get_opacity() + 0.1 * widget._fade_dir
        if op >= 1.0:
            widget.set_opacity(1.0)
            widget._fade_timer = 0
            return False
        if op <= 0.0:
            widget.hide()
            widget._fade_timer = 0
            return False
        widget.set_opacity(op)
        return True

    # ------------------------------------------------------- real actions
    def _wifi_radio(self):
        out = run(["nmcli", "radio", "wifi"])
        return out.strip().lower().startswith("enabled")

    def _wifi_ssid(self):
        out = run(["nmcli", "-t", "-f", "IN-USE,SSID", "dev", "wifi"])
        for ln in out.splitlines():
            used, _, ssid = ln.partition(":")
            if used == "*":
                return ssid
        return None

    def _set_wifi(self, on):
        run(["nmcli", "radio", "wifi", "on" if on else "off"])

    def _on_wifi_toggle(self, _s, _p):
        self._set_wifi(self.wifi_sw.get_active())
        self._tick_status()

    def _get_volume_pct(self):
        out = run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        m = re.search(r"(\d+)%", out)
        return (int(m.group(1)) / 100.0) if m else 0.5

    def _set_volume(self, v):
        pct = int(round(v * 100))
        run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "%d%%" % pct])

    def _output_name(self):
        for ln in run(["xrandr", "--query"]).splitlines():
            if " connected" in ln:
                return ln.split()[0]
        return None

    def _get_brightness(self):
        out = run(["xrandr", "--verbose"])
        m = re.search(r"Brightness:\s*([0-9.]+)", out)
        return float(m.group(1)) if m else 0.6

    def _set_brightness(self, v):
        name = self._output_name()
        if name:
            run(["xrandr", "--output", name, "--brightness", "%.2f" % v])

    def _battery(self):
        for base in ("BAT0", "BAT1", "BAT2"):
            cap = os.path.join("/sys/class/power_supply", base, "capacity")
            if os.path.exists(cap):
                try:
                    level = int(open(cap).read().strip())
                except (OSError, ValueError):
                    level = 0
                return level
        return None

    def _icon_battery(self, level):
        if level is None:
            return "battery-missing"
        if level >= 90:
            return "battery-full"
        if level >= 60:
            return "battery-good"
        if level >= 35:
            return "battery-caution"
        return "battery-empty"

    def _on_wifi(self):
        self._set_wifi(self.wifi_sw.get_active())
        self._tick_status()

    def _power(self, action):
        self.hide_quick()
        if action == "lock":
            run(["loginctl", "lock-session"])
            return
        obj = "org.freedesktop.login1.Manager"
        calls = {"restart": "Reboot", "shutdown": "PowerOff"}
        method = calls.get(action, "PowerOff")
        if shutil.which("dbus-send"):
            subprocess.Popen([
                "dbus-send", "--system", "--print-reply",
                "--dest=org.freedesktop.login1", "/org/freedesktop/login1",
                obj + "." + method, "boolean:true"])
        else:
            subprocess.Popen(["systemctl", action])

    # --------------------------------------------------------------- ticks
    def _tick(self):
        now = time.localtime()
        self.tm_label.set_text(time.strftime("%H:%M", now))
        hr = now.tm_hour
        if 5 <= hr < 12:
            greet = "Good morning"
        elif 12 <= hr < 18:
            greet = "Good afternoon"
        else:
            greet = "Good evening"
        self.greet_label.set_text(greet)
        self.dt_label.set_text(time.strftime("%A · %d %B", now))
        return True

    def _tick_status(self):
        try:
            self.wifi_sw.set_active(self._wifi_radio())
            ssid = self._wifi_ssid()
            self.ssid_label.set_text(ssid or ("Scanning…" if self.wifi_sw.get_active() else "Off"))
        except Exception:
            pass
        try:
            self.wifi_btn.set_image(Gtk.Image.new_from_icon_name(
                "network-wireless" if self.wifi_sw.get_active() else "network-offline",
                Gtk.IconSize.MENU))
        except Exception:
            pass
        try:
            level = self._battery()
            if level is not None:
                self.bat_btn.set_image(Gtk.Image.new_from_icon_name(
                    self._icon_battery(level), Gtk.IconSize.MENU))
                self.bat_label.set_text("%d%%" % level)
                self.bat_lvl.set_value(level)
                self.bat_btn.set_visible(True)
            else:
                self.bat_btn.set_visible(False)
                self.bat_label.set_text("—")
        except Exception:
            pass
        try:
            vol = self._get_volume_pct()
            self.vol_btn.set_image(Gtk.Image.new_from_icon_name(
                "audio-volume-high" if vol > 0.02 else "audio-volume-muted",
                Gtk.IconSize.MENU))
        except Exception:
            pass

    def _refresh_status(self):
        self._tick()
        self._tick_status()
        return True

    # -------------------------------------------------------------- chrome
    def _draw_bg(self, _w, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        try:
            cr.set_source_rgb(0.031, 0.049, 0.075)
            cr.rectangle(0, 0, w, h)
            cr.fill()
            cr.set_source_rgba(0.20, 0.62, 0.56, 0.10)
            cr.arc(w * 0.85, h * 0.12, h * 0.5, 0, 6.2832)
            cr.fill()
            cr.set_source_rgba(0.36, 0.22, 0.78, 0.08)
            cr.arc(w * 0.10, h * 0.95, h * 0.45, 0, 6.2832)
            cr.fill()
        except Exception:
            pass
        return False

    def _toast(self, text):
        self.toast.set_text(text)
        self.toast.show()
        if self._toast_timer:
            GLib.source_remove(self._toast_timer)
        self._toast_timer = GLib.timeout_add(2000, self._hide_toast)

    def _hide_toast(self):
        self.toast.hide()
        self._toast_timer = 0
        return False

    def _raise_shell(self):
        self.set_keep_below(False)
        self.present()

    def _sink(self):
        self.set_keep_below(True)

    def _on_focus_in(self, *_a):
        self.set_keep_below(False)
        return False

    def _on_focus_out(self, *_a):
        if not (self.launcher_ov.get_visible()
                or self.quick_ov.get_visible()):
            self.set_keep_below(True)
        return False

    def _on_key(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        if key in ("Super_L", "Super_R"):
            self.toggle_launcher()
            return True
        if key == "Escape":
            if self.launcher_ov.get_visible():
                self.hide_launcher()
            elif self.quick_ov.get_visible():
                self.hide_quick()
            return True
        if key in ("Down", "Up", "Right", "Left") and self.search.has_focus():
            children = self.flow.get_children()
            if children:
                self.flow.child_focus(
                    Gtk.DirectionType.DOWN if key in ("Down", "Right")
                    else Gtk.DirectionType.UP)
            return True
        return False


# ------------------------------------------------------------------ IPC
def ipc_server(window):
    """Listen for commands from luke-home / luke-launcher on a unix socket."""

    def _dispatch(msg):
        msg = msg.strip()
        if msg == "home":
            window._raise_shell()
            window.hide_launcher()
            window.hide_quick()
        elif msg == "launcher":
            window.show_launcher()
        elif msg == "quick":
            window.show_quick()
        return False

    def _loop():
        try:
            os.unlink(SOCK)
        except OSError:
            pass
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(SOCK)
        except OSError:
            return
        sock.listen(4)
        while True:
            try:
                conn, _ = sock.accept()
                data = conn.recv(64).decode("utf-8", "replace")
                conn.close()
                if data:
                    GLib.idle_add(_dispatch, data)
            except OSError:
                break
        sock.close()

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in MODES else "home"
    ensure_css()
    win = ShellWindow(mode)
    ipc_server(win)
    win.show_all()
    win.set_keep_below(True)
    GLib.timeout_add(1200, lambda: (win.present(), False)[1])
    Gtk.main()


if __name__ == "__main__":
    main()