# Aurora OS — build system.
#   make            build build/aurora.img (bootable floppy image)
#   make kernel     build the raw kernel only
#   make run        boot Aurora OS in QEMU (graphical)
#   make debug      boot in QEMU with GDB stub at :1234
#   make test       headless QEMU smoke test over serial
#   make clean

CC      := gcc
LD      := ld
CFLAGS  := -m32 -ffreestanding -fno-pic -fno-builtin -fno-stack-protector \
           -Wall -Wextra -O2 -I kernel
LDFLAGS := -m elf_i386 -nostdlib

KERNEL_OBJS := kernel/entry.o \
               kernel/main.o \
               kernel/graphics/fb.o \
               kernel/graphics/font.o \
               kernel/drivers/keyboard.o \
               kernel/drivers/serial.o

KERN_ELF := build/kernel.bin
KERN_RAW := build/kernel.raw
IMG      := build/aurora.img

all: $(IMG)

$(KERN_ELF): $(KERNEL_OBJS) kernel/link.ld
	@mkdir -p build
	$(LD) $(LDFLAGS) -T kernel/link.ld -o $@ $(KERNEL_OBJS)

$(KERN_RAW): $(KERN_ELF)
	objcopy -O binary $< $@

$(IMG): $(KERN_RAW) boot/boot.asm boot/boot.ld tools/build-image.sh
	chmod +x tools/build-image.sh
	./tools/build-image.sh $(KERN_RAW) $@

kernel: $(KERN_RAW)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.asm
	as --32 -c -o $@ $<

image: $(IMG)
	@echo "image ready: $<"

check: $(IMG)
	@od -An -tx1 -j510 -N2 $(IMG) | grep -q "55 aa" && echo "OK: boot sector signature present" \
	 || { echo "FAIL: bad boot sector signature"; exit 1; }

HDA := -drive file=$(IMG),format=raw,if=floppy

run: $(IMG) check
	qemu-system-i386 -m 256 $(HDA)

debug: $(IMG) check
	qemu-system-i386 -m 256 -s -S $(HDA)

test: $(IMG) check
	@timeout 8 qemu-system-i386 -m 256 -display none -serial stdio $(HDA) 2>/dev/null | grep -q "type below" \
	 && echo "AURORA BOOT OK" || { echo "AURORA BOOT FAILED"; exit 1; }

clean:
	rm -f $(KERNEL_OBJS) $(KERN_ELF) $(KERN_RAW) $(IMG)
	rm -rf build

.PHONY: all image kernel run debug test check clean