"""Luke application system v2: a file-based app registry and installer.

Applications are described by entries in ~/.luke/apps.json (the registry)
with an original manifest format: id, name, exec, icon, category, description,
keywords, version, author, dependencies. The registry is the single source of
truth — the shell, launcher, dock and .desktop generation all go through it.

v2 additions over v1:
  * ordered categories (manifest order, not alphabetical)
  * keyword search (name + description + keywords + tags)
  * version / author / system flags
  * real install_bundle() / uninstall() helpers
  * icons resolved from the shared assets manifest (lukeassets)
"""

import json
import os
import shlex
import shutil
import subprocess
import sys

from lukepaths import ROOT
from lukeassets import icon as asset_icon

MANIFEST = os.path.join(ROOT, "apps.json")
STATE = os.path.join(ROOT, "state")
RECENTS = os.path.join(STATE, "recents.json")
FAVORITES = os.path.join(STATE, "favorites.json")
APPS_HOME = os.path.join(ROOT, "apps")
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
        self.version = data.get("version", "1.0")
        self.author = data.get("author", "Luke")
        self.keywords = data.get("keywords", [])
        self.tags = data.get("tags", [])
        self.depends = data.get("depends", [])
        self.terminal = bool(data.get("terminal", False))
        self.hidden = bool(data.get("hidden", False))
        self.system = bool(data.get("system", False))

    # ---- identity ------------------------------------------------------
    def icon_path(self, size=128):
        """Path to the original Luke icon PNG, or None for a theme icon."""
        if self.icon.startswith("luke:"):
            return asset_icon(self.icon.split(":", 1)[1], size)
        return None

    def icon_name(self):
        """Theme icon to fall back on when no Luke PNG exists."""
        return self.icon.replace("luke:", "luke-", 1)

    def keywords_text(self):
        return " ".join(list(self.keywords) + list(self.tags)).lower()

    def suggestions(self):
        return self.keywords_text()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "exec": self.exec,
            "icon": self.icon,
            "color": self.color,
            "category": self.category,
            "desc": self.desc,
            "version": self.version,
            "author": self.author,
            "keywords": self.keywords,
            "tags": self.tags,
            "depends": self.depends,
            "terminal": self.terminal,
            "hidden": self.hidden,
            "system": self.system,
        }


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


def _raw_manifest():
    try:
        with open(MANIFEST, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def load_apps(public_only=True):
    """Read and validate the registry, in manifest (curated) order."""
    global _APPS
    if _APPS is None:
        apps = []
        for item in _raw_manifest():
            if isinstance(item, dict) and item.get("id") and item.get("exec"):
                apps.append(App(item))
        _APPS = apps
    if public_only:
        return [a for a in _APPS if not a.hidden]
    return list(_APPS)


def refresh():
    """Drop the cache so the next call re-reads the registry."""
    global _APPS
    _APPS = None


def get_app(app_id):
    for app in load_apps(public_only=False):
        if app.id == app_id:
            return app
    return None


def apps(query=None, category=None):
    """Search/filter the public registry. Query matches name, desc, keywords."""
    query = (query or "").strip().lower()
    out = []
    for app in load_apps():
        if category and app.category != category:
            continue
        if query:
            hay = (app.name + " " + app.desc + " " + app.keywords_text()).lower()
            if query not in hay:
                continue
        out.append(app)
    return out


def categories():
    """Ordered (category, [apps]) pairs, preserving manifest order."""
    seen = []
    for app in load_apps():
        if app.category not in [s[0] for s in seen]:
            seen.append((app.category, []))
        for cat, items in seen:
            if cat == app.category:
                items.append(app)
                break
    return seen


def favorites():
    favs = _load_json(FAVORITES, None)
    if favs is None:
        return DEFAULT_FAVORITES
    return [f for f in favs if get_app(f)]


def save_favorites(order):
    _save_json(FAVORITES, [a for a in order if get_app(a)])


def recents():
    return [r for r in _load_json(RECENTS, []) if get_app(r)]


def mark_recent(app_id):
    rec = [r for r in _load_json(RECENTS, []) if r != app_id]
    rec.insert(0, app_id)
    _save_json(RECENTS, rec[:MAX_RECENTS])


# ------------------------------------------------------------------ launch
def _resolve(cmd):
    out = []
    for part in cmd:
        if part == "~" or part.startswith("~/"):
            part = os.path.expanduser(part)
        out.append(part)
    return out


def _missing_dep(app):
    for dep in app.depends:
        if shutil.which(dep) is None and not os.path.exists(
                os.path.expanduser(dep)):
            return dep
    return None


def launch(app, in_terminal=None):
    """Start an application. Returns True when the process was started."""
    if app is None:
        return False
    dep = _missing_dep(app)
    if dep:
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
    env["PYTHONPATH"] = fw + (os.pathsep + env["PYTHONPATH"]
                              if env.get("PYTHONPATH") else "")
    try:
        if use_terminal:
            subprocess.Popen(["xfce4-terminal", "-e", shlex.join(cmd)],
                             start_new_session=True, env=env)
        else:
            subprocess.Popen(cmd, start_new_session=True, env=env)
        mark_recent(app.id)
        return True
    except OSError:
        return False


# --------------------------------------------------------- install support
def read_bundle_descriptor(path):
    """Read a Luke app bundle's app.json descriptor, or None."""
    descriptor = os.path.join(path, "app.json")
    try:
        with open(descriptor, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not (isinstance(data, dict) and data.get("id") and data.get("exec")):
        return None
    return data


def install_bundle(path):
    """Copy a Luke app bundle into the user's apps dir and register it.

    Returns (ok, reason). The bundle must contain an app.json descriptor.
    """
    descriptor = read_bundle_descriptor(path)
    if descriptor is None:
        return False, "No app.json descriptor in the bundle."
    app_id = descriptor["id"]
    if get_app(app_id) is not None:
        return False, "An app with id '%s' is already registered." % app_id

    dest = os.path.join(APPS_HOME, app_id)
    try:
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(path, dest)
    except OSError as err:
        return False, "Could not copy the bundle: %s" % err

    entry = dict(descriptor)
    entry.setdefault("version", "1.0")
    entry.setdefault("author", "Luke")
    entry.setdefault("category", "Utilities")
    entry.setdefault("icon", "luke:app")
    entry.setdefault("color", "#1e2731")
    entry.setdefault("desc", "")
    entry.setdefault("keywords", [])
    entry.setdefault("depends", [])
    entry["exec"] = ["python3", os.path.join("~/.luke/apps", app_id, "main.py")]
    entry.setdefault("system", False)

    raw = _raw_manifest()
    raw.append(entry)
    _save_json(MANIFEST, raw)
    refresh()
    try:
        subprocess.Popen([sys.executable, os.path.join(ROOT, "tools",
                                                       "gen-desktops.py")],
                         start_new_session=True,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        pass
    return True, app_id


def uninstall(app_id):
    """Remove a non-system app (bundle dir, registry entry, .desktop)."""
    app = get_app(app_id)
    if app is None:
        return False, "Unknown app '%s'." % app_id
    if app.system:
        return False, "'%s' is built into Luke and cannot be removed." % app_id

    raw = _raw_manifest()
    raw = [e for e in raw if e.get("id") != app_id]
    _save_json(MANIFEST, raw)
    refresh()

    bundle = os.path.join(APPS_HOME, app_id)
    if os.path.isdir(bundle):
        shutil.rmtree(bundle, ignore_errors=True)

    desktop = os.path.join(os.path.expanduser("~/.local/share/applications"),
                           "luke-%s.desktop" % app_id)
    if os.path.exists(desktop):
        try:
            os.remove(desktop)
        except OSError:
            pass
    return True, app_id