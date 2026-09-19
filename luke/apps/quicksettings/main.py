"""Luke Quick Settings — a small overlay with real, live controls.
Volume + mute (pactl), Wi-Fi on/off and current network (nmcli),
screen brightness (xrandr), dark/bright theme (xfconf), and
Restart / Shut Down (systemctl through logind).

It opens just below the top-right of the screen, hides on Esc or when
it loses focus, and exits when hidden (no lingering process).
Every control changes a real system value or says it cannot."""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.expanduser("~/.luke/framework"))

from lukeui import ensure_css
from gi.repository import Gtk, Gdk, GLib

PANEL_GAP = 30


def sh(cmd, timeout=10):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip(), proc.returncode
    except Exception as err:
        return str(err), -1


def volume():
    """(level, muted) for the default sink, or None when pactl is absent."""
    out, code = sh(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    if code != 0:
        return None
    levels = [int(m) for m in re.findall(r"(\d+)%", out)]
    muted, _ = sh(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
    return (levels[-1] if levels else 100, muted.startswith("yes"))


def wifi_on():
    out, code = sh(["nmcli", "radio", "wifi"])
    return code == 0 and out.startswith("enabled")


def wifi_ssid():
    out, code = sh(["nmcli", "-g", "NAME", "connection", "show", "--active"])
    if code != 0:
        return None
    return next((ln for ln in out.splitlines() if ln.strip()), None)


def active_output():
    out, code = sh(["xrandr", "--current"])
    if code != 0:
        return None
    name = None
    for line in out.splitlines():
        if " connected " in line:
            name = line.split()[0]
        elif name and "*" in line:
            return name
    return name


def current_brightness(output):
    out, code = sh(["xrandr", "--verbose"])
    if code != 0:
        return None
    here = None
    for line in out.splitlines():
        if " connected " in line:
            here = line.split()[0] == output
        elif here and "Brightness:" in line:
            try:
                return float(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def theme_lists():
    dark, bright = [], []
    try:
        for name in os.listdir("/usr/share/themes"):
            if os.path.isdir(os.path.join("/usr/share/themes", name)):
                (dark if "dark" in name.lower() else bright).append(name)
    except OSError:
        pass
    return sorted(dark), sorted(bright)


def current_theme():
    out, code = sh(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName"])
    return out.splitlines()[0].strip() if code == 0 and out else ""


def power(action):
    subprocess.Popen(["systemctl", "-i",
                      "poweroff" if action == "off" else "reboot"],
                     start_new_session=True)


class QuickSettings(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        ensure_css()
        self.set_decorated(False)
        self.set_title("Quick Settings")
        self.set_resizable(False)
        self.set_default_size(300, -1)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.get_style_context().add_class("quick")

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        panel.get_style_context().add_class("quick-panel")
        panel.set_margin_start(18)
        panel.set_margin_end(18)
        panel.set_margin_top(16)
        panel.set_margin_bottom(16)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="Quick Settings", xalign=0)
        title.get_style_context().add_class("luke-title")
        close = Gtk.Button(label="✕")
        close.get_style_context().add_class("flat")
        close.connect("clicked", lambda _w: self.hide())
        head.pack_start(title, True, True, 0)
        head.pack_end(close, False, False, 0)
        panel.pack_start(head, False, False, 0)

        for row in (self._row_wifi(), self._row_volume(),
                    self._row_brightness(), self._row_theme(),
                    self._row_power()):
            panel.pack_start(row, False, False, 0)

        self.add(panel)
        self.connect("key-press-event", self._on_key)
        self.connect("focus-out-event", lambda _w, _e: self.hide())
        self.refresh()

    def popup(self):
        self.show_all()
        self.present()
        scr = Gdk.Screen.get_default()
        geo = scr.get_monitor_geometry(scr.get_primary_monitor())
        w = self.get_allocation().width
        self.move(geo.x + geo.width - w - 10, geo.y + PANEL_GAP)

    def hide(self):
        Gtk.Window.hide(self)
        GLib.idle_add(Gtk.main_quit)

    def _on_key(self, _w, event):
        if Gdk.keyval_name(event.keyval) == "Escape":
            self.hide()
            return True
        return False

    # ---- rows ------------------------------------------------------------
    def _row_wifi(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label="Wi-Fi", xalign=0)
        label.set_hexpand(True)
        self.wifi_detail = Gtk.Label(label="")
        self.wifi_detail.get_style_context().add_class("luke-sub")
        self.wifi_detail.set_ellipsize(1)
        self.wifi_switch = Gtk.Switch()
        self.wifi_switch.connect("notify::active", self._toggle_wifi)
        row.pack_start(label, True, True, 0)
        row.pack_start(self.wifi_detail, False, False, 0)
        row.pack_start(self.wifi_switch, False, False, 0)
        return row

    def _row_volume(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label="Volume", xalign=0)
        label.set_hexpand(True)
        self.vol_pct = Gtk.Label(label="")
        self.vol_pct.get_style_context().add_class("luke-sub")
        head.pack_start(label, True, True, 0)
        head.pack_end(self.vol_pct, False, False, 0)
        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 150, 5)
        self.slider.set_draw_value(False)
        self.slider.set_size_request(220, -1)
        self.slider.connect("value-changed", self._vol_changed)
        self.mute = Gtk.CheckButton(label="Mute")
        self.mute.connect("toggled", self._mute_changed)
        self.vol_note = Gtk.Label(label="", xalign=0)
        self.vol_note.get_style_context().add_class("luke-sub")
        box.pack_start(head, False, False, 0)
        box.pack_start(self.slider, False, False, 0)
        box.pack_start(self.mute, False, False, 0)
        box.pack_start(self.vol_note, False, False, 0)
        return box

    def _row_brightness(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label="Brightness", xalign=0)
        label.set_hexpand(True)
        self.bri_pct = Gtk.Label(label="")
        self.bri_pct.get_style_context().add_class("luke-sub")
        head.pack_start(label, True, True, 0)
        head.pack_end(self.bri_pct, False, False, 0)
        self.bri = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 30, 100, 5)
        self.bri.set_draw_value(False)
        self.bri.set_size_request(220, -1)
        self.bri.connect("value-changed", self._bri_changed)
        self.bri_note = Gtk.Label(label="", xalign=0)
        self.bri_note.get_style_context().add_class("luke-sub")
        box.pack_start(head, False, False, 0)
        box.pack_start(self.bri, False, False, 0)
        box.pack_start(self.bri_note, False, False, 0)
        return box

    def _row_theme(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label = Gtk.Label(label="Dark theme", xalign=0)
        label.set_hexpand(True)
        self.dark = Gtk.CheckButton()
        self.dark.connect("toggled", self._theme_changed)
        row.pack_start(label, True, True, 0)
        row.pack_start(self.dark, False, False, 0)
        return row

    def _row_power(self):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        restart = Gtk.Button(label="Restart")
        poweroff = Gtk.Button(label="Shut Down")
        poweroff.get_style_context().add_class("destructive-action")
        restart.connect("clicked", lambda _w: power("reboot"))
        poweroff.connect("clicked", lambda _w: power("off"))
        row.pack_end(poweroff, False, False, 0)
        row.pack_end(restart, False, False, 0)
        return row

    # ---- actions ---------------------------------------------------------
    def _toggle_wifi(self, sw, _pspec):
        sh(["nmcli", "radio", "wifi", "on" if sw.get_active() else "off"])
        GLib.timeout_add(500, self.update_wifi)

    def _vol_changed(self, scale):
        level = int(scale.get_value())
        self.vol_pct.set_text("%d%%" % level)
        sh(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "%d%%" % level])

    def _mute_changed(self, chk):
        sh(["pactl", "set-sink-mute", "@DEFAULT_SINK@",
            "1" if chk.get_active() else "0"])

    def _bri_changed(self, scale):
        if not self.output:
            return
        level = int(scale.get_value())
        self.bri_pct.set_text("%d%%" % level)
        sh(["xrandr", "--output", self.output, "--brightness", "%.2f" % (level / 100.0)])

    def _theme_changed(self, chk):
        dark, bright = theme_lists()
        pool = dark if chk.get_active() else bright
        if not pool:
            return
        preferred = next((t for t in pool if "light" in t.lower() or "dark" in t.lower()), pool[0])
        sh(["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", preferred])

    # ---- state -----------------------------------------------------------
    def update_wifi(self):
        on = wifi_on()
        self.wifi_switch.handler_block_by_func(self._toggle_wifi)
        self.wifi_switch.set_active(on)
        self.wifi_switch.handler_unblock_by_func(self._toggle_wifi)
        ssid = wifi_ssid() if on else None
        self.wifi_detail.set_text(ssid if ssid else ("on" if on else "off"))
        return False

    def refresh(self):
        self.update_wifi()

        vol = volume()
        self.slider.handler_block_by_func(self._vol_changed)
        self.mute.handler_block_by_func(self._mute_changed)
        if vol is None:
            self.slider.set_sensitive(False)
            self.mute.set_sensitive(False)
            self.vol_pct.set_text("")
            self.vol_note.set_text("Needs pulseaudio-utils (apply-root.sh)")
        else:
            self.slider.set_sensitive(True)
            self.mute.set_sensitive(True)
            self.slider.set_value(vol[0])
            self.mute.set_active(vol[1])
            self.vol_pct.set_text("%d%%" % vol[0])
            self.vol_note.set_text("")
        self.slider.handler_unblock_by_func(self._vol_changed)
        self.mute.handler_unblock_by_func(self._mute_changed)

        self.output = active_output()
        cur = current_brightness(self.output) if self.output else None
        self.bri.handler_block_by_func(self._bri_changed)
        if self.output and cur is not None:
            level = int(round(cur * 100))
            self.bri.set_sensitive(True)
            self.bri.set_value(level)
            self.bri_pct.set_text("%d%%" % level)
            self.bri_note.set_text("")
        else:
            self.bri.set_sensitive(False)
            self.bri_pct.set_text("")
            self.bri_note.set_text("No adjustable display output")
        self.bri.handler_unblock_by_func(self._bri_changed)

        dark, bright = theme_lists()
        cur_theme = current_theme()
        self.dark.handler_block_by_func(self._theme_changed)
        if dark and bright:
            self.dark.set_sensitive(True)
            self.dark.set_active("dark" in cur_theme.lower())
        elif not dark and not bright:
            self.dark.set_sensitive(False)
            self.dark.set_active(False)
        else:
            self.dark.set_sensitive(False)
        self.dark.handler_unblock_by_func(self._theme_changed)


def main():
    QuickSettings().popup()
    Gtk.main()


if __name__ == "__main__":
    main()