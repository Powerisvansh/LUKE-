/* Aurora OS — x86 port I/O. */
#ifndef AURORA_DRV_PORTIO_H
#define AURORA_DRV_PORTIO_H

#include <stdint.h>

static inline uint8_t inb(uint16_t port)
{
    uint8_t v;
    __asm__ volatile("inb %1, %0" : "=a"(v) : "Nd"(port));
    return v;
}

static inline void outb(uint16_t port, uint8_t val)
{
    __asm__ volatile("outb %0, %1" : : "a"(val), "Nd"(port));
}

static inline void io_wait(void)
{
    outb(0x80, 0);
}

#endif