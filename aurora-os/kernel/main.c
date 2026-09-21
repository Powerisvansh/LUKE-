/* Aurora OS — kernel main.
 * Phase 1: read the boot-params from the Aurora bootloader, bring up the
 * framebuffer, paint the first Aurora boot screen and poll the keyboard. */

#include <stdint.h>
#include "config/aurora.h"
#include "drivers/serial.h"
#include "drivers/keyboard.h"
#include "graphics/graphics.h"
#include "graphics/font.h"

/* Aurora palette — 0xAARRGGBB (memory LE = BBGGRR, the VBE 24bpp order). */
#define RGB(r, g, b) (0x00u | ((uint32_t)(r) << 16) | ((uint32_t)(g) << 8) | (uint32_t)(b))
#define C_BG_TOP   RGB(26, 32, 58)
#define C_BG_BOT   RGB(52, 38, 78)
#define C_BAR      RGB(16, 20, 32)
#define C_PANEL    RGB(20, 26, 38)
#define C_ACCENT   RGB(90, 180, 245)
#define C_TEXT     RGB(240, 245, 255)
#define C_DIM      RGB(160, 170, 190)
#define C_BORDER   RGB(45, 60, 85)

static char *u32dec(uint32_t v, char *out)
{
    char tmp[12];
    int i = 0;
    do { tmp[i++] = (char)('0' + v % 10); v /= 10; } while (v);
    int j = 0;
    while (i) out[j++] = tmp[--i];
    out[j] = 0;
    return out;
}

static void bootscreen(const boot_params_t *bp)
{
    char line[40];

    fb_fill_gradient(C_BG_TOP, C_BG_BOT);
    fb_fill_rect(0, 0, AURORA_SCREEN_W, 30, C_BAR);
    fb_fill_rect(0, AURORA_SCREEN_H - 30, AURORA_SCREEN_W, 30, C_BAR);

    fb_draw_text(16, 10, AURORA_NAME, 1, C_DIM, C_BAR);
    fb_draw_text(AURORA_SCREEN_W - 54, 10, "BOOT v0.1", 1, C_ACCENT, C_BAR);

    /* centered brand panel */
    fb_fill_rect(344, 250, 336, 150, C_PANEL);
    fb_fill_rect(344, 250, 336, 2, C_ACCENT);
    fb_draw_text(392, 280, AURORA_NAME, 4, C_TEXT, C_PANEL);
    fb_draw_text(404, 370, "D E S K T O P   O S", 2, C_ACCENT, C_PANEL);

    fb_draw_text(380, 460, "FRAMEBUFFER INITIALIZED", 2, C_DIM, C_BG_BOT);
    fb_draw_text(428, 496, "KEYBOARD READY", 2, C_DIM, C_BG_BOT);

    uint32_t mem_mb = bp->mem_kb / 1024u;
    fb_draw_text(24, 548, "MEMORY", 1, C_DIM, C_BG_BOT);
    fb_draw_text(80, 550, u32dec(mem_mb, line), 1, C_TEXT, C_BG_BOT);
    fb_draw_text(150, 550, "MB", 1, C_DIM, C_BG_BOT);

    fb_draw_text(24, 566, "DISPLAY", 1, C_DIM, C_BG_BOT);
    fb_draw_text(80, 568, u32dec(bp->fb_width, line), 1, C_TEXT, C_BG_BOT);
    fb_draw_text(104, 568, "x", 1, C_DIM, C_BG_BOT);
    fb_draw_text(114, 568, u32dec(bp->fb_height, line), 1, C_TEXT, C_BG_BOT);
    fb_draw_text(150, 568, "@", 1, C_DIM, C_BG_BOT);
    fb_draw_text(160, 568, "32", 1, C_TEXT, C_BG_BOT);

    fb_draw_text(24, 600, "TYPE BELOW:", 1, C_DIM, C_BG_BOT);
}

static void echo_boxed(const char *line)
{
    fb_fill_rect(24, 620, 976, 30, C_PANEL);
    fb_fill_rect(24, 620, 976, 1, C_BORDER);
    fb_draw_text(32, 626, line, 1, C_TEXT, C_PANEL);
}

int kernel_main(void)
{
    char buf[80];

    serial_init();
    serial_write("[aurora] Aurora kernel " AURORA_VERSION " booting\n");

    boot_params_t *bp = (boot_params_t *)BOOT_PARAMS_ADDR;
    if (bp->magic != BOOT_MAGIC) {
        serial_write("[aurora] FATAL: bad boot params magic\n");
        for (;;)
            ;
    }

    fb_init(bp->fb_addr, bp->fb_width, bp->fb_height, bp->fb_pitch,
            bp->fb_bpp);
    serial_write("[aurora] fb_addr=");
    serial_write(u32dec(bp->fb_addr, buf));
    serial_write(":\n");
    serial_write("[aurora] framebuffer ");
    serial_write(u32dec(bp->fb_width, buf));
    serial_write("x");
    serial_write(u32dec(bp->fb_height, buf));
    serial_write(" ready\n");

    keyboard_init();
    serial_write("[aurora] keyboard ready\n");

    bootscreen(bp);
    serial_write("[aurora] type below (q to halt)\n");

    int len = 0;
    for (;;) {
        char c = keyboard_read();
        if (!c)
            continue;

        if (c == '\n') {
            buf[len] = 0;
            serial_write("[key] ");
            serial_write(buf);
            serial_write("\n");
            if (len == 1 && (buf[0] == 'q' || buf[0] == 'Q')) {
                serial_write("[aurora] powering off (halt)\n");
                __asm__ volatile("cli; hlt");
            }
            len = 0;
            buf[0] = 0;
            echo_boxed("");
            continue;
        }
        if (c == '\b') {
            if (len > 0)
                len--;
            buf[len] = 0;
            echo_boxed(buf);
            continue;
        }
        if (len < 79) {
            buf[len++] = c;
            buf[len] = 0;
            echo_boxed(buf);
        }
    }
}