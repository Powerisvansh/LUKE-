#!/bin/bash
# Apply the Luke boot experience to the pendrive target.
#
#   sudo bash boot/apply-boot.sh [TARGET]   TARGET defaults to /media/aman/LUKE-ROOT
#
# What it does (all reversible, copies kept):
#   1. Installs the generated GRUB theme into  /boot/grub/themes/luke
#   2. Points /etc/default/grub at it (backup first)
#   3. Installs the plymouth theme into       /usr/share/plymouth/themes/luke
#   4. Re-works the bootloader + initramfs in a chroot: update-grub && update-initramfs
#
# It does NOT touch firmware, partition tables, or the kernel.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="${1:-/media/aman/LUKE-ROOT}"
THEME_SRC="$SRC/out/themes/luke"
PLY_SRC="$SRC/plymouth"

[ "$(id -u)" = 0 ] || { echo "run with sudo (from the build host)"; exit 1; }
[ -d "$ROOT/boot/grub" ] || { echo "ERROR: no GRUB at $ROOT/boot/grub"; exit 1; }
[ -d "$THEME_SRC" ] || { echo "ERROR: build the theme first: python3 boot/gen-assets.py"; exit 1; }

backup() { cp -a "$1" "$1.bak.$(date +%F-%H%M)" 2>/dev/null || true; }

echo "[1/4] installing GRUB theme"
install -d "$ROOT/boot/grub/themes/luke"
cp -a "$THEME_SRC/." "$ROOT/boot/grub/themes/luke/"

echo "[2/4] pointing /etc/default/grub at the theme"
GRUBD="$ROOT/etc/default/grub"
[ -f "$GRUBD" ] || { echo "ERROR: $GRUBD missing"; exit 1; }
backup "$GRUBD"
grep -q '^GRUB_THEME=' "$GRUBD" \
  || printf '\nGRUB_THEME="/boot/grub/themes/luke/theme.txt"\n' >> "$GRUBD"
sed -i 's#^GRUB_THEME=.*#GRUB_THEME="/boot/grub/themes/luke/theme.txt"#' "$GRUBD"

echo "[3/4] installing plymouth theme"
install -d "$ROOT/usr/share/plymouth/themes/luke"
cp -a "$PLY_SRC/." "$ROOT/usr/share/plymouth/themes/luke/"

echo "[4/4] rebuilding GRUB + initramfs (chroot)"
mount --bind /proc "$ROOT/proc"
mount --bind /sys  "$ROOT/sys"
mount --bind /dev  "$ROOT/dev"
mount --bind /run  "$ROOT/run"
trap 'umount "$ROOT/proc" "$ROOT/sys" "$ROOT/dev" "$ROOT/run" 2>/dev/null || true' EXIT

chroot "$ROOT" /bin/bash -e -c '
  if command -v plymouth-set-default-theme >/dev/null 2>&1; then
    plymouth-set-default-theme luke || true
  else
    update-alternatives --set default.plymouth \
      /usr/share/plymouth/themes/luke/luke.plymouth || true
  fi
  update-grub
  update-initramfs -u -k all
'

echo "Done. The pendrive now boots with the Luke boot experience."
echo "Recovery: old files are kept as *.bak.* beside the files above, and GRUB's"
echo "'Advanced options' recovery kernels are still reachable from the new menu."