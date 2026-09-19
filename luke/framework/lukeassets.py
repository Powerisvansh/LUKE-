"""Luke asset library — resolve shared OS assets from the generated manifest.

The manifest (design/assets/manifest.json) describes brand, wallpapers and
icons so neither the shell nor the apps hard-code file paths. Handles both
deployed (~/.luke) and source-tree (dev host) layouts. If a requested asset
is missing it returns None and callers fall back to theme icons / defaults.
"""

import json
import os

from lukepaths import ROOT

ASSETS_DIR = os.path.join(ROOT, "design", "assets")
MANIFEST_PATH = os.path.join(ASSETS_DIR, "manifest.json")

_manifest = None


def manifest():
    global _manifest
    if _manifest is None:
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as fh:
                _manifest = json.load(fh)
        except (OSError, ValueError):
            _manifest = {}
    return _manifest


def _resolve(rel):
    if not rel:
        return None
    p = os.path.join(ASSETS_DIR, *rel.split("/"))
    return p if os.path.exists(p) else None


def icon(glyph, size):
    """Path to the original icon PNG for a glyph id, or None."""
    m = manifest().get("icons", {}).get(glyph, {})
    sizes = ["%d" % size, "256", "128", "48"]
    for s in sizes:
        if s in m:
            p = _resolve(m[s])
            if p:
                return p
    return None


def brand_mark(size=512):
    m = manifest().get("brand", {}).get("mark", {})
    nearby = [str(size), "512", "1024", "256"]
    for s in nearby:
        if s in m:
            p = _resolve(m[s])
            if p:
                return p
    return None


def wordmark():
    return _resolve(manifest().get("brand", {}).get("wordmark"))


def wallpaper(prefer=None):
    """Default wallpaper, optionally for a specific resolution."""
    m = manifest().get("wallpapers", {})
    if prefer and prefer in m:
        p = _resolve(m[prefer])
        if p:
            return p
    return _resolve(manifest().get("defaults", {}).get("wallpaper")) or \
        _resolve(next(iter(m.values()), ""))


def defaults():
    return manifest().get("defaults", {})