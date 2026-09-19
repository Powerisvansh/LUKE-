"""Luke Greeter — the Luke login screen (runs under LightDM).

Original UI: wallpaper backdrop from the shared design system, brand mark,
monogram avatar, live clock, password show/hide, working sign-in through the
LightDM daemon, and power buttons. Falls back gracefully if the LightDM
bindings are missing instead of failing silently.
"""

import os
import time

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")

try:
    gi.require_version("LightDM", "1.0")
    from gi.repository import LightDM
    HAVE_LIGHTDM = True
except (ValueError, ImportError):
    HAVE_LIGHTDM = False

try:
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Pango, PangoCairo, cairo
    HAVE_DRAWING = True
except (ValueError, ImportError, AttributeError):
    HAVE_DRAWING = False

AVATAR_PALETTE = [
    (0.78, 0.55, 0.20), (0.42, 0.44, 0.82), (0.22, 0.55, 0.76),
    (0.66, 0.38, 0.62), (0.20, 0.72, 0.48), (0.47, 0.55, 0.64),
]


def asset(name):
    for base in (ASSETS, HERE):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def session_name():
    for name in ("xfce", "lightdm-xsession"):
        if os.path.exists("/usr/share/xsessions/%s.desktop" % name):
            return name
    try:
        for entry in sorted(os.listdir("/usr/share/xsessions")):
            if entry.endswith(".desktop"):
                return entry[:-8]
    except OSError:
        pass
    return "xfce"


def users():
    if not HAVE_LIGHTDM:
        return []
    try:
        return [u for u in LightDM.get_users() if not u.get_is_logged_in()]
    except Exception:
        return []


def avatar_brush(seed):
    idx = sum(ord(ch) for ch in (seed or "LK")[:8]) % len(AVATAR_PALETTE)
    return AVATAR_PALETTE[idx]


class Avatar(Gtk.DrawingArea):
    def __init__(self, letter, seed="", size=88):
        Gtk.DrawingArea.__init__(self)
        self.letter = (letter or "?")[0].upper()
        self.rgb = avatar_brush(seed)
        self.set_size_request(size, size)
        self.connect("draw", self._render)
        self.set_can_focus(False)

    def _render(self, _w, cr):
        w = self.get_allocated_width()
        h = self.get_allocated_height()
        if not HAVE_DRAWING:
            return False
        r, g, b = self.rgb
        cr.set_source_rgb(r * 0.72, g * 0.72, b * 0.72)
        cr.arc(w / 2, h / 2, min(w, h) * 0.46, 0, 6.2832)
        cr.fill()
        cr.set_source_rgb(r, g, b)
        cr.arc(w / 2, h / 2, min(w, h) * 0.38, 0, 6.2832)
        cr.fill()
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(
            Pango.FontDescription("Noto Sans Bold %d" % int(min(w, h) * 0.44)))
        layout.set_text(self.letter, -1)
        tw, th = layout.get_pixel_size()
        cr.move_to((w - tw) / 2, (h - th) / 2)
        cr.set_source_rgb(0.05, 0.05, 0.09)
        PangoCairo.show_layout(cr, layout)
        return False


class GreeterWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.fullscreen()
        self.set_title("Luke")
        self.session = session_name()
        self._connected = False
        self._q_users = [u for u in users() if u.get_name() != "guest"]

        css = Gtk.CssProvider()
        try:
            css.load_from_path(os.path.join(HERE, "greeter.css"))
            screen = Gdk.Screen.get_default()
            if screen is not None:
                Gtk.StyleContext.add_provider_for_screen(
                    screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception:
            pass

        overlay = Gtk.Overlay()

        self.bg = Gtk.Image()
        overlay.add(self.bg)

        scrim = Gtk.DrawingArea()
        scrim.connect("draw", self._draw_scrim)
        overlay.add_overlay(scrim)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add_overlay(root)
        self.add(overlay)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        top.set_margin_start(40)
        top.set_margin_end(40)
        top.set_margin_top(30)
        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mark = Gtk.Image()
        mpath = asset("luke-mark.png")
        if mpath:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(mpath, 34, 34)
                mark.set_from_pixbuf(pb)
                mark.set_size_request(34, 34)
            except GLib.Error:
                mark = Gtk.Label(label="L")
                mark.get_style_context().add_class("wordmark")
        brand.pack_start(mark, False, False, 0)
        word = Gtk.Label()
        word.set_markup('<span letter_spacing="2400">LUKE</span>')
        word.get_style_context().add_class("wordmark")
        brand.pack_start(word, False, False, 0)
        top.pack_start(brand, False, False, 0)

        self.clock_label = Gtk.Label(label="")
        self.clock_label.get_style_context().add_class("clock-label")
        self.date_label = Gtk.Label(label="")
        self.date_label.get_style_context().add_class("date-label")
        clock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        clock_box.set_halign(Gtk.Align.END)
        clock_box.set_valign(Gtk.Align.CENTER)
        clock_box.pack_end(self.date_label, False, False, 0)
        clock_box.pack_end(self.clock_label, False, False, 0)
        top.pack_end(clock_box, False, False, 0)
        root.pack_start(top, False, False, 0)

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center.set_valign(Gtk.Align.CENTER)
        center.set_halign(Gtk.Align.CENTER)
        root.pack_start(center, True, True, 0)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.get_style_context().add_class("card")
        card.set_size_request(360, -1)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_start(30)
        inner.set_margin_end(30)
        inner.set_margin_top(30)
        inner.set_margin_bottom(30)

        self.avatar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.avatar.set_halign(Gtk.Align.CENTER)
        inner.pack_start(self.avatar, False, False, 0)

        self.welcome = Gtk.Label(label="Welcome")
        self.welcome.get_style_context().add_class("title-label")
        self.subtitle = Gtk.Label(label="Sign in to continue")
        self.subtitle.get_style_context().add_class("subtitle-label")
        inner.pack_start(self.welcome, False, False, 0)
        inner.pack_start(self.subtitle, False, False, 0)

        self.err_label = Gtk.Label(label="")
        self.err_label.get_style_context().add_class("err-label")
        self.err_label.set_line_wrap(True)
        inner.pack_start(self.err_label, False, False, 0)

        inner.pack_start(self._field("Username"), False, False, 0)
        self.user_entry = Gtk.Entry()
        self.user_entry.set_width_chars(22)
        inner.pack_start(self.user_entry, False, False, 0)

        inner.pack_start(self._field("Password"), False, False, 0)
        pass_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pass_entry = Gtk.Entry()
        self.pass_entry.set_visibility(False)
        self.pass_entry.set_activates_default(True)
        self.pass_entry.connect("activate", lambda _e: self._submit())
        self.toggle = Gtk.Button(label="Show")
        self.toggle.set_size_request(68, -1)
        self.toggle.get_style_context().add_class("ghost")
        self.toggle.connect("clicked", self._on_toggle_pass)
        pass_row.pack_start(self.pass_entry, True, True, 0)
        pass_row.pack_start(self.toggle, False, False, 0)
        inner.pack_start(pass_row, False, False, 0)

        self.caps_label = Gtk.Label(label="Caps Lock is on")
        self.caps_label.get_style_context().add_class("caps-label")
        inner.pack_start(self.caps_label, False, False, 0)

        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        self.spin_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.spin_row.set_halign(Gtk.Align.CENTER)
        self.spin_row.pack_start(self.spinner, False, False, 0)
        self.spin_status = Gtk.Label(label="Signing in…")
        self.spin_status.get_style_context().add_class("subtitle-label")
        self.spin_row.pack_start(self.spin_status, False, False, 0)
        inner.pack_start(self.spin_row, False, False, 0)

        self.login_btn = Gtk.Button(label="Sign In")
        self.login_btn.get_style_context().add_class("primary")
        self.login_btn.connect("clicked", lambda _w: self._submit())
        self.login_btn.set_halign(Gtk.Align.FILL)
        inner.pack_start(self.login_btn, False, False, 0)

        card.pack_start(inner, True, True, 0)
        center.pack_start(card, False, False, 0)
        self.user_entry.connect("activate", lambda _e: self.pass_entry.grab_focus())

        power = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        power.set_margin_start(40)
        power.set_margin_end(40)
        power.set_margin_bottom(26)
        restart = Gtk.Button(label="Restart")
        restart.get_style_context().add_class("power")
        restart.connect("clicked", lambda _w: self._power("restart"))
        shutdown = Gtk.Button(label="Shut Down")
        shutdown.get_style_context().add_class("power")
        shutdown.connect("clicked", lambda _w: self._power("shutdown"))
        power.pack_end(shutdown, False, False, 0)
        power.pack_end(restart, False, False, 0)
        root.pack_end(power, False, False, 0)

        footer = Gtk.Label(label="Luke 1.0")
        footer.get_style_context().add_class("footer")
        root.pack_end(footer, False, False, 0)

        self._setup_user()
        self._update_clock()
        GLib.timeout_add(1000, self._update_clock)
        GLib.timeout_add(1000, self._caps_check)
        self.connect("key-press-event", self._on_key)
        self.connect("size-allocate", self._resize)

        self.set_opacity(0.0)
        self._fade = 0
        GLib.timeout_add(16, self._fade_in)

    def _fade_in(self):
        self._fade += 26
        self.set_opacity(min(self._fade / 1000.0, 1.0))
        return self._fade < 1000

    def _resize(self, _w, alloc):
        self._fit_background()

    def _fit_background(self):
        wp = asset("wallpaper.png")
        if not wp:
            return
        try:
            src = GdkPixbuf.Pixbuf.new_from_file(wp)
            w = self.get_allocated_width() or 1366
            h = self.get_allocated_height() or 768
            copy = src.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
            self.bg.set_from_pixbuf(copy)
        except GLib.Error:
            pass

    def _draw_scrim(self, _w, cr):
        cr.set_source_rgba(0.02, 0.03, 0.05, 0.35)
        cr.paint()
        return False

    def _field(self, text):
        lbl = Gtk.Label(label=text, xalign=0)
        lbl.get_style_context().add_class("field-label")
        return lbl

    def _setup_user(self):
        if self._q_users:
            user = self._q_users[0]
            self.user_entry.set_text(user.get_name())
            self.welcome.set_text("Welcome")
            self.subtitle.set_text(user.get_display_name() or user.get_name())
            self.avatar.add(
                Avatar((user.get_name() or "?")[0].upper(), user.get_name(), 88))
            self.pass_entry.grab_focus()
        elif not HAVE_LIGHTDM:
            self.err_label.set_text(
                "The LightDM bindings are missing.\nRun apply-root.sh and this "
                "screen will work.")
            self.subtitle.set_text("Setup needed")
            self.login_btn.set_sensitive(False)

    def _update_clock(self):
        now = time.localtime()
        self.clock_label.set_text(time.strftime("%H:%M", now))
        self.date_label.set_text(time.strftime("%A · %d %B %Y", now))
        return True

    def _caps_check(self):
        keymap = Gdk.Keymap.get_default()
        if keymap is not None:
            self.caps_label.set_visible(keymap.get_caps_lock_state())
        return True

    def _on_toggle_pass(self, _w):
        visible = self.pass_entry.get_visibility()
        self.pass_entry.set_visibility(not visible)
        self.toggle.set_label("Hide" if not visible else "Show")
        self.pass_entry.grab_focus()

    def _on_key(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Tab":
            self._cycle_focus()
            return True
        return False

    def _cycle_focus(self):
        focused = self.get_focus()
        targets = [self.user_entry, self.pass_entry, self.login_btn]
        idx = 0
        for i, w in enumerate(targets):
            if focused is w:
                idx = (i + 1) % len(targets)
                break
        targets[idx].grab_focus()

    def _submit(self):
        if not HAVE_LIGHTDM or self.spinner.get_visible():
            return
        username = self.user_entry.get_text().strip()
        if not username:
            self.err_label.set_text("Enter a username.")
            self.user_entry.grab_focus()
            return
        self.err_label.set_text("")
        self.spinner.set_visible(True)
        self.spinner.start()
        self.login_btn.set_sensitive(False)
        self.pass_entry.set_sensitive(False)
        self.user_entry.set_sensitive(False)

        self.greeter = LightDM.get_greeter()
        if not self._connected:
            self._connected = True
            self.greeter.connect("show-prompt", self._on_prompt)
            self.greeter.connect("show-message", self._on_message)
            self.greeter.connect("authentication-complete", self._on_complete)
        try:
            self.greeter.authenticate(username)
        except Exception:
            try:
                LightDM.greeter_authenticate(self.greeter, username)
            except Exception as err:
                self._reset("Could not start sign-in: %s" % err)

    def _on_prompt(self, _g, _text, prompt_type):
        if prompt_type == LightDM.PromptType.SECRET:
            self.greeter.respond(self.pass_entry.get_text())
        else:
            self.greeter.respond("")

    def _on_message(self, _g, text, message_type):
        if text and message_type == LightDM.MessageType.ERROR:
            self.err_label.set_text(text)

    def _on_complete(self, _g):
        if self.greeter.get_is_authenticated():
            self.spin_status.set_text("Starting session…")
            ok = False
            try:
                ok = self.greeter.start_session_sync(self.session)
            except Exception:
                pass
            if not ok:
                try:
                    ok = LightDM.greeter_start_session_sync(self.greeter, self.session)
                except Exception:
                    ok = False
            if ok:
                Gtk.main_quit()
            else:
                self._reset("The session could not be started.")
        else:
            self._reset("Incorrect username or password.")

    def _reset(self, message):
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.login_btn.set_sensitive(True)
        self.pass_entry.set_sensitive(True)
        self.user_entry.set_sensitive(True)
        if message:
            self.err_label.set_text(message)
        self.pass_entry.set_text("")
        self.pass_entry.grab_focus()

    def _power(self, action):
        if not HAVE_LIGHTDM:
            return
        try:
            import dbus
            bus = dbus.SystemBus()
            manager = bus.get_object("org.freedesktop.DisplayManager",
                                     "/org/freedesktop/DisplayManager")
            manager.Shutdown(dbus_interface="org.freedesktop.DisplayManager") \
                if action == "shutdown" else \
                manager.Restart(dbus_interface="org.freedesktop.DisplayManager")
        except Exception:
            os.system("systemctl %s" % ("poweroff" if action == "shutdown" else "reboot"))


def main():
    win = GreeterWindow()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()