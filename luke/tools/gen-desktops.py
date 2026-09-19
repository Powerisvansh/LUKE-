#!/usr/bin/env python3
"""Generate .desktop launchers from the Luke app registry (idempotent).

Lets Whisker/docks/menus open the same apps the Luke launcher shows.
Run inside the Luke session; writes only to the user's own directories."""

import json
import os

HOME = os.path.expanduser("~")
LUKE = os.path.join(HOME, ".luke")
APPS_DIR = os.path.join(HOME, ".local", "share", "applications")
FALLBACK_ICONS = {"luke:about": "system-help"}


def main():
    with open(os.path.join(LUKE, "apps.json")) as fh:
        manifest = json.load(fh)
    os.makedirs(APPS_DIR, exist_ok=True)
    for item in manifest:
        app_id = item["id"]
        icon = FALLBACK_ICONS.get(item.get("icon", ""), item.get("icon", "appgrid"))
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
    print("wrote %d .desktop launchers" % len(manifest))


if __name__ == "__main__":
    main()