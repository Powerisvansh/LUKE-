import os
import shutil
import subprocess
import sys

import cairo

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))
from design import gen, art, tokens

OUT = os.path.join(BASE, "out", "themes", "luke")
PLY = os.path.join(BASE, "plymouth")


def canvas(w, h):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    return surf, cairo.Context(surf)


def save(surf, name):
    os.makedirs(OUT, exist_ok=True)
    surf.write_to_png(os.path.join(OUT, name))


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def pill(cr, w, h, r, hexcol, border=None):
    cr.move_to(w - r, 0.5)
    cr.arc(w - r, h / 2, r, -1.5708, 1.5708)
    cr.line_to(r, h - 0.5)
    cr.arc(r, h / 2, r, 1.5708, 4.71239)
    cr.close_path()
    cr.set_source_rgba(*(_rgb(hexcol) + (0.92,)))
    cr.fill()


def select_sliver(w):
    surf, cr = canvas(w, 36)
    pill(cr, w, 36, 17, "#131B28", "#26344B")
    cr.rectangle(9, 16, 3.5, 4)
    cr.set_source_rgba(*(_rgb("#33E0B0") + (1.0,)))
    cr.fill()
    return surf


def bar_sliver(w, fill):
    surf, cr = canvas(w, 8)
    pill(cr, w, 8, 3.5, fill)
    return surf


def background():
    W, H = 1366, 768
    surf, cr = canvas(W, H)
    gen.wallpaper(cr, W, H, "boot")
    art.draw_mark(cr, 118, W / 2, 148)
    cr.select_font_face("Noto Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(44)
    cr.move_to(W / 2 - 78, 226)
    art.set_source(cr, tokens.PALETTE["paper"])
    cr.show_text("LUKE")
    cr.set_font_size(16)
    art.set_source(cr, tokens.PALETTE["faint"])
    cr.move_to(W / 2 - 118, 254)
    cr.show_text("PERSONAL OPERATING SYSTEM")
    save(surf, "background-1366x768.png")


def theme_assets():
    save(select_sliver(44), "select_s.png")
    save(select_sliver(2), "select_c.png")
    save(select_sliver(44), "select_e.png")
    for fill, stem in (("#33E0B0", "full"), ("#1B2434", "empty")):
        save(bar_sliver(12, fill), f"progressbar_{stem}_s.png")
        save(bar_sliver(2, fill), f"progressbar_{stem}_c.png")
        save(bar_sliver(12, fill), f"progressbar_{stem}_e.png")


def fonts():
    src = [
        ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", 16, "luke-16"),
        ("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", 26, "luke-26"),
    ]
    for path, size, name in src:
        out = os.path.join(OUT, f"{name}.pf2")
        subprocess.run(["grub-mkfont", "-s", str(size), "-n", name,
                        "-o", out, path], check=True)


def theme_txt():
    txt = """# Luke GRUB theme
title-text: "Luke"
title-font: "luke-26"
title-color: "#EAF1F8"
desktop-image: "background-1366x768.png"
desktop-color: "#080C13"

+ boot_menu {
    left = 12%
    top = 42%
    width = 76%
    height = 30%
    item_font = "luke-16"
    item_color = "#A9B7C9"
    selected_item_color = "#EAF1F8"
    item_icon_space = 0
    item_height = 34
    item_padding = 14
    item_spacing = 8
    selected_item_pixmap_style = "select_*.png"
}

+ label {
    text = "CHOOSE AN OPERATING SYSTEM"
    font = "luke-16"
    color = "#6C7B92"
    align = "center"
    left = 50%-400
    top = 34%
    width = 800
    height = 26
}

+ label {
    id = "__timeout__"
    text = ""
    font = "luke-26"
    color = "#33E0B0"
    align = "center"
    left = 50%-100
    top = 76%
    width = 200
    height = 34
}

+ progress_bar {
    id = "__timeout__"
    left = 22%
    top = 84%
    width = 56%
    height = 8
    bar_style = "progressbar_full_*.png"
    empty_style = "progressbar_empty_*.png"
}

+ label {
    text = "UP / DOWN navigate     ENTER boot     E edit     C console"
    font = "luke-16"
    color = "#6C7B92"
    align = "center"
    left = 50%-420
    top = 92%
    width = 840
    height = 26
}
"""
    with open(os.path.join(OUT, "theme.txt"), "w") as fh:
        fh.write(txt)


def plymouth_assets():
    os.makedirs(PLY, exist_ok=True)
    src = os.path.join(os.path.dirname(BASE), "design", "assets", "brand",
                       "luke-mark-512.png")
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(PLY, "luke-mark.png"))
    with open(os.path.join(PLY, "luke.script"), "w") as fh:
        fh.write("""Window.SetBackgroundTopColor (0.031, 0.043, 0.078);
Window.SetBackgroundBottomColor (0.020, 0.027, 0.047);

mark = Sprite ();
mark.image = Image ("luke-mark.png");
mark.SetPosition (Window.GetWidth () * 0.5 - 120, Window.GetHeight () * 0.26);
mark.SetOpacity (0.96);

bar = ProgressBar (Window.GetWidth () * 0.22, Window.GetHeight () * 0.58,
                   Window.GetWidth () * 0.56, 8);
bar.SetBarShader (Shader.RoundedRectangle (bar, 4));
bar.SetBackgroundShader (Shader.RoundedRectangle (bar, 4));
bar.BarColor = Colours.Custom (0.20, 0.88, 0.69);
bar.BackgroundColor = Colours.Custom (0.09, 0.12, 0.18);
""")
    with open(os.path.join(PLY, "luke.plymouth"), "w") as fh:
        fh.write("""[Plymouth Theme]
Name=Luke
Description=original Luke boot experience
ModuleName=script
""")


def main():
    background()
    theme_assets()
    fonts()
    theme_txt()
    plymouth_assets()
    print("GRUB theme + plymouth theme built ->", OUT)


if __name__ == "__main__":
    main()