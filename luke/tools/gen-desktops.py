#!/usr/bin/env python3
"""Generate .desktop launchers from the Luke app registry v2 (idempotent).

Lets Whisker/docks/menus open the same apps the Luke shell shows. Runs
inside the Luke session; writes only to the user's own directories. Hidden
registry entries and built-in shell surfaces are skipped."""

import json
import os
import sys

HOME = os.path.expanduser("~")
LUKE = os.path.join(HOME, ".luke")
APPS_DIR = os.path.join(HOME, ".local", "share", "applications")
SKIP = {"launcher", "quicksettings"}


def write_desktops():
    with open(os.path.join(LUKE, "apps.json")) as fh:
        manifest = json.load(fh)
    os.makedirs(APPS_DIR, exist_ok=True)
    written = 0
    for item in manifest:
        app_id = item["id"]
        if app_id in SKIP or item.get("hidden", False):
            continue
        icon = item.get("icon", "appgrid")
        exec_cmd = " ".join(
            os.path.expanduser(a) if a.startswith("~") else a
            for a in item["exec"])
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Version=1.0\n"
            "Name=%s\n"
            "Comment=%s\n"
            "Exec=%s\n"
            "Icon=%s\n"
            "Terminal=false\n"
            "Categories=%s;\n"
            "X-Luke-App=%s\n"
            % (item["name"], item.get("desc", ""), exec_cmd, icon,
               item.get("category", "Utility"), app_id))
        with open(os.path.join(APPS_DIR, "luke-%s.desktop" % app_id), "w") as fh:
            fh.write(content)
        written += 1
    return written


if __name__ == "__main__":
    print("wrote %d .desktop launchers" % write_desktops())
    sys.exit(0)