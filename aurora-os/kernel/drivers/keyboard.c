/* Aurora OS — PS/2 keyboard driver.
 * Phase 1: polled scancode-set-1 input with Shift handling. */

#include <stdint.h>
#include <stdbool.h>
#include "portio.h"

#define KBD_DATA    0x60
#define KBD_STATUS  0x64
#define KBD_OUT_FULL 0x01

/* scancode -> unshifted ascii, index 0..57 (key-up entries are outside). */
static const char scancode_map[58] = {
     0,   0, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
    '-', '=', '\b', '\t', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i',
    'o', 'p', '[', ']', '\n', 0, 'a', 's', 'd', 'f', 'g', 'h',
    'j', 'k', 'l', ';', '\'', '`', 0, '\\', 'z', 'x', 'c', 'v',
    'b', 'n', 'm', ',', '.', '/', 0, '*', 0, ' '
};

static bool shift_pressed;

static char shift_char(char c)
{
    if (c >= 'a' && c <= 'z')
        return (char)(c - 'a' + 'A');
    switch (c) {
        case '1': return '!'; case '2': return '@'; case '3': return '#';
        case '4': return '$'; case '5': return '%'; case '6': return '^';
        case '7': return '&'; case '8': return '*'; case '9': return '(';
        case '0': return ')'; case '-': return '_'; case '=': return '+';
        case '[': return '{'; case ']': return '}'; case ';': return ':';
        case '\'': return '"'; case '`': return '~'; case '\\': return '|';
        case ',': return '<'; case '.': return '>'; case '/': return '?';
        default: return c;
    }
}

void keyboard_init(void)
{
    shift_pressed = false;
}

/* Non-blocking: returns an ascii char, or 0 for no event /
 * unidentified key. Handles key-up by stripping bit 7. */
char keyboard_read(void)
{
    if (!(inb(KBD_STATUS) & KBD_OUT_FULL))
        return 0;

    uint8_t sc = inb(KBD_DATA);

    if (sc & 0x80) {
        uint8_t up = sc & 0x7F;
        if (up == 0x2A || up == 0x36)
            shift_pressed = false;
        return 0;
    }

    if (sc == 0x2A || sc == 0x36) {
        shift_pressed = true;
        return 0;
    }
    if (sc == 0x1D || sc == 0x38 || sc == 0xE0 || sc == 0xE1)
        return 0;                /* ctrl/alt/extended: ignored in phase 1 */

    if (sc >= 58)
        return 0;

    char c = scancode_map[sc];
    return shift_pressed ? shift_char(c) : c;
}