/* Aurora OS — linear framebuffer drawing.
 * Minimal set: fill, vertical gradient, bars and text blitting helpers. */

#include <stdint.h>
#include "graphics.h"

typedef struct {
    uint32_t addr;
    uint32_t width;
    uint32_t height;
    uint32_t pitch;
    uint32_t bpp;
} fb_t;

static fb_t fb;

void fb_init(uint32_t addr, uint32_t width, uint32_t height,
             uint32_t pitch, uint32_t bpp)
{
    fb.addr = addr;
    fb.width = width;
    fb.height = height;
    fb.pitch = pitch;
    fb.bpp = bpp;
}

uint32_t fb_width(void)  { return fb.width; }
uint32_t fb_height(void) { return fb.height; }

static uint32_t *px(int x, int y)
{
    /* LFB modes store each pixel in 4 bytes even at 24bpp. */
    return (uint32_t *)(fb.addr + (uint32_t)y * fb.pitch + (uint32_t)x * 4u);
}

static uint32_t blend(uint32_t a, uint32_t b, uint32_t t)
{
    /* t in 0..256, blend a towards b */
    uint32_t r = ((a & 0xFF) * (256 - t) + (b & 0xFF) * t) >> 8;
    uint32_t g = (((a >> 8) & 0xFF) * (256 - t) + ((b >> 8) & 0xFF) * t) >> 8;
    uint32_t bl = (((a >> 16) & 0xFF) * (256 - t) + ((b >> 16) & 0xFF) * t) >> 8;
    return r | (g << 8) | (bl << 16);
}

void fb_fill(uint32_t color)
{
    for (uint32_t y = 0; y < fb.height; y++)
        for (uint32_t x = 0; x < fb.width; x++)
            px(x, y)[0] = color;
}

void fb_fill_rect(int x0, int y0, int w, int h, uint32_t color)
{
    for (int y = y0; y < y0 + h && y < (int)fb.height; y++)
        for (int x = x0; x < x0 + w && x < (int)fb.width; x++)
            if (x >= 0 && y >= 0)
                px(x, y)[0] = color;
}

void fb_fill_gradient(uint32_t top, uint32_t bottom)
{
    for (uint32_t y = 0; y < fb.height; y++)
        for (uint32_t x = 0; x < fb.width; x++)
            px(x, y)[0] = blend(top, bottom, (uint32_t)(y * 256 / fb.height));
}

void fb_blit_glyph(int x, int y, const uint8_t *glyph, int scale,
                   uint32_t fg, uint32_t bg)
{
    for (int row = 0; row < 7; row++) {
        uint8_t bits = glyph[row];
        for (int col = 0; col < 5; col++) {
            uint32_t c = (bits & (0x10 >> col)) ? fg : bg;
            fb_fill_rect(x + col * scale, y + row * scale, scale, scale, c);
        }
    }
}