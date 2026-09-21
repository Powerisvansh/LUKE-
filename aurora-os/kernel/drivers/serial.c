/* Aurora OS — COM1 serial console.
 * Used for development/tests: `qemu -nographic -serial stdio` shows logs. */

#include <stdint.h>
#include "portio.h"

#define COM1 0x3F8

void serial_init(void)
{
    outb(COM1 + 1, 0x00);          /* disable interrupts */
    outb(COM1 + 3, 0x80);          /* enable DLAB */
    outb(COM1 + 0, 0x03);          /* divisor 3 -> 38400 baud */
    outb(COM1 + 1, 0x00);
    outb(COM1 + 3, 0x03);          /* 8N1 */
    outb(COM1 + 2, 0xC7);          /* FIFO enable, clear */
    outb(COM1 + 4, 0x0B);          /* DTR+RTS */
}

void serial_putc(char c)
{
    while (!(inb(COM1 + 5) & 0x20))
        ;
    outb(COM1, (uint8_t)c);
}

void serial_write(const char *s)
{
    for (; *s; s++)
        serial_putc(*s);
}