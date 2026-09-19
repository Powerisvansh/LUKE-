from . import art
from .tokens import PALETTE

CUT = "#0E1420"


def p(cr, x, y):
    return x, y


def g_terminal(cr, S):
    w = S * 0.085
    art.path_line(cr, S * 0.26, S * 0.30, S * 0.47, S * 0.50, w, PALETTE["paper"])
    art.path_line(cr, S * 0.47, S * 0.50, S * 0.26, S * 0.70, w, PALETTE["paper"])
    art.path_line(cr, S * 0.52, S * 0.70, S * 0.74, S * 0.70, w, PALETTE["paper"])


def g_files(cr, S):
    art.fill_rounded(cr, S * 0.22, S * 0.36, S * 0.56, S * 0.40, S * 0.08,
                     PALETTE["paper"], 1.0)
    art.rounded(cr, S * 0.22, S * 0.36, S * 0.56, S * 0.40, S * 0.08)
    cr.set_line_width(S * 0.055)
    cr.set_source_rgba(*(art.hex_rgb(CUT) + (0.9,)))
    cr.move_to(S * 0.22, S * 0.38)
    cr.line_to(S * 0.46, S * 0.38)
    cr.line_to(S * 0.53, S * 0.46)
    cr.line_to(S * 0.78, S * 0.46)
    cr.stroke()


def g_settings(cr, S):
    art.dot(cr, S * 0.40, S * 0.36, S * 0.08, PALETTE["paper"])
    art.arc(cr, S * 0.40, S * 0.36, S * 0.15, 0.3, 3.5, S * 0.085, PALETTE["paper"])
    art.dot(cr, S * 0.66, S * 0.64, S * 0.08, PALETTE["paper"])
    art.arc(cr, S * 0.66, S * 0.64, S * 0.15, 0.3, 3.5, S * 0.085, PALETTE["paper"])


def g_web(cr, S):
    art.ring(cr, S * 0.52, S * 0.52, S * 0.27, S * 0.075, PALETTE["paper"])
    art.arc(cr, S * 0.52, S * 0.52, S * 0.27, -1.2, 1.2, S * 0.07, PALETTE["paper"])
    art.arc(cr, S * 0.52, S * 0.52, S * 0.27, 2.0, 4.4, S * 0.07, PALETTE["paper"])
    art.line(cr, S * 0.25, S * 0.40, S * 0.79, S * 0.40, S * 0.07, PALETTE["paper"])
    art.line(cr, S * 0.25, S * 0.64, S * 0.79, S * 0.64, S * 0.07, PALETTE["paper"])


def g_store(cr, S):
    cr.move_to(S * 0.30, S * 0.44)
    cr.line_to(S * 0.36, S * 0.26)
    cr.line_to(S * 0.64, S * 0.26)
    cr.line_to(S * 0.70, S * 0.44)
    cr.line_to(S * 0.68, S * 0.70)
    cr.line_to(S * 0.32, S * 0.70)
    cr.close_path()
    cr.set_line_width(S * 0.075)
    art.set_source(cr, PALETTE["paper"])
    cr.stroke()
    art.dot(cr, S * 0.50, S * 0.52, S * 0.07, PALETTE["paper"])


def g_calculator(cr, S):
    art.fill_rounded(cr, S * 0.26, S * 0.20, S * 0.48, S * 0.60, S * 0.10,
                     PALETTE["paper"], 1.0)
    art.fill_rounded(cr, S * 0.32, S * 0.27, S * 0.36, S * 0.11, S * 0.035,
                     CUT, 0.85)
    for i in range(2):
        for j in range(3):
            art.fill_rounded(cr, S * (0.34 + 0.16 * i), S * (0.47 + 0.11 * j),
                             S * 0.10, S * 0.045, S * 0.02, CUT, 0.85)


def g_editor(cr, S):
    art.line(cr, S * 0.28, S * 0.30, S * 0.72, S * 0.30, S * 0.09, PALETTE["paper"])
    art.line(cr, S * 0.28, S * 0.50, S * 0.60, S * 0.50, S * 0.09, PALETTE["paper"])
    art.line(cr, S * 0.28, S * 0.70, S * 0.50, S * 0.70, S * 0.09, PALETTE["paper"])
    art.dot(cr, S * 0.66, S * 0.70, S * 0.05, PALETTE["lumen"])


def g_monitor(cr, S):
    art.arc(cr, S * 0.50, S * 0.52, S * 0.26, 0.9, 5.4, S * 0.085, PALETTE["paper"])
    art.line(cr, S * 0.50, S * 0.52, S * 0.72, S * 0.52, S * 0.05, PALETTE["lumen"])
    art.dot(cr, S * 0.50, S * 0.52, S * 0.06, PALETTE["paper"])


def g_task(cr, S):
    for i in range(3):
        h = S * (0.24 + 0.16 * i)
        art.fill_rounded(cr, S * (0.24 + 0.20 * i), S * 0.76 - h, S * 0.13, h,
                         S * 0.03, PALETTE["paper"], 0.95)
    art.line(cr, S * 0.16, S * 0.80, S * 0.84, S * 0.80, S * 0.05, PALETTE["paper"])


def g_viewer(cr, S):
    art.rounded(cr, S * 0.24, S * 0.26, S * 0.52, S * 0.48, S * 0.08)
    art.set_source(cr, PALETTE["paper"], 0.95)
    cr.fill()
    art.dot(cr, S * 0.42, S * 0.44, S * 0.06, PALETTE["lumen"])
    cr.move_to(S * 0.32, S * 0.62)
    cr.line_to(S * 0.46, S * 0.50)
    cr.line_to(S * 0.58, S * 0.60)
    cr.line_to(S * 0.68, S * 0.50)
    cr.set_line_width(S * 0.05)
    cr.set_source_rgba(*(art.hex_rgb(CUT) + (0.9,)))
    cr.stroke()


def g_media(cr, S):
    art.ring(cr, S / 2, S / 2, S * 0.27, S * 0.06, PALETTE["paper"])
    cr.move_to(S * 0.44, S * 0.40)
    cr.line_to(S * 0.44, S * 0.60)
    cr.line_to(S * 0.62, S * 0.50)
    cr.close_path()
    art.set_source(cr, PALETTE["paper"])
    cr.fill()


def g_clock(cr, S):
    art.ring(cr, S / 2, S / 2, S * 0.26, S * 0.07, PALETTE["paper"])
    art.line(cr, S / 2, S / 2, S / 2, S * 0.38, S * 0.055, PALETTE["paper"])
    art.line(cr, S / 2, S / 2, S * 0.60, S * 0.52, S * 0.055, PALETTE["paper"])


def g_calendar(cr, S):
    art.fill_rounded(cr, S * 0.22, S * 0.26, S * 0.56, S * 0.48, S * 0.08,
                     PALETTE["paper"], 1.0)
    art.fill_rounded(cr, S * 0.34, S * 0.16, S * 0.09, S * 0.22, S * 0.03,
                     PALETTE["paper"], 0.95)
    art.fill_rounded(cr, S * 0.58, S * 0.16, S * 0.09, S * 0.22, S * 0.03,
                     PALETTE["paper"], 0.95)
    art.fill_rounded(cr, S * 0.28, S * 0.34, S * 0.44, S * 0.08, S * 0.03,
                     CUT, 0.85)
    art.dot(cr, S * 0.52, S * 0.56, S * 0.07, PALETTE["lumen"])


def g_about(cr, S):
    art.draw_mark(cr, S * 0.78, S * 0.5, S * 0.54)


def g_network(cr, S):
    for i in range(3):
        a0 = -1.2 + i * 0.5
        a1 = 1.2 - i * 0.5
        r = S * (0.13 + 0.11 * i)
        art.arc(cr, S * 0.5, S * 0.66, r, a0, a1, S * 0.068, PALETTE["paper"])
    art.dot(cr, S * 0.5, S * 0.74, S * 0.05, PALETTE["lumen"])


def g_updates(cr, S):
    art.arc(cr, S / 2, S / 2, S * 0.24, -0.4, 2.2, S * 0.07, PALETTE["paper"])
    art.arc(cr, S / 2, S / 2, S * 0.24, 2.7, 5.3, S * 0.07, PALETTE["paper"])
    art.dot(cr, S * 0.74, S * 0.38, S * 0.05, PALETTE["lumen"])
    art.dot(cr, S * 0.26, S * 0.62, S * 0.05, PALETTE["lumen"])


def g_launcher(cr, S):
    for i in range(2):
        for j in range(2):
            h = PALETTE["lumen"] if (i + j) % 2 else PALETTE["paper"]
            art.fill_rounded(cr, S * (0.22 + 0.28 * i), S * (0.22 + 0.28 * j),
                             S * 0.2, S * 0.2, S * 0.055, h, 0.95)


def g_quick(cr, S):
    art.line(cr, S * 0.24, S * 0.36, S * 0.76, S * 0.36, S * 0.09, PALETTE["paper"])
    art.dot(cr, S * 0.48, S * 0.36, S * 0.07, PALETTE["lumen"])
    art.line(cr, S * 0.24, S * 0.64, S * 0.76, S * 0.64, S * 0.09, PALETTE["paper"])
    art.dot(cr, S * 0.62, S * 0.64, S * 0.07, PALETTE["dusk"])


def g_app(cr, S):
    art.fill_rounded(cr, S * 0.24, S * 0.24, S * 0.52, S * 0.52, S * 0.12,
                     PALETTE["paper"], 0.92)
    art.dot(cr, S * 0.5, S * 0.5, S * 0.09, CUT)


GLYPHS = {
    "terminal": g_terminal,
    "files": g_files,
    "settings": g_settings,
    "web": g_web,
    "store": g_store,
    "calculator": g_calculator,
    "editor": g_editor,
    "monitor": g_monitor,
    "task": g_task,
    "viewer": g_viewer,
    "media": g_media,
    "clock": g_clock,
    "calendar": g_calendar,
    "about": g_about,
    "network": g_network,
    "updates": g_updates,
    "launcher": g_launcher,
    "quick": g_quick,
    "app": g_app,
}

ICONS = {
    "terminal": ("#1B8F74", "#0F5A4B"),
    "files": ("#5B54B8", "#3A3580"),
    "editor": ("#2D7FB8", "#1B4E75"),
    "calculator": ("#1FA98A", "#11664F"),
    "monitor": ("#6A5FD0", "#403896"),
    "task": ("#7A5FCF", "#4C3585"),
    "settings": ("#56518F", "#33306A"),
    "web": ("#159C93", "#0C5F5A"),
    "store": ("#C28A2E", "#7A5315"),
    "viewer": ("#D2685B", "#8A3C33"),
    "media": ("#C95D8B", "#82314F"),
    "clock": ("#3E92C8", "#21547A"),
    "calendar": ("#3E7FC8", "#21487A"),
    "network": ("#1FB59A", "#0E6C5A"),
    "updates": ("#1E8F6F", "#0D5B45"),
    "about": ("#131B28", "#0E1420"),
    "launcher": ("#1E2A3A", "#131B28"),
    "quick": ("#33404F", "#1A222E"),
    "app": ("#28364A", "#172131"),
}


def draw_icon(cr, S, icon_id):
    top, _ = ICONS[icon_id]
    art.fill_rounded(cr, 0, 0, S, S, S * 0.22, top, 1.0)
    art.fill_rounded(cr, 0, 0, S, S, S * 0.22, "#FFFFFF", 0.06)
    art.rounded(cr, 0, 0, S, S, S * 0.22)
    cr.set_line_width(max(S * 0.008, 1))
    cr.set_source_rgba(0, 0, 0, 0.22)
    cr.stroke()
    GLYPHS.get(icon_id, GLYPHS["app"])(cr, S)