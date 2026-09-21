# Aurora OS

An original, Android-inspired PC operating system — built from the ground up,
not a copy of any existing OS.

```
BIOS
 ↓
Aurora Bootloader
 ↓
Aurora Kernel
 ↓
System Services       (planned)
 ↓
Graphics System
 ↓
Aurora UI Framework   (planned)
 ↓
Aurora Shell          (planned)
```

## Status — Phase 1 (minimum bootable kernel)

Works today:

* Aurora Bootloader (real-mode boot sector loaded by the BIOS)
  * RAM detection (INT15 E801)
  * loads the kernel from disk into memory
  * sets a VBE 1024x768 linear framebuffer
  * enters protected mode and jumps to the kernel
* Aurora Kernel (32-bit, freestanding)
  * framebuffer driver + original 5x7 bitmap font
  * Aurora boot screen (gradient, brand panel, system info)
  * PS/2 keyboard driver (polled, scancode set 1)
  * COM1 serial console for development
* Build system (`make`, `make run`, `make debug`, `make test`, `make image`)

## Build & run

Requires: `gcc`, `as`, `ld`, `objcopy`, `qemu-system-i386`, `make`.

```bash
cd aurora-os
make               # builds build/aurora.img via make/test/... targets
make run           # boot in QEMU (graphical)
make test          # headless smoke test over serial
make debug         # QEMU with GDB stub on :1234
```

The kernel boots from a 1.44MB floppy image. `qemu-system-i386 -m 256
-drive file=build/aurora.img,format=raw,if=floppy`.

## Layout

```text
aurora-os/
├── boot/     Aurora Bootloader (boot sector + linker script)
├── kernel/   kernel entry, main, drivers, graphics, config
├── graphics/ (shared graphics interfaces)
├── tools/    build-image.sh
└── docs/     (roadmap)
```

## Roadmap

Phase 2: IDT/GDT, PIT timer, interrupt-driven keyboard, E820 memory map.
Phases 3-14 follow the project plan (storage, processes, UI framework,
home screen, launcher, apps, services, networking, SDK, installer).