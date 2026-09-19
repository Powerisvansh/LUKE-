"""Luke Greeter — the login screen for the Luke operating system.

Runs under LightDM as the greeter session. Talks to the LightDM daemon
through the LightDM GObject API (gir1.2-lightdm-1). Everything on this
screen is deliberately original: gradient background drawn in cairo,
rounded card, avatar monogram, live clock, show/hide password, loading
state and clear error messages.

If the LightDM bindings are missing it explains what is wrong instead of
failing silently (a real screen is still drawn).
"""

import os
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Gtk, Gdk, GLib, cairo, Pango, PangoCairo

HERE = os.path.dirname(os.path.abspath(__file__))

ACCENT = (0.31, 0.82, 0.77)
FONT = "Luke Sans"

try:
    gi.require_version("LightDM", "1.0")
    from gi.repository import LightDM
    HAVE_LIGHTDM = True
except (ValueError, ImportError):
    HAVE_LIGHTDM = False


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
        all_users = list(LightDM.get_users())
    except Exception:
        return []
    return [u for u in all_users if not u.get_is_logged_in()]


def _round_rect(cr, x, y, w, h, r):
    cr.new_path()
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.arc(x + w - r, y + r, r, 4.7124, 6.2832)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.close_path()


def draw_background(cr, w, h):
    """Original soft vertical gradient with a faint accent glow."""
    grad = cairo.LinearGradient(0, 0, 0, h)
    grad.add_color_stop_rgb(0.0, 0.05, 0.08, 0.11)
    grad.add_color_stop_rgb(0.55, 0.07, 0.10, 0.14)
    grad.add_color_stop_rgb(1.0, 0.05, 0.12, 0.13)
    cr.set_source(grad)
    cr.paint()
    # faint glow near top
    glow = cairo.RadialGradient(w / 2, h * 0.08, 10.0, w / 2, h * 0.08, w * 0.55)
    glow.add_color_stop_rgba(0.0, *ACCENT, 0.10)
    glow.add_color_stop_rgba(1.0, *ACCENT, 0.0)
    cr.set_source(glow)
    cr.set_operator(cairo.OPERATOR_OVER)
    cr.paint()


def avatar_pixbuf(letter, size=88, seed=""):
    hue = sum(ord(ch) for ch in seed or "LK") % 8
    palette = [
        (0.24, 0.51, 0.48), (0.30, 0.42, 0.62), (0.50, 0.35, 0.55),
        (0.36, 0.50, 0.35), (0.45, 0.42, 0.28), (0.28, 0.48, 0.58),
        (0.46, 0.36, 0.44), (0.34, 0.44, 0.52),
    ]
    r, g, b = palette[hue % len(palette)]
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)
    cr.arc(size / 2, size / 2, size * 0.46, 0, 6.2832)
    cr.set_source_rgb(r, g, b)
    cr.fill()
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(Pango.FontDescription("%s Bold %d" % (FONT, int(size * 0.46))))
    layout.set_text(letter, -1)
    tw, th = layout.get_pixel_size()
    cr.move_to((size - tw) / 2, (size - th) / 2)
    cr.set_source_rgb(0.98, 1.0, 1.0)
    PangoCairo.show_layout(cr, layout)
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)


class GreeterWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        self.get_style_context().add_class("greeter")
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

        self.background = Gtk.DrawingArea()
        self.background.connect("draw", self._draw_bg)
        self.background.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.background.connect("button-press-event", self._on_bg_click)

        overlay = Gtk.Overlay()
        overlay.add(self.background)
        self.add(overlay)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_valign(Gtk.Align.FILL)
        overlay.add_overlay(root)

        # top bar
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        top.set_margin_start(36)
        top.set_margin_end(36)
        top.set_margin_top(28)
        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mark = Gtk.Image.new_from_pixbuf(avatar_pixbuf("L", 40, "lk"))
        brand.pack_start(mark, False, False, 0)
        word = Gtk.Label(label="LUKE")
        word.get_style_context().add_class("wordmark")
        brand.pack_start(word, False, False, 0)
        top.pack_start(brand, False, False, 0)

        self.clock_label = Gtk.Label(label="")
        self.clock_label.get_style_context().add_class("clock-label")
        self.date_label = Gtk.Label(label="")
        self.date_label.get_style_context().add_class("date-label")
        clock_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        clock_box.set_halign(Gtk.Align.END)
        clock_box.pack_end(self.clock_label, False, False, 0)
        clock_box.pack_end(self.date_label, False, False, 0)
        top.pack_end(clock_box, False, False, 0)
        root.pack_start(top, False, False, 0)

        # center content
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        center.set_halign(Gtk.Align.CENTER)
        center.set_valign(Gtk.Align.CENTER)
        root.pack_start(center, True, True, 0)

        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.card.get_style_context().add_class("card")
        self.card.set_halign(Gtk.Align.CENTER)
        self.card.set_margin_top(22)
        self.card.set_margin_bottom(22)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        inner.set_margin_start(30)
        inner.set_margin_end(30)
        inner.set_margin_top(28)
        inner.set_margin_bottom(28)

        self.avatar = Gtk.Image.new_from_pixbuf(avatar_pixbuf("?", 88, ""))
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
        self.toggle.set_size_request(64, -1)
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

        self.card.pack_start(inner, True, True, 0)
        center.pack_start(self.card, False, False, 0)
        self.user_entry.connect("activate", lambda _e: self.pass_entry.grab_focus())

        # bottom power row
        power = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        power.set_margin_start(36)
        power.set_margin_end(36)
        power.set_margin_bottom(24)
        restart = Gtk.Button(label="Restart")
        restart.get_style_context().add_class("power")
        restart.connect("clicked", lambda _w: self._power("restart"))
        shutdown = Gtk.Button(label="Shut Down")
        shutdown.get_style_context().add_class("power")
        shutdown.connect("clicked", lambda _w: self._power("shutdown"))
        power.pack_end(shutdown, False, False, 0)
        power.pack_end(restart, False, False, 0)
        root.pack_end(power, False, False, 0)

        self._setup_user()
        self._update_clock()
        GLib.timeout_add(1000, self._update_clock)
        GLib.timeout_add(1000, self._caps_check)

        self.connect("key-press-event", self._on_key)

    # ---- UI helpers -------------------------------------------------------
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
            self.avatar.set_from_pixbuf(
                avatar_pixbuf((user.get_name() or "?")[0].upper(), 88, user.get_name()))
            self.pass_entry.grab_focus()
        elif not HAVE_LIGHTDM:
            self.err_label.set_text(
                "The LightDM bindings are missing.\nRun apply-root.sh to install "
                "gir1.2-lightdm-1 and this screen will work.")
            self.subtitle.set_text("Set-up needed")
            self.login_btn.set_sensitive(False)

    def _draw_bg(self, _w, cr):
        draw_background(cr, self.get_allocated_width(), self.get_allocated_height())
        return False

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

    def _on_bg_click(self, _w, _ev):
        self.user_entry.grab_focus()
        return False

    def _on_key(self, _w, event):
        key = Gdk.keyval_name(event.keyval)
        if key == "Escape" and HAVE_LIGHTDM:
            return False
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

    # ---- authentication ---------------------------------------------------
    def _submit(self):
        if not HAVE_LIGHTDM:
            return
        if self.spinner.get_visible():
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
            except TypeError:
                pass
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

    # ---- power ------------------------------------------------------------
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