/* Aurora OS — text drawing on the framebuffer. */
#ifndef AURORA_FONT_H
#define AURORA_FONT_H

#include <stdint.h>

void fb_draw_text(int x, int y, const char *s, int scale,
                  uint32_t fg, uint32_t bg);

#endif