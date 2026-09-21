/* Aurora OS — linker script.
 * Load at 1M, layout matching the boot/boot.asm + kernel sections. */

ENTRY(_start)

SECTIONS
{
    . = 1M;

    .multiboot : { KEEP(*(.multiboot)) }

    .text : ALIGN(4K) { *(.text*) }

    .rodata : ALIGN(4K) { *(.rodata*) }

    .data : ALIGN(4K) { *(.data*) }

    .bss : ALIGN(4K) {
        *(COMMON)
        *(.bss*)
        stack_top = ABSOLUTE(.) + 0x8000;
    }

    /DISCARD/ : { *(.comment) *(.eh_frame) }
}