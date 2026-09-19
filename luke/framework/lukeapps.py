"""Luke application system: an original, file-based app registry.

Applications are described by entries in ~/.luke/apps.json. The launcher
and other tools read this registry; a .desktop entry is optional sugar for
menus that do not understand the registry (Whisker, dock). There is no
hard-coded desktop: everything goes through this registry.
"""

import json
import os
import shlex
import shutil
import subprocess

from lukepaths import ROOT

MANIFEST = os.path.join(ROOT, "apps.json")
STATE = os.path.join(ROOT, "state")
RECENTS = os.path.join(STATE, "recents.json")
FAVORITES = os.path.join(STATE, "favorites.json")
MAX_RECENTS = 8

DEFAULT_FAVORITES = ["terminal", "files", "editor"]

_APPS = None


class App:
    def __init__(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.exec = data["exec"]
        self.icon = data.get("icon", "application-x-executable")
        self.color = data.get("color", "#1e2731")
        self.category = data.get("category", "Other")
        self.desc = data.get("desc", "")
        self.terminal = bool(data.get("terminal", False))


def _state_path(name):
    return os.path.join(STATE, name)


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _save_json(path, value):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2)
    except OSError:
        pass


def load_apps():
    """Read and validate the registry. Returns list of App."""
    global _APPS
    if _APPS is None:
        apps = []
        try:
            with open(MANIFEST, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            for item in raw:
                if isinstance(item, dict) and item.get("id") and item.get("exec"):
                    apps.append(App(item))
        except (OSError, ValueError):
            apps = []
        apps.sort(key=lambda a: a.name.lower())
        _APPS = apps
    return list(_APPS)


def get_app(app_id):
    for app in load_apps():
        if app.id == app_id:
            return app
    return None


def _resolve(cmd):
    out = []
    for part in cmd:
        if part == "~" or part.startswith("~/"):
            part = os.path.expanduser(part)
        out.append(part)
    return out


def launch(app, in_terminal=None):
    """Start an application. Returns True when the process was started."""
    if app is None:
        return False
    cmd = _resolve(app.exec)
    if not cmd:
        return False
    first = cmd[0]
    if not first.startswith("/"):
        if shutil.which(first) is None:
            return False
    elif not os.path.exists(os.path.expanduser(first)):
        return False

    use_terminal = app.terminal if in_terminal is None else in_terminal
    env = dict(os.environ)
    fw = os.path.join(ROOT, "framework")
    env["PYTHONPATH"] = fw + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        if use_terminal:
            line = shlex.join(cmd)
            subprocess.Popen(["xfce4-terminal", "-e", line],
                             start_new_session=True, env=env)
        else:
            subprocess.Popen(cmd, start_new_session=True, env=env)
        mark_recent(app.id)
        return True
    except OSError:
        return False


def favorites():
    favs = _load_json(FAVORITES, None)
    if favs is None:
        return DEFAULT_FAVORITES
    return [f for f in favs if get_app(f)]


def save_favorites(order):
    _save_json(FAVORITES, [a for a in order if get_app(a)])


def recents():
    rec = _load_json(RECENTS, [])
    return [r for r in rec if get_app(r)]


def mark_recent(app_id):
    rec = _load_json(RECENTS, [])
    rec = [r for r in rec if r != app_id]
    rec.insert(0, app_id)
    _save_json(RECENTS, rec[:MAX_RECENTS])


def categories():
    cats = {}
    for app in load_apps():
        cats.setdefault(app.category, []).append(app)
    return cats