import json
import math
import os

import cairo

from design import art
from design import iconlib
from design.tokens import PALETTE, FONTS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "design", "assets")
OUT = os.path.join(ROOT, "design", "out")


def canvas(w, h):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    cr = cairo.Context(surf)
    return surf, cr


def save(surf, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    surf.write_to_png(path)


def render_icon(icon_id, s):
    surf, cr = canvas(s, s)
    iconlib.draw_icon(cr, s, icon_id)
    grad = cairo.LinearGradient(0, 0, 0, s)
    grad.add_color_stop_rgba(0, 1, 1, 1, 0.10)
    grad.add_color_stop_rgba(0.45, 1, 1, 1, 0.00)
    grad.add_color_stop_rgba(1, 0, 0, 0, 0.14)
    cr.set_source(grad)
    art.rounded(cr, 0, 0, s, s, s * 0.22)
    cr.clip()
    cr.paint()
    save(surf, os.path.join(ASSETS, "icons", f"{icon_id}-{s}.png"))


def brand_pngs():
    for s in (256, 512, 1024):
        surf, cr = canvas(s, s)
        art.draw_mark(cr, s * 0.9, s * 0.5, s * 0.5)
        save(surf, os.path.join(ASSETS, "brand", f"luke-mark-{s}.png"))
    surf, cr = canvas(1024, 420)
    art.draw_mark(cr, 300, 220, 210)
    cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(150)
    cr.move_to(420, 265)
    art.set_source(cr, PALETTE["paper"])
    cr.show_text("LUKE")
    cr.move_to(424, 325)
    cr.set_font_size(34)
    cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    art.set_source(cr, PALETTE["faint"])
    cr.show_text("a personal operating system")
    save(surf, os.path.join(ASSETS, "brand", "luke-wordmark-1024.png"))


def wallpaper(cr, W, H, name):
    grad = cairo.LinearGradient(0, 0, 0, H)
    grad.add_color_stop_rgb(0, *(art.hex_rgb("#0D1522")))
    grad.add_color_stop_rgb(0.55, *(art.hex_rgb("#0A101A")))
    grad.add_color_stop_rgb(1, *(art.hex_rgb("#070A10")))
    cr.set_source(grad)
    cr.paint()

    g = cairo.RadialGradient(W * 0.86, H * 0.16, 0, W * 0.86, H * 0.16, W * 0.7)
    g.add_color_stop_rgba(0, *(art.hex_rgb("#2E3A60") + (0.55,)))
    g.add_color_stop_rgba(1, *(art.hex_rgb("#2E3A60") + (0.0,)))
    cr.set_source(g)
    cr.paint()

    g = cairo.RadialGradient(W * 0.12, H * 0.92, 0, W * 0.12, H * 0.92, W * 0.6)
    g.add_color_stop_rgba(0, *(art.hex_rgb("#0F5A4B") + (0.45,)))
    g.add_color_stop_rgba(1, *(art.hex_rgb("#0F5A4B") + (0.0,)))
    cr.set_source(g)
    cr.paint()

    ribbons = [
        ((0.0, 0.32), (0.55, 0.18), (1.0, 0.40), "lumen", 0.045),
        ((0.0, 0.60), (0.45, 0.74), (1.0, 0.52), "dusk", 0.045),
        ((0.0, 0.85), (0.35, 0.70), (1.0, 0.95), "sky", 0.035),
    ]
    for (a0, b0), (a1, b1), (a2, b2), col, al in ribbons:
        cr.set_line_width(H * 0.9)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        art.set_source(cr, PALETTE[col], al)
        cr.move_to(W * a0, H * b0)
        cr.curve_to(W * 0.30, H * b1, W * 0.72, H * b1 + H * 0.06, W * a2, H * b2)
        cr.stroke()

    v = cairo.RadialGradient(W / 2, H / 2, min(W, H) * 0.32, W / 2, H / 2,
                             max(W, H) * 0.76)
    v.add_color_stop_rgba(0, 0, 0, 0, 0.0)
    v.add_color_stop_rgba(1, 0, 0, 0, 0.5)
    cr.set_source(v)
    cr.paint()


def wallpapers():
    for w, h in ((1366, 768), (1920, 1080)):
        surf, cr = canvas(w, h)
        wallpaper(cr, w, h, f"{w}x{h}")
        save(surf, os.path.join(ASSETS, "wallpapers", f"luke-wallpaper-{w}x{h}.png"))


def preview():
    W, H = 1366, 1500
    surf, cr = canvas(W, H)
    art.set_source(cr, PALETTE["veil"])
    cr.paint()
    x, y = 40, 40
    cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(40)
    art.set_source(cr, PALETTE["paper"])
    cr.move_to(x, y + 34)
    cr.show_text("Luke design system")

    sw = 150
    for i, (name, h) in enumerate(PALETTE.items()):
        sx = x + i * (sw + 10)
        art.fill_rounded(cr, sx, y + 60, sw, 70, 10, h)
        cr.set_font_size(17)
        art.set_source(cr, PALETTE["faint"])
        cr.move_to(sx, y + 66)
        cr.show_text(str(name))

    y = y + 170
    surf_mark, cr_m = canvas(220, 220)
    art.draw_mark(cr_m, 220 * 0.9, 220 * 0.5, 220 * 0.5)
    save(surf_mark, os.path.join(OUT, "mark.png"))
    cr.set_source_surface(surf_mark, x + 20, y)
    cr.paint()

    cr.set_font_size(22)
    art.set_source(cr, PALETTE["paper"])
    cr.move_to(x + 280, y + 40)
    cr.show_text("Mark")
    cr.move_to(x + 280, y + 74)
    cr.set_font_size(17)
    art.set_source(cr, PALETTE["faint"])
    cr.show_text("alternate: ring + dagger, slot, gauge")

    y += 180
    icons = sorted(iconlib.ICONS)
    for i, name in enumerate(icons):
        gx = x + (i % 9) * 120
        gy = y + (i // 9) * 120
        iconlib.draw_icon(cr, 96, name)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.translate(gx, gy)
        cr.paint()
        cr.translate(-gx, -gy)
    cr.set_font_size(15)
    art.set_source(cr, PALETTE["faint"])
    for i, name in enumerate(icons):
        gx = x + (i % 9) * 120
        gy = y + (i // 9) * 120
        cr.move_to(gx + 10, gy + 112)
        cr.show_text(name)
    save(surf, os.path.join(OUT, "preview-design.png"))
    print(f"preview -> {OUT}/preview-design.png")


def write_manifest():
    """Assets manifest (device-tree style) so tools never hard-code paths."""
    rel = lambda *parts: "/".join(parts)
    manifest = {
        "version": 2,
        "brand": {
            "mark": {
                str(s): rel("brand", "luke-mark-%d.png" % s)
                for s in (256, 512, 1024)
            },
            "wordmark": rel("brand", "luke-wordmark-1024.png"),
        },
        "wallpapers": {
            "%dx%d" % (w, h): rel("wallpapers", "luke-wallpaper-%dx%d.png" % (w, h))
            for w, h in ((1366, 768), (1920, 1080))
        },
        "icons": {
            name: {
                str(s): rel("icons", "%s-%d.png" % (name, s))
                for s in (48, 128, 256)
            }
            for name in iconlib.ICONS
        },
        "defaults": {
            "wallpaper": rel("wallpapers", "luke-wallpaper-1366x768.png"),
            "mark": rel("brand", "luke-mark-512.png"),
            "wordmark": rel("brand", "luke-wordmark-1024.png"),
        },
    }
    out = os.path.join(ASSETS, "manifest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print("manifest ->", out)


def main():
    for s in (48, 128, 256):
        for name in iconlib.ICONS:
            render_icon(name, s)
    brand_pngs()
    wallpapers()
    write_manifest()
    preview()
    print("assets written to", ASSETS)


if __name__ == "__main__":
    main()