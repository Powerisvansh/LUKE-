/* Aurora Bootloader — real-mode boot sector.
 * Loaded by the BIOS at 0x7C00. Here it:
 *   1. banner, A20 enable, RAM size (INT15 E801)
 *   2. reads the kernel (KERN_SECTORS x 512) from disk into 0x10000
 *   3. sets a VBE 1024x768 linear framebuffer (mode 0x118, 4 BPP)
 *   4. writes a boot-params block at 0x8000
 *   5. enters protected mode, copies the kernel to 1M and jumps to it
 *
 * Disk image layout: sector 0 = this boot sector,
 *                    sectors 1..KERN_SECTORS = raw kernel binary.
 * CHS geometry assumed: 1.44MB floppy (80C/2H/18S). */

    .code16
    .section .text, "ax"

    .set BOOT_SEG,       0x7C00      /* runtime segment base            */
    .set PARAM_ADDR,     0x8000      /* boot-params block in low memory */
    .set KERN_LOAD_PHYS, 0x10000     /* BIOS load target                */
    .set KERN_DEST,      0x100000    /* protected-mode copy target      */
    .set SPT,            18          /* sectors/track on 1.44MB floppy */
    .set HEADS,          2

.global start
start:
    cli
    xor %ax, %ax
    mov %ax, %ds
    mov %ax, %es
    mov %ax, %ss
    mov $BOOT_SEG, %sp
    cld
    mov %dl, bootdrv

    mov $msg_boot, %si
    call print

    /* A20 */
    mov $0x2401, %ax
    int $0x15

    /* total RAM in KB (INT15 E801); we never use ss:bp here */
    xor %cx, %cx
    xor %dx, %dx
    mov $0xE801, %ax
    int $0x15
    jc  mem_fail
    test %cx, %cx
    jz  1f
    mov %cx, %ax                /* configured values take precedence */
    mov %dx, %bx
1:
    movzwl %ax, %eax
    movzwl %bx, %ecx
    shll $6, %ecx               /* upper 16MB+ units of 64KB */
    addl %ecx, %eax
    addl $1024, %eax
    movl %eax, (PARAM_ADDR + 24)    /* mem_kb */

    /* load kernel: KERN_SECTORS sectors starting at LBA 1 -> 0x10000 */
    mov $(KERN_LOAD_PHYS >> 4), %ax
    mov %ax, %es
    xor %bx, %bx
    mov $KERN_SECTORS, %di      /* sectors remaining */
    mov $1, %bp                 /* lba */
load_loop:                      /* %bp = lba */
    mov %bp, %ax                /* ax = lba */
    mov $SPT, %cx
    xor %dx, %dx
    div %cx                     /* ax = lba/SPT, dx = lba%SPT */
    inc %dx                     /* dx = sector (1-based) */
    mov %dx, %si                /* save sector */
    mov %ax, %dx                /* dx = lba/SPT */
    mov $HEADS, %cx
    xor %ax, %ax
    xchg %ax, %dx               /* ax = lba/SPT, dx = 0 */
    div %cx                     /* ax = cyl, dx = head */
    mov %dl, %dh                /* dh = head */
    mov %si, %cx                /* cl = sector */
    mov %al, %ch                /* ch = cylinder (fits 8 bits here) */
    mov bootdrv, %dl
    mov $0x0201, %ax            /* BIOS read 1 sector */
    int $0x13
    jc  disk_fail
    mov %es, %ax
    add $0x20, %ax              /* advance 512 bytes */
    mov %ax, %es
    inc %bp
    dec %di
    jnz load_loop

    mov $msg_ok, %si
    call print

    /* VBE: mode 0x118, 1024x768 linear (24bpp stored as 4BPP) */
    xor %ax, %ax                    /* info block goes to ES:2000 = 0x2000 */
    mov %ax, %es
    mov $0x4F01, %ax
    mov $0x0118, %cx
    mov $0x2000, %di
    int $0x10
    cmp $0x004F, %ax
    jne vbe_fail
    xor %ax, %ax                    /* BIOS may clobber DS/ES/DI: reset  */
    mov %ax, %ds
    mov %ax, %es
    mov $0x2000, %si
    movl $0x41555241, %eax       /* "AURA" magic */
    movl %eax, (PARAM_ADDR + 0)
    movl 0x28(%si), %eax         /* framebuffer physical address */
    movl %eax, (PARAM_ADDR + 4)
    movzwl 0x10(%si), %eax       /* bytes per scanline (pitch) */
    movl %eax, (PARAM_ADDR + 8)
    movl $1024, (PARAM_ADDR + 12)
    movl $768,  (PARAM_ADDR + 16)
    movl $4,    (PARAM_ADDR + 20) /* bytes per pixel */

    mov $0x4F02, %ax
    mov $0x4118, %bx            /* 0x118 | 0x4000 (linear frame buffer) */
    int $0x10
    cmp $0x004F, %ax
    jne vbe_fail

    /* --- enter protected mode --- */
    lgdt gdtr
    mov %cr0, %eax
    orl $1, %eax
    mov %eax, %cr0
    ljmp $0x08, $pmode

.code32
pmode:
    mov $0x10, %ax
    mov %ax, %ds
    mov %ax, %es
    mov %ax, %fs
    mov %ax, %gs
    mov %ax, %ss
    mov $BOOT_SEG, %esp

    /* copy kernel 0x10000 -> 0x100000 (KERN_SECTORS sectors) */
    mov $KERN_LOAD_PHYS, %esi
    mov $KERN_DEST, %edi
    mov $(KERN_SECTORS * 128), %ecx   /* dwords */
    rep movsl

    mov $KERN_DEST, %eax
    jmp *%eax
hang:
    cli
    hlt
    jmp hang

/* ---- real-mode helpers ---- */
.code16
print:
    lodsb
    test %al, %al
    jz  1f
    mov $0x0E, %ah
    mov $0x07, %bl
    int $0x10
    jmp print
1:  ret

mem_fail:
    mov $msg_nomem, %si
    call print
    jmp hang
vbe_fail:
    mov $msg_novbe, %si
    call print
    jmp hang
disk_fail:
    mov $msg_nodisk, %si
    call print
    jmp hang

msg_boot:   .asciz "Aurora boot\r\n"
msg_ok:     .asciz "kernel [OK]\r\n"
msg_nomem:  .asciz "ERROR MEM\r\n"
msg_novbe:  .asciz "ERROR VBE\r\n"
msg_nodisk: .asciz "ERROR DISK\r\n"

    .balign 8
gdt:
    .long 0, 0                  /* null descriptor            */
    .long 0x0000FFFF, 0x00CF9A00 /* ring0 code: base0, 4G     */
    .long 0x0000FFFF, 0x00CF9200 /* ring0 data: base0, 4G     */
gdtr:
    .word (gdtr - gdt - 1)
    .long gdt

    .balign 2
bootdrv: .byte 0

    .org 510
    .word 0xAA55
