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
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

from lukepaths import ROOT
from lukeassets import icon as asset_icon

MANIFEST = os.path.join(ROOT, "apps.json")
STATE = os.path.join(ROOT, "state")
RECENTS = os.path.join(STATE, "recents.json")
FAVORITES = os.path.join(STATE, "favorites.json")
APPS_HOME = os.path.join(ROOT, "store", "apps")
MAX_RECENTS = 8
DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/Powerisvansh/LUKE-/master/"
    "catalog/apps.json")

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


def install_bundle(path, replace=False):
    """Copy a Luke app bundle into the user's apps dir and register it.

    Returns (ok, reason). The bundle must contain an app.json descriptor.
    """
    descriptor = read_bundle_descriptor(path)
    if descriptor is None:
        return False, "No app.json descriptor in the bundle."
    app_id = descriptor["id"]
    current = get_app(app_id)
    if current is not None and not replace:
        return False, "An app with id '%s' is already registered." % app_id
    if current is not None and current.system:
        return False, "'%s' is built into Luke and cannot be replaced." % app_id

    dest = os.path.join(APPS_HOME, app_id)
    try:
        os.makedirs(APPS_HOME, exist_ok=True)
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

    raw = [e for e in _raw_manifest() if e.get("id") != app_id]
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


def fetch_catalog(url=None, timeout=20):
    """Fetch a remote catalog and return its validated app entries."""
    url = url or os.environ.get("LUKE_APP_CATALOG", DEFAULT_CATALOG_URL)
    request = urllib.request.Request(url, headers={"User-Agent": "Luke-App-Store/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeError) as err:
        return [], "Could not load the app catalog: %s" % err
    entries = data.get("apps", []) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return [], "The app catalog has an invalid format."
    valid = []
    for entry in entries:
        if (isinstance(entry, dict) and entry.get("id") and
                entry.get("name") and entry.get("url")):
            valid.append(entry)
    return valid, None


def _safe_extract(archive, destination):
    """Extract an archive without allowing paths outside destination."""
    members = archive.getmembers() if isinstance(archive, tarfile.TarFile) else archive.infolist()
    for member in members:
        name = member.name if isinstance(member, tarfile.TarInfo) else member.filename
        target = os.path.abspath(os.path.join(destination, name))
        if os.path.commonpath([destination, target]) != os.path.abspath(destination):
            raise ValueError("Archive contains an unsafe path.")
    archive.extractall(destination)


def _find_bundle(root):
    for current, _dirs, files in os.walk(root):
        if "app.json" in files:
            return current
    return None


def download_bundle(entry, progress=None, timeout=60):
    """Download and unpack one catalog entry, returning a temporary bundle path."""
    url = entry.get("url")
    if not url:
        raise ValueError("Catalog entry has no bundle URL.")
    root = tempfile.mkdtemp(prefix="luke-store-")
    archive_path = os.path.join(root, "bundle.archive")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Luke-App-Store/1"})
        digest = hashlib.sha256()
        total = int(entry.get("size", 0) or 0)
        received = 0
        with urllib.request.urlopen(request, timeout=timeout) as response, \
                open(archive_path, "wb") as output:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                if progress:
                    progress(received, total)
        expected = entry.get("sha256")
        if expected and digest.hexdigest().lower() != expected.lower():
            raise ValueError("Downloaded bundle checksum does not match the catalog.")

        extract_root = os.path.join(root, "bundle")
        os.makedirs(extract_root)
        try:
            with tarfile.open(archive_path, "r:*") as archive:
                _safe_extract(archive, extract_root)
        except tarfile.ReadError:
            with zipfile.ZipFile(archive_path) as archive:
                _safe_extract(archive, extract_root)
        bundle = _find_bundle(extract_root)
        descriptor = read_bundle_descriptor(bundle) if bundle else None
        if descriptor is None or descriptor.get("id") != entry.get("id"):
            raise ValueError("Downloaded bundle does not match the catalog entry.")
        return root, bundle
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def install_catalog_app(entry, replace=False, progress=None):
    """Download, validate, and install a catalog entry."""
    root, bundle = download_bundle(entry, progress=progress)
    try:
        return install_bundle(bundle, replace=replace)
    finally:
        shutil.rmtree(root, ignore_errors=True)


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