import math

from .tokens import PALETTE

TAU = 6.283185307179586


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def set_source(cr, h, alpha=1.0):
    cr.set_source_rgba(*(hex_rgb(h) + (alpha,)))


def rounded(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.move_to(x + r, y)
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.14159)
    cr.arc(x + r, y + r, r, 3.14159, 4.71239)
    cr.close_path()


def fill_rounded(cr, x, y, w, h, r, hcol, alpha=1.0):
    rounded(cr, x, y, w, h, r)
    set_source(cr, hcol, alpha)
    cr.fill()


def dot(cr, cx, cy, r, h, alpha=1.0):
    cr.arc(cx, cy, r, 0, TAU)
    set_source(cr, h, alpha)
    cr.fill()


def ring(cr, cx, cy, r, w, h, alpha=1.0):
    cr.set_line_width(w)
    set_source(cr, h, alpha)
    cr.arc(cx, cy, r, 0, TAU)
    cr.stroke()


def arc(cr, cx, cy, r, a0, a1, w, h, alpha=1.0):
    cr.set_line_width(w)
    set_source(cr, h, alpha)
    cr.arc(cx, cy, r, a0, a1)
    cr.stroke()


def line(cr, x1, y1, x2, y2, w, h, alpha=1.0):
    cr.set_line_width(w)
    set_source(cr, h, alpha)
    cr.move_to(x1, y1)
    cr.line_to(x2, y2)
    cr.stroke()


path_line = line


def mark_blade(cr, cx, cy, R, w0, w1, a0, a1):
    steps = 64
    outer = []
    inner = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        w = w0 + (w1 - w0) * i / steps
        outer.append((cx + (R + w / 2) * math.cos(a), cy + (R + w / 2) * math.sin(a)))
        inner.append((cx + (R - w / 2) * math.cos(a), cy + (R - w / 2) * math.sin(a)))
    cr.move_to(*outer[0])
    for px, py in outer[1:]:
        cr.line_to(px, py)
    cr.line_to(*inner[-1])
    for px, py in reversed(inner[:-1]):
        cr.line_to(px, py)
    cr.close_path()


def draw_mark(cr, S, cx=None, cy=None, blade="lumen", node="dusk"):
    if cx is None:
        cx = S / 2
    if cy is None:
        cy = S / 2
    R = S * 0.30
    w0 = S * 0.158
    w1 = S * 0.066
    a0 = -2.45
    a1 = 0.85
    mark_blade(cr, cx, cy, R, w0, w1, a0, a1)
    set_source(cr, PALETTE[blade])
    cr.fill()
    an = a0 + (a1 - a0) * 0.52
    dot(cr, cx + (R + (w0 + w1) * 0.47) * math.cos(an),
        cy + (R + (w0 + w1) * 0.47) * math.sin(an),
        S * 0.072, PALETTE[node])