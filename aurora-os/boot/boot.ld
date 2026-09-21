/* Aurora Bootloader — boot sector layout.
 * VMA 0x7C00 (where the BIOS loads it), LMA 0 so the raw binary
 * is exactly 512 bytes. */

ENTRY(start)

SECTIONS
{
    . = 0x7C00;
    .text : AT(0) {
        *(.text*)
    }
    /DISCARD/ : { *(.note.GNU-stack) *(.comment) }
}