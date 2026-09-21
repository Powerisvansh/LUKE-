/* Aurora OS — graphics interface. */
#ifndef AURORA_GRAPHICS_H
#define AURORA_GRAPHICS_H

#include <stdint.h>

void fb_init(uint32_t addr, uint32_t width, uint32_t height,
             uint32_t pitch, uint32_t bpp);
uint32_t fb_width(void);
uint32_t fb_height(void);

void fb_fill(uint32_t color);
void fb_fill_rect(int x0, int y0, int w, int h, uint32_t color);
void fb_fill_gradient(uint32_t top, uint32_t bottom);
void fb_blit_glyph(int x, int y, const uint8_t *glyph, int scale,
                   uint32_t fg, uint32_t bg);

#endif