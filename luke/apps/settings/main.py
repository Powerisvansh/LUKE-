"""Luke Settings — every control here changes a real system value.
Anything that cannot be done is reported honestly instead of faked."""

import getpass
import glob
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.expanduser("~/.luke/framework"))

from lukeui import LukeWindow, start, show_error
from lukeapps import get_app, launch
from gi.repository import Gtk, GdkPixbuf

PICTURES = os.path.expanduser("~/.luke/wallpapers")
SEARCH_BG = [PICTURES, os.path.expanduser("~/Pictures"), "/usr/share/backgrounds"]


def run(cmd, timeout=30):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout, proc.stderr, proc.returncode
    except (OSError, subprocess.TimeoutExpired) as err:
        return "", str(err), -1


def xfconf_set(channel, prop, value):
    return run(["xfconf-query", "-c", channel, "-p", prop, "-s", value])


def xfconf_list(channel):
    out, _, _ = run(["xfconf-query", "-c", channel, "-l"])
    return out.splitlines() if out else []


# ---------------------------------------------------------------- sections

class Section(Gtk.Box):
    title = "Section"
    icon = "preferences-system"

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        head = Gtk.Label(label=self.title, xalign=0)
        head.get_style_context().add_class("luke-title")
        self.pack_start(head, False, False, 0)


def _card(title, widget):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.get_style_context().add_class("luke-card")
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    inner.set_margin_start(14)
    inner.set_margin_end(14)
    inner.set_margin_top(12)
    inner.set_margin_bottom(12)
    if title:
        t = Gtk.Label(label=title, xalign=0)
        t.get_style_context().add_class("luke-card-title")
        inner.pack_start(t, False, False, 0)
    inner.pack_start(widget, True, True, 0)
    box.pack_start(inner, True, True, 0)
    return box


class Appearance(Section):
    title = "Appearance"

    def __init__(self):
        Section.__init__(self)
        self.chosen = None

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        th = Gtk.ComboBoxText()
        themes = sorted(d for d in os.listdir("/usr/share/themes")
                        if os.path.isdir(os.path.join("/usr/share/themes", d)))
        for name in themes:
            th.append_text(name)
        current = self._get_xsettings("/Net/ThemeName")
        if current in themes:
            th.set_active_id(current)
        th.connect("changed", self._set_theme)

        icon = Gtk.ComboBoxText()
        icons = sorted(d for d in os.listdir("/usr/share/icons")
                       if os.path.isdir(os.path.join("/usr/share/icons", d)))
        for name in icons:
            icon.append_text(name)
        current_icon = self._get_xsettings("/Net/IconThemeName")
        if current_icon in icons:
            icon.set_active_id(current_icon)
        icon.connect("changed", self._set_icons)

        font = Gtk.ComboBoxText()
        sizes = ["Luke Sans 9", "Luke Sans 10", "Luke Sans 11", "Luke Sans 12", "Luke Sans 13"]
        for s in sizes:
            font.append_text(s)
        cur_font = self._get_xsettings("/Gtk/FontName")
        if cur_font in sizes:
            font.set_active_id(cur_font)
        font.connect("changed", lambda cb: xfconf_set(
            "xsettings", "/Gtk/FontName", cb.get_active_text()))

        box.pack_start(_card("Theme", self._row("GTK theme", th)), False, False, 0)
        box.pack_start(_card("Icons", self._row("Icon set", icon)), False, False, 0)
        box.pack_start(_card("Font", self._row("Interface font", font)), False, False, 0)

        wall = self._wallpapers()
        box.pack_start(_card("Wallpaper", wall), False, False, 0)

        gen = Gtk.Button(label="Create a fresh wallpaper")
        gen.connect("clicked", self._generate)
        box.pack_start(gen, False, False, 0)
        self.pack_start(box, True, True, 0)

    @staticmethod
    def _get_xsettings(prop):
        out, _, _ = run(["xfconf-query", "-c", "xsettings", "-p", prop])
        return out.strip() if out else ""

    @staticmethod
    def _row(label, widget):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lbl = Gtk.Label(label=label, xalign=0)
        lbl.set_hexpand(True)
        row.pack_start(lbl, True, True, 0)
        row.pack_start(widget, False, False, 0)
        return row

    def _set_theme(self, cb):
        name = cb.get_active_text()
        if name:
            xfconf_set("xsettings", "/Net/ThemeName", name)

    def _set_icons(self, cb):
        name = cb.get_active_text()
        if name:
            xfconf_set("xsettings", "/Net/IconThemeName", name)

    def _wallpapers(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        flow.set_max_children_per_line(6)
        files = []
        for folder in SEARCH_BG:
            if os.path.isdir(folder):
                files += sorted(glob.glob(folder + "/*.{png,jpg,jpeg,svg}", recursive=False))
        if not files:
            note = Gtk.Label(label="No wallpapers found", xalign=0)
            note.get_style_context().add_class("luke-sub")
            box.pack_start(note, False, False, 0)
            return box
        for path in files[:30]:
            child = self._thumb(path)
            flow.add(child)
        flow.connect("child-activated", self._pick)
        box.pack_start(flow, True, True, 0)
        apply_btn = Gtk.Button(label="Set wallpaper")
        apply_btn.connect("clicked", self._apply)
        box.pack_start(apply_btn, False, False, 0)
        return box

    def _thumb(self, path):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 140, 90, True)
            img = Gtk.Image.new_from_pixbuf(pb)
        except Exception:
            return Gtk.Label(label=os.path.basename(path))
        button = Gtk.Button()
        button.set_image(img)
        button.luke_path = path
        button.connect("clicked", lambda w: setattr(self, "chosen", w.luke_path))
        return button

    def _pick(self, flow, child):
        self.chosen = getattr(child.get_child(), "luke_path", None)

    def _apply(self, _w):
        if not self.chosen or not os.path.exists(self.chosen):
            show_error(self, "Choose a wallpaper image first.")
            return
        changed = 0
        for prop in xfconf_list("xfce4-desktop"):
            if prop.endswith("/last-image"):
                xfconf_set("xfce4-desktop", prop, self.chosen)
                changed += 1
        if not changed:
            show_error(self,
                       "The desktop plugin (xfdesktop) is not responding.\n"
                       "Restart it or check that xfce4-desktop is still enabled.")

    def _generate(self, _w):
        os.makedirs(PICTURES, exist_ok=True)
        target = os.path.join(PICTURES, "luke-gradient.png")
        out, err, code = run(["convert", "-size", "1920x1080",
                              "gradient:#0e1318-#2c4a4a", target])
        if code != 0 or not os.path.exists(target):
            show_error(self, err or "Could not create wallpaper (ImageMagick missing).")
            return
        self.chosen = target
        self._apply(None)


class Display(Section):
    title = "Display"

    def __init__(self):
        Section.__init__(self)
        view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        out, err, code = run(["xrandr", "--current"])
        if code != 0 or not out:
            view.pack_start(Gtk.Label(label="Display control is not available here. (%s)" % err,
                                      xalign=0), False, False, 0)
            self.pack_start(_card("Outputs", view), True, True, 0)
            return
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        first = self._parse(out)
        self.combos = []
        if not first:
            view.pack_start(Gtk.Label(label="No connected outputs found.", xalign=0),
                            False, False, 0)
            self.pack_start(_card("Outputs", view), True, True, 0)
            return
        for out_name, current_mode, modes in first:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            name = Gtk.Label(label=out_name, xalign=0)
            name.set_size_request(120, -1)
            combo = Gtk.ComboBoxText()
            for m in modes:
                combo.append_text(m)
            if current_mode in modes:
                combo.set_active_id(current_mode)
            combo.luke_output = out_name
            combo.luke_original = current_mode
            row.pack_start(name, False, False, 0)
            row.pack_start(combo, True, True, 0)
            box.pack_start(row, False, False, 0)
            self.combos.append(combo)
        apply = Gtk.Button(label="Apply resolution")
        apply.connect("clicked", self._apply)
        box.pack_start(apply, False, False, 0)
        view.pack_start(box, True, True, 0)
        self.pack_start(_card("Outputs", view), True, True, 0)

    @staticmethod
    def _parse(xrandr_out):
        outputs = []
        current = None
        for line in xrandr_out.splitlines():
            if not line.startswith(" ") and " connected " in line:
                current = line.split()[0]
                mobj = re.search(r"(\d+x\d+)", line)
                modes = []
                this = [current, (mobj.group(1) if mobj else ""), modes]
                outputs.append(this)
            elif current and line.strip() and line.lstrip().startswith(tuple("0123456789")):
                mode = line.split()[0]
                if re.match(r"^\d+x\d+$", mode) and mode not in outputs[-1][2]:
                    outputs[-1][2].append(mode)
                if "*" in line:
                    outputs[-1][1] = mode
        return outputs

    def _apply(self, _w):
        applied = 0
        for combo in self.combos:
            out_name = combo.luke_output
            mode = combo.get_active_text()
            if not mode or mode == combo.luke_original:
                continue
            _, err, code = run(["xrandr", "--output", out_name, "--mode", mode])
            if code != 0:
                show_error(self, err.strip() or "xrandr could not switch to that mode.")
            else:
                applied += 1
                combo.luke_original = mode
        if applied:
            run(["xfce4-panel", "-r"])


class NetworkS(Section):
    title = "Network"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        out, err, _ = run(["nmcli", "device", "status"])
        text = out or ("NetworkManager is not available: %s" % err)
        label = Gtk.Label(label=text, xalign=0)
        label.set_line_wrap(True)
        label.set_selectable(True)
        box.pack_start(label, True, True, 0)
        open_net = Gtk.Button(label="Open the Network app")
        open_net.connect("clicked", lambda _w: launch(get_app("network")))
        box.pack_start(open_net, False, False, 0)
        self.pack_start(_card("Connections", box), True, True, 0)


class Sound(Section):
    title = "Sound"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        if not shutil.which("pactl"):
            box.pack_start(Gtk.Label(
                label="Volume control needs pulseaudio-utils.\n"
                      "Run apply-root.sh on this computer to install it.",
                xalign=0), False, False, 0)
            self.pack_start(_card("Output volume", box), True, True, 0)
            return
        out, err, _ = run(["pactl", "get-default-sink"])
        sink = out.strip()
        self.sink = sink

        self.slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 150, 5)
        self.slider.set_value(self._volume())
        self.slider.connect("value-changed", self._set_volume)

        self.mute = Gtk.CheckButton(label="Mute")
        self.mute.set_active(self._muted())
        self.mute.connect("toggled", self._set_mute)

        box.pack_start(self.slider, False, False, 0)
        box.pack_start(self.mute, False, False, 0)
        self.pack_start(_card("Output volume", box), True, True, 0)

    @staticmethod
    def _pulse(args):
        out, err, code = run(["pactl"] + args)
        return out.strip(), err, code

    def _volume(self):
        out, _, _ = self._pulse(["get-sink-volume", self.sink])
        m = re.findall(r"(\d+)%", out)
        return int(m[-1]) if m else 100

    def _muted(self):
        out, _, _ = self._pulse(["get-sink-mute", self.sink])
        return out.lower().startswith("yes")

    def _set_volume(self, scale):
        self._pulse(["set-sink-volume", self.sink, "%d%%" % int(scale.get_value())])

    def _set_mute(self, btn):
        cmd = "1" if btn.get_active() else "0"
        self._pulse(["set-sink-mute", self.sink, cmd])


class Storage(Section):
    title = "Storage"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        rows = []
        try:
            with open("/proc/mounts") as fh:
                for line in fh:
                    fields = line.split()
                    if len(fields) < 3 or not fields[0].startswith("/dev/"):
                        continue
                    if fields[1].startswith(("/proc", "/sys", "/dev", "/run", "/snap")):
                        continue
                    st = os.statvfs(fields[1])
                    rows.append((fields[1], st.f_blocks * st.f_frsize,
                                 st.f_bavail * st.f_frsize))
        except OSError as err:
            box.pack_start(Gtk.Label(label=str(err), xalign=0), False, False, 0)
            self.pack_start(_card("Filesystems", box), True, True, 0)
            return
        for path, total, free in rows:
            used = total - free
            frac = used / total if total else 0
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            name = Gtk.Label(label=path, xalign=0)
            name.set_hexpand(True)
            bar = Gtk.ProgressBar()
            bar.set_fraction(frac)
            pct = Gtk.Label(label="%.0f%%" % (frac * 100))
            box.pack_start(row, False, False, 0)
            row.pack_start(name, False, False, 0)
            row.pack_start(bar, True, True, 0)
            row.pack_start(pct, False, False, 0)
        self.pack_start(_card("Filesystems", box), True, True, 0)


class Users(Section):
    title = "Users"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        current = getpass.getuser()
        try:
            with open("/etc/passwd") as fh:
                for line in fh:
                    parts = line.strip().split(":")
                    if len(parts) < 7:
                        continue
                    name, uid, shell = parts[0], parts[2], parts[6]
                    if shell in ("/usr/sbin/nologin", "/bin/false"):
                        continue
                    flag = "  (this session)" if name == current else ""
                    lbl = Gtk.Label(label="%s   uid %s%s" % (name, uid, flag), xalign=0)
                    box.pack_start(lbl, False, False, 0)
        except OSError as err:
            box.pack_start(Gtk.Label(label=str(err), xalign=0), False, False, 0)
        note = Gtk.Label(
            label="Adding or removing users is not exposed here yet.\n"
                  "Use the terminal:  sudo adduser <name>",
            xalign=0)
        note.get_style_context().add_class("luke-sub")
        box.pack_start(note, False, False, 0)
        self.pack_start(_card("Accounts", box), True, True, 0)


class Privacy(Section):
    title = "Privacy & Security"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        if shutil.which("ufw"):
            out, _, code = run(["ufw", "status"])
            box.pack_start(Gtk.Label(label=out.strip() or "ufw installed",
                                     xalign=0, selectable=True), False, False, 0)
            box.pack_start(Gtk.Label(
                label="Change it with:  sudo ufw enable/disable",
                xalign=0, selectable=True), False, False, 0)
        else:
            box.pack_start(Gtk.Label(
                label="No firewall is installed (ufw).\n"
                      "You can install one with:  sudo apt install ufw",
                xalign=0), False, False, 0)
        box.pack_start(Gtk.Label(
            label="Passwords and keys are stored by the system's own "
                  "account services.\nLuke never stores user passwords itself.",
            xalign=0), False, False, 0)
        self.pack_start(_card("Firewall", box), True, True, 0)


class Updates(Section):
    title = "Updates"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.label = Gtk.Label(label="Checking…", xalign=0)
        box.pack_start(self.label, False, False, 0)
        check = Gtk.Button(label="Check again")
        check.connect("clicked", self._check)
        term = Gtk.Button(label="Open update terminal")
        term.connect("clicked", lambda _w: run(
            ["xfce4-terminal", "-e", "sudo apt full-upgrade"]))
        box.pack_start(check, False, False, 0)
        box.pack_start(term, False, False, 0)
        self.pack_start(_card("Package upgrades", box), True, True, 0)
        self._check()

    def _check(self):
        out, err, code = run(["apt", "list", "--upgradable"], timeout=60)
        if code != 0:
            self.label.set_text("Could not reach the package list (%s)" % err.strip())
            return
        count = len([l for l in out.splitlines() if l.strip().split("/")[0][-1].isdigit()])
        self.label.set_text(
            "%d packages have available upgrades." % count
            if count else "Everything is up to date.")


class AboutS(Section):
    title = "About"

    def __init__(self):
        Section.__init__(self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        info = ""
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as fh:
                rel = {}
                for line in fh:
                    if "=" in line:
                        k, _, v = line.partition("=")
                        rel[k.strip()] = v.strip().strip('"')
            info = "%s  %s\nKernel %s" % (rel.get("NAME", "Luke"),
                                          rel.get("VERSION_ID", ""),
                                          os.uname().release)
        box.pack_start(Gtk.Label(label=info, selectable=True, xalign=0),
                       False, False, 0)
        more = Gtk.Button(label="Open About Luke")
        more.connect("clicked", lambda _w: launch(get_app("about")))
        box.pack_start(more, False, False, 0)
        self.pack_start(_card("System", box), True, True, 0)


# ---------------------------------------------------------------- app root

class SettingsWindow(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Settings", width=860, height=580)
        self._sections = []

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar.get_style_context().add_class("luke-card")
        sidebar.set_size_request(210, -1)

        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-selected", self._on_row)
        self.content = Gtk.Stack()

        for cls in (Appearance, Display, NetworkS, Sound, Storage, Users,
                    Privacy, Updates, AboutS):
            section = cls()
            self._sections.append((cls.title, section))
            row = Gtk.Label(label=cls.title, xalign=0)
            row.set_margin_start(12)
            row.set_margin_end(12)
            row.set_margin_top(6)
            row.set_margin_bottom(6)
            self.listbox.add(row)
            self.content.add_named(section, cls.title)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.listbox)
        sidebar.pack_start(scroller, True, True, 0)

        margin = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        margin.pack_start(sidebar, False, False, 0)
        margin.pack_start(self.content, True, True, 0)
        margin.set_margin_top(14)
        margin.set_margin_bottom(14)
        margin.set_margin_start(18)
        margin.set_margin_end(18)
        self.body.pack_start(margin, True, True, 0)

        self.listbox.select_row(self.listbox.get_row_at_index(0))

    def _on_row(self, _list, row):
        if row is not None:
            index = row.get_index()
            title = self._sections[index][0]
            self.content.set_visible_child_name(title)
            self.set_title_text("Settings — %s" % title)


if __name__ == "__main__":
    start(SettingsWindow)