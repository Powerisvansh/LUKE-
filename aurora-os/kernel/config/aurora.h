/* Aurora OS — common kernel types and version. */
#ifndef AURORA_H
#define AURORA_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

#define AURORA_VERSION "0.1.0"
#define AURORA_NAME    "Aurora OS"
#define AURORA_SCREEN_W  1024u
#define AURORA_SCREEN_H  768u

/* Default OS user account (used by the future lock/login service). */
#define AURORA_DEFAULT_USER "aurora"
#define AURORA_DEFAULT_PASS "aurora"

/* Boot-params block written by the Aurora bootloader at 0x8000. */
#define BOOT_PARAMS_ADDR 0x8000u
#define BOOT_MAGIC       0x41555241u   /* "AURA" */

typedef struct {
    uint32_t magic;
    uint32_t fb_addr;                  /* physical framebuffer address */
    uint32_t fb_pitch;                 /* bytes per scanline */
    uint32_t fb_width;
    uint32_t fb_height;
    uint32_t fb_bpp;                   /* bytes per pixel (4) */
    uint32_t mem_kb;                   /* total RAM in KiB */
} __attribute__((packed)) boot_params_t;

#endif