#!/usr/bin/env python3
"""One-time dock tweak: turn the idle separator next to the app drawer into a
Luke launcher button. Only touches that one plugin; backs up the file first.
Idempotent via a marker file."""

import os
import shutil
import xml.etree.ElementTree as ET

HOME = os.path.expanduser("~")
PANEL = os.path.join(HOME, ".config", "xfce4", "xfconf",
                     "xfce-perchannel-xml", "xfce4-panel.xml")
MARKER = os.path.join(HOME, ".luke", "state", "dock_done")
DESKTOP = os.path.join(HOME, ".local", "share", "applications",
                       "luke-launcher.desktop")


def main():
    if os.path.exists(MARKER) or not os.path.exists(PANEL):
        return
    tree = ET.parse(PANEL)
    root = tree.getroot()

    plugins = root.find("property[@name='plugins']")
    if plugins is None:
        return
    plugin = plugins.find("property[@name='plugin-11']")
    if plugin is None or plugin.get("value") != "separator":
        return
    style = plugin.find("property[@name='style']")
    if style is not None and style.get("value", "0") != "0":
        return

    plugin.set("value", "launcher")
    for child in list(plugin):
        plugin.remove(child)
    items = ET.SubElement(plugin, "property",
                          {"name": "items", "type": "array"})
    ET.SubElement(items, "value", {"type": "string"}).text = DESKTOP

    shutil.copy2(PANEL, PANEL + ".lukebak")
    tree.write(PANEL, encoding="utf-8", xml_declaration=True)
    os.makedirs(os.path.dirname(MARKER), exist_ok=True)
    with open(MARKER, "w") as fh:
        fh.write(str(DESKTOP) + "\n")
    print("dock updated")


if __name__ == "__main__":
    main()