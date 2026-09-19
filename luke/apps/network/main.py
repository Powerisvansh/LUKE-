"""Luke Network — real Wi-Fi management through NetworkManager (nmcli)."""

import subprocess
import threading
from lukeui import LukeWindow, start, show_error
from gi.repository import Gtk, GLib


def run_nm(args):
    try:
        proc = subprocess.run(["nmcli"] + args,
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as err:
        return None, str(err)
    return proc.stdout, proc.stderr


def _rows(stdout, chunk):
    parts = [p.strip("\n") for p in stdout.split("\n") if p != ""]
    return [tuple(parts[i:i + chunk]) for i in range(0, len(parts), chunk)
            if len(parts[i:i + chunk]) == chunk]


def wifi_state():
    out, _ = run_nm(["radio", "wifi"])
    return (out or "").strip().startswith("enabled")


def active_connection():
    out, _ = run_nm(["-g", "NAME", "connection", "show", "--active"])
    connected = (out or "").strip().split("\n")
    return [c for c in connected if c][:1]


def saved_connections():
    out, _ = run_nm(["-g", "NAME,TYPE", "connection", "show"])
    if out is None:
        return []
    return _rows(out, 2)


def scan_wifi():
    out, _ = run_nm(["-g", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
    if out is None:
        return []
    best = {}
    lines = out.split("\n")
    i, n = 0, len(lines)
    while i < n:
        ssid = lines[i].strip()
        signal = lines[i + 1].strip() if i + 1 < n else ""
        sec = lines[i + 2].strip() if i + 2 < n else ""
        if ssid:
            cur = best.get(ssid)
            if cur is None or int(signal) > cur[1]:
                best[ssid] = (signal, sec)
        i += 3
    return [(ssid, sig, sec) for ssid, (sig, sec) in sorted(
        best.items(), key=lambda kv: int(kv[1][0]), reverse=True)]


class Network(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Network", width=720, height=560)

        self.state_switch = Gtk.Switch()
        self.state_switch.connect("notify::active", self._on_toggle)
        self.state_label = Gtk.Label(label="")
        self.state_label.get_style_context().add_class("luke-sub")
        self.active_label = Gtk.Label(label="…", xalign=0)
        self.active_label.get_style_context().add_class("luke-sub")
        self.status_label = Gtk.Label(label="", xalign=0)
        self.status_label.get_style_context().add_class("luke-accent")

        self.saved_list = Gtk.ListBox()
        self.saved_list.get_style_context().add_class("luke-card")
        self.wifi_list = Gtk.ListBox()

        btn_rescan = Gtk.Button(label="Rescan")
        btn_rescan.connect("clicked", lambda _w: self.refresh())

        top = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        top.set_margin_start(20)
        top.set_margin_end(20)
        top.set_margin_top(18)
        top.set_margin_bottom(18)

        state_card = self._card_box()
        state_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        t = Gtk.Label(label="Wi-Fi", xalign=0)
        t.get_style_context().add_class("luke-card-title")
        state_row.pack_start(t, False, False, 0)
        state_row.pack_start(self.state_switch, False, False, 0)
        state_row.pack_start(self.state_label, False, False, 0)
        state_card.pack_start(state_row, False, False, 0)
        state_card.pack_start(self.active_label, False, False, 0)
        state_card.pack_start(self.status_label, False, False, 0)

        saved_card = self._card_box()
        st = Gtk.Label(label="Saved connections", xalign=0)
        st.get_style_context().add_class("luke-card-title")
        saved_card.pack_start(st, False, False, 0)
        saved_card.pack_start(self.saved_list, True, True, 0)

        wifi_card = self._card_box()
        wt = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wtl = Gtk.Label(label="Available networks", xalign=0)
        wtl.get_style_context().add_class("luke-card-title")
        wt.pack_start(wtl, True, True, 0)
        wt.pack_start(btn_rescan, False, False, 0)
        wifi_card.pack_start(wt, False, False, 0)
        wifi_card.pack_start(self.wifi_list, True, True, 0)

        top.pack_start(state_card, False, False, 0)
        top.pack_start(saved_card, False, False, 0)
        top.pack_start(wifi_card, True, True, 0)

        self.body.pack_start(top, True, True, 0)
        self.refresh()
        GLib.timeout_add(5000, self.refresh)

    @staticmethod
    def _card_box():
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.get_style_context().add_class("luke-card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        inner.set_margin_start(14)
        inner.set_margin_end(14)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        box.pack_start(inner, True, True, 0)
        return inner

    def _on_toggle(self, _sw, _pspec):
        desired = "on" if self.state_switch.get_active() else "off"
        out, err = run_nm(["radio", "wifi", desired])
        if err and "Error" in err:
            show_error(self, err.strip())
        else:
            self.refresh()

    def _connect(self, widget):
        ssid = getattr(widget, "luke_ssid", None)
        security = getattr(widget, "luke_sec", "")
        if not ssid:
            return
        password = ""
        if security and security not in ("", "--"):
            dlg = Gtk.Dialog(
                title="Password for %s" % ssid,
                transient_for=self, modal=True, destroy_with_parent=True)
            dlg.get_content_area().set_margin_start(14)
            dlg.get_content_area().set_margin_end(14)
            dlg.get_content_area().set_margin_top(14)
            dlg.get_content_area().set_margin_bottom(14)
            entry = Gtk.Entry()
            entry.set_visibility(False)
            lbl = Gtk.Label(label="Wireless security key:", xalign=0)
            dlg.get_content_area().pack_start(lbl, False, False, 0)
            dlg.get_content_area().pack_start(entry, False, False, 0)
            dlg.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dlg.add_button("Connect", Gtk.ResponseType.OK)
            dlg.show_all()
            resp = dlg.run()
            password = entry.get_text()
            dlg.destroy()
            if resp != Gtk.ResponseType.OK:
                return
        self.status_label.set_text("Connecting to %s…" % ssid)
        threading.Thread(target=self._connect_job, args=(ssid, password),
                         daemon=True).start()

    def _connect_job(self, ssid, password):
        args = ["dev", "wifi", "connect", ssid]
        if password:
            args += ["password", password]
        out, err = run_nm(args)
        message = ((out or err) or "").strip()
        if "success" in message.lower():
            GLib.idle_add(self._connected, (ssid, "Success"))
        else:
            GLib.idle_add(self._connected, (None, message or "Connection failed"))

    def _connected(self, result):
        ssid, message = result
        if ssid:
            self.status_label.set_text("Connected to %s" % ssid)
        else:
            self.status_label.set_text("")
            show_error(self, message)

    def refresh(self):
        on = wifi_state()
        self.state_switch.handler_block_by_func(self._on_toggle)
        self.state_switch.set_active(on)
        self.state_switch.handler_unblock_by_func(self._on_toggle)
        self.state_label.set_text("on" if on else "off")

        active = active_connection()
        self.active_label.set_text(
            "Connected to %s" % active[0] if active else "No active connection")

        for box, rows in ((self.saved_list, saved_connections()),
                          (self.wifi_list, scan_wifi())):
            while box.get_children():
                box.remove(box.get_children()[0])
            if box is self.saved_list:
                for name, typ in rows:
                    row = Gtk.Label(label="%s  (%s)" % (name, typ), xalign=0)
                    row.set_margin_top(2)
                    row.set_margin_bottom(2)
                    box.add(row)
            else:
                for ssid, sig, sec in rows:
                    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                    name = Gtk.Label(label=ssid, xalign=0)
                    name.set_hexpand(True)
                    name.set_line_wrap(True)
                    signal = Gtk.Label(label="%s%%" % sig)
                    signal.get_style_context().add_class("luke-sub")
                    btn = Gtk.Button(label="Connect")
                    btn.luke_ssid = ssid
                    btn.luke_sec = sec
                    btn.connect("clicked", self._connect)
                    row.set_margin_top(2)
                    row.set_margin_bottom(2)
                    row.pack_start(name, True, True, 0)
                    row.pack_start(signal, False, False, 0)
                    row.pack_start(btn, False, False, 0)
                    box.add(row)
            box.show_all()

        if not self.saved_list.get_children():
            note = Gtk.Label(label="No saved connections", xalign=0)
            note.get_style_context().add_class("luke-sub")
            self.saved_list.add(note)
            self.saved_list.show_all()
        if not self.wifi_list.get_children():
            note = Gtk.Label(label="No networks in range", xalign=0)
            note.get_style_context().add_class("luke-sub")
            self.wifi_list.add(note)
            self.wifi_list.show_all()
        return True


if __name__ == "__main__":
    start(Network)