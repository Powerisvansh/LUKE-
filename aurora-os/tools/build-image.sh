#!/bin/sh
# Aurora OS — assemble the boot sector and pack a bootable floppy image.
# usage: build-image.sh <kernel.raw> <out.img>
set -e

RAW=$1
OUT=$2
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

mkdir -p build/boot

SIZE=$(stat -c%s "$RAW")
SECS=$(( (SIZE + 511) / 512 ))

as --32 --defsym KERN_SECTORS=$SECS -c boot/boot.asm -o build/boot/boot.o
ld -m elf_i386 -T boot/boot.ld build/boot/boot.o -o build/boot/boot.elf
objcopy -O binary --pad-to 512 build/boot/boot.elf build/bootsec.bin

# image = boot sector + kernel sectors, padded to a full 1.44MB floppy
{
    cat build/bootsec.bin
    dd if="$RAW" bs=512 conv=sync status=none
} > build/aurora.img.tmp
truncate -s 1474560 build/aurora.img.tmp
mv build/aurora.img.tmp "$OUT"

echo "image built: $OUT ($((1 + SECS)) sectors used)"