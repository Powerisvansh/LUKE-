"""Luke App Store: browse a remote catalog and install Luke bundles."""

import os
import sys
import threading

sys.path.insert(0, os.path.expanduser("~/.luke/framework"))

import gi

gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk

from lukeapps import (apps, fetch_catalog, get_app, install_catalog_app,
                      uninstall)
from lukeui import LukeWindow, show_error, start


class Store(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Luke App Store", width=760, height=560)
        self.catalog = []

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.set_margin_start(20)
        header.set_margin_end(20)
        header.set_margin_top(16)
        title = Gtk.Label(label="App Store", xalign=0)
        title.get_style_context().add_class("luke-title")
        header.pack_start(title, True, True, 0)
        refresh = Gtk.Button(label="Refresh catalog")
        refresh.connect("clicked", lambda _w: self._load_catalog())
        header.pack_end(refresh, False, False, 0)
        self.body.pack_start(header, False, False, 0)

        self.status = Gtk.Label(label="Loading catalog...", xalign=0)
        self.status.set_margin_start(20)
        self.status.set_margin_end(20)
        self.status.set_margin_top(6)
        self.status.get_style_context().add_class("luke-sub")
        self.body.pack_start(self.status, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.set_margin_start(20)
        self.listbox.set_margin_end(20)
        self.listbox.set_margin_top(12)
        self.listbox.set_margin_bottom(20)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.listbox)
        self.body.pack_start(scroll, True, True, 0)
        self.show_all()
        self._load_catalog()

    def _load_catalog(self):
        self.status.set_text("Loading catalog...")
        self._clear()
        threading.Thread(target=self._catalog_worker, daemon=True).start()

    def _catalog_worker(self):
        entries, error = fetch_catalog()
        GLib.idle_add(self._catalog_loaded, entries, error)

    def _catalog_loaded(self, entries, error):
        if error:
            self.status.set_text(error)
            return False
        self.catalog = entries
        self.status.set_text("%d app%s available" %
                             (len(entries), "" if len(entries) == 1 else "s"))
        for entry in entries:
            self.listbox.add(self._catalog_row(entry))
        self.listbox.show_all()
        return False

    def _catalog_row(self, entry):
        row = Gtk.ListBoxRow()
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        name = entry.get("name", entry.get("id", "App"))
        version = entry.get("version", "")
        label = Gtk.Label(label=name, xalign=0)
        label.get_style_context().add_class("luke-card-title")
        desc = Gtk.Label(label=entry.get("desc", ""), xalign=0)
        desc.set_line_wrap(True)
        desc.get_style_context().add_class("luke-sub")
        meta = Gtk.Label(label="%s  ·  %s" %
                         (entry.get("author", "Luke"), version), xalign=0)
        meta.get_style_context().add_class("luke-sub")
        details.pack_start(label, False, False, 0)
        details.pack_start(desc, False, False, 0)
        details.pack_start(meta, False, False, 0)
        outer.pack_start(details, True, True, 0)

        installed = get_app(entry.get("id"))
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action = Gtk.Button(label="Update" if installed else "Install")
        action.connect("clicked", self._install, entry, bool(installed))
        actions.pack_start(action, False, False, 0)
        if installed and not installed.system:
            remove = Gtk.Button(label="Remove")
            remove.connect("clicked", self._remove, entry, row)
            actions.pack_start(remove, False, False, 0)
        outer.pack_end(actions, False, False, 0)
        row.add(outer)
        return row

    def _remove(self, button, entry, row):
        button.set_sensitive(False)
        app_id = entry.get("id")
        ok, result = uninstall(app_id)
        if not ok:
            button.set_sensitive(True)
            self.status.set_text("Remove failed: %s" % result)
            return
        self.listbox.remove(row)
        self.status.set_text("Removed %s" % app_id)

    def _install(self, button, entry, replace):
        button.set_sensitive(False)
        button.set_label("Downloading...")
        self.status.set_text("Downloading %s..." % entry.get("name", "app"))
        threading.Thread(target=self._install_worker,
                         args=(button, entry, replace), daemon=True).start()

    def _install_worker(self, button, entry, replace):
        try:
            result = install_catalog_app(entry, replace=replace)
            GLib.idle_add(self._install_done, button, result, None)
        except Exception as err:
            GLib.idle_add(self._install_done, button, None, str(err))

    def _install_done(self, button, result, error):
        if error:
            button.set_sensitive(True)
            button.set_label("Try again")
            self.status.set_text("Install failed: %s" % error)
        else:
            button.set_label("Installed")
            self.status.set_text("Installed %s" % result[1])
        return False

    def _clear(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)


if __name__ == "__main__":
    start(Store)
