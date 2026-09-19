"""LukeSync — Bookmarks and browsing history, stored locally."""

import os
import time

from lukepaths import state_path

_DIR = state_path("browser")
BOOKMARKS = os.path.join(_DIR, "bookmarks.json")
HISTORY = os.path.join(_DIR, "history.json")

MAX_HISTORY = 60

__all__ = ["add_bookmark", "remove_bookmark", "bookmarks", "visited",
           "record", "recent_visited"]


def _load(path):
    try:
        with open(path) as fh:
            import json
            return json.load(fh)
    except (OSError, ValueError):
        return []


def _save(path, data):
    try:
        if not os.path.isdir(_DIR):
            os.makedirs(_DIR)
        with open(path, "w") as fh:
            import json
            json.dump(data, fh, indent=2)
    except OSError:
        pass


def add_bookmark(title, url):
    items = _load(BOOKMARKS)
    if any(b["url"] == url for b in items):
        return False
    items.append({"title": title, "url": url, "ts": int(time.time())})
    _save(BOOKMARKS, items)
    return True


def remove_bookmark(url):
    items = _load(BOOKMARKS)
    kept = [b for b in items if b["url"] != url]
    if len(kept) != len(items):
        _save(BOOKMARKS, kept)
        return True
    return False


def bookmarks():
    return _load(BOOKMARKS)


def visited(url):
    return any(b["url"] == url for b in bookmarks())


def record(title, url):
    items = _load(HISTORY)
    items = [h for h in items if h["url"] != url]
    items.insert(0, {"title": title, "url": url, "ts": int(time.time())})
    _save(HISTORY, items[:MAX_HISTORY])


def recent_visited(n=8):
    return _load(HISTORY)[:n]
