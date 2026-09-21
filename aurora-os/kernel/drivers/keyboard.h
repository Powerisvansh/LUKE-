/* Aurora OS — PS/2 keyboard driver. */
#ifndef AURORA_DRV_KEYBOARD_H
#define AURORA_DRV_KEYBOARD_H

void keyboard_init(void);
char keyboard_read(void);   /* 0 = no event / ignored key */

#endif