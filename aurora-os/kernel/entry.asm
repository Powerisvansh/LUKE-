/* Aurora OS — kernel entry point (placed first in the image).
 * The bootloader copies us to 1M and jumps to _start. */

.section .text, "ax"
.code32
.global _start
_start:
    cli
    movl $(stack_top), %esp
    call kernel_main
hang:
    cli
    hlt
    jmp hang

.section .bss, "aw"
.space 0x8000                        /* kernel stack */
stack_top:

.section .note.GNU-stack,"",@progbits
