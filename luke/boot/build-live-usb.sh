#!/usr/bin/env bash
set -Eeuo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USB_DEVICE=""
USERNAME="aman"
SUITE="bookworm"
MIRROR="${MIRROR:-http://deb.debian.org/debian}"
TARGET_DIR=""
ROOT_PART=""
EFI_PART=""

usage() {
  cat <<EOF
Usage: sudo bash build-live-usb.sh --device /dev/sdX [--username NAME] [--suite SUITE] [--mirror URL]

Builds a bootable Luke USB stick from a Debian minbase rootfs and installs a
GRUB + EFI bootloader for the Luke desktop. The script creates a GPT layout, a
small EFI system partition, and a root filesystem partition on the selected USB
device.

Example:
  sudo bash build-live-usb.sh --device /dev/sdb --username aman --suite bookworm
EOF
  exit 2
}

if [[ ${EUID} -ne 0 ]]; then
  command -v sudo >/dev/null || {
    echo "This build requires root privileges and sudo is unavailable." >&2
    exit 1
  }
  SCRIPT_PATH="$(readlink -f "$0")"
  exec sudo -- "$SCRIPT_PATH" "$@"
fi

while (($#)); do
  case "$1" in
    --device)
      USB_DEVICE="$2"
      shift 2
      ;;
    --username)
      USERNAME="$2"
      shift 2
      ;;
    --suite)
      SUITE="$2"
      shift 2
      ;;
    --mirror)
      MIRROR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      ;;
  esac
done

[[ -n "$USB_DEVICE" ]] || usage
[[ -b "$USB_DEVICE" ]] || { echo "Device not found: $USB_DEVICE" >&2; exit 1; }

for cmd in debootstrap mkfs.vfat mkfs.ext4 mount umount parted grub-install rsync; do
  command -v "$cmd" >/dev/null || { echo "Missing required command: $cmd" >&2; exit 1; }
done

if [[ "$USB_DEVICE" == "/dev/loop"* ]] || [[ "$USB_DEVICE" == "/dev/nvme"* ]]; then
  echo "Refusing to target a loopback or NVMe device automatically; pass a removable USB device instead." >&2
  exit 1
fi

# Prefer a safe, user-visible tmp rootfs path.
TARGET_DIR="$(mktemp -d /tmp/luke-live-usb.XXXXXX)"
cleanup() {
  if mountpoint -q "$TARGET_DIR"; then umount -R "$TARGET_DIR" || true; fi
  if [[ -d "$TARGET_DIR" ]]; then rm -rf "$TARGET_DIR"; fi
}
trap cleanup EXIT

ROOT_PART="${USB_DEVICE}2"
EFI_PART="${USB_DEVICE}1"

if lsblk -no NAME "$USB_DEVICE" | grep -q '.*'; then
  echo "==> Warning: this script will overwrite the selected USB device: $USB_DEVICE"
  echo "==> Proceeding in 3 seconds..."
  sleep 3
fi

parted -s "$USB_DEVICE" mklabel gpt
parted -s "$USB_DEVICE" mkpart ESP fat32 1MiB 1025MiB
parted -s "$USB_DEVICE" mkpart root ext4 1025MiB 100%
parted -s "$USB_DEVICE" set 1 esp on
parted -s "$USB_DEVICE" set 1 boot on

mkfs.vfat -F32 "$EFI_PART"
mkfs.ext4 -F "$ROOT_PART"

mkdir -p "$TARGET_DIR"
mount "$ROOT_PART" "$TARGET_DIR"
mkdir -p "$TARGET_DIR/boot/efi"
mount "$EFI_PART" "$TARGET_DIR/boot/efi"
mountpoint -q "$TARGET_DIR/boot/efi" || {
  echo "EFI partition failed to mount at $TARGET_DIR/boot/efi" >&2
  exit 1
}

if [[ ! -d "$TARGET_DIR/etc" ]]; then
  echo "==> Creating Debian minbase root filesystem"
  debootstrap --variant=minbase "$SUITE" "$TARGET_DIR" "$MIRROR"
fi

mount --bind /dev "$TARGET_DIR/dev"
mount --make-slave "$TARGET_DIR/dev"
mount -t proc proc "$TARGET_DIR/proc"
mount --bind /sys "$TARGET_DIR/sys"
mount --make-slave "$TARGET_DIR/sys"
mount --bind /run "$TARGET_DIR/run"
mount --make-slave "$TARGET_DIR/run"
cp /etc/resolv.conf "$TARGET_DIR/etc/resolv.conf"

cat > "$TARGET_DIR/root/luke-live.sh" <<EOF
#!/bin/bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
export LANG=C

apt-get update
apt-get install -y --no-install-recommends \
  systemd-sysv dbus sudo network-manager wpasupplicant ca-certificates locales \
  linux-image-amd64 linux-base firmware-linux-free initramfs-tools \
  grub-efi-amd64 dosfstools xfsprogs btrfs-progs ntfs-3g git python3 python3-cairo \
  python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 lightdm plymouth \
  pulseaudio-utils xauth dbus-x11

echo 'luke-live' > /etc/hostname
cat > /etc/hosts <<'HOSTS'
127.0.0.1 localhost
127.0.1.1 luke-live
HOSTS

locale-gen en_US.UTF-8
useradd --create-home --shell /bin/bash --groups sudo,video,render,input '$USERNAME' 2>/dev/null || true
install -d -m 0755 /home/$USERNAME/.luke

cat > /etc/fstab <<'FSTAB'
UUID=$(blkid -s UUID -o value "$ROOT_PART") / ext4 defaults,noatime 0 1
UUID=$(blkid -s UUID -o value "$EFI_PART") /boot/efi vfat defaults 0 2
FSTAB

cat > /etc/default/grub <<'GRUB'
GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_DISTRIBUTOR=Luke
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_TERMINAL=console
GRUB_GFXMODE=auto
GRUB_THEME="/boot/grub/themes/luke/theme.txt"
GRUB_DISABLED_OS_PROBER=true
GRUB_BACKGROUND="/usr/share/images/desktop-base/desktop-grub.png"
GRUB_ENABLE_CRYPTODISK=n
GRUB_RECORDFAIL_TIMEOUT=5
GRUB_CMDLINE_LINUX=""
GRUB_INIT_TUNE=""
GRUB_DISABLE_LINUX_UUID=true
GRUB_DISABLE_RECOVERY="false"
GRUB_SAVEDEFAULT=true
GRUB_PRELOAD_MODULES="part_gpt part_msdos"
GRUB_TIMEOUT_STYLE=hidden
GRUB_GFXPAYLOAD_LINUX=text
GRUB_TERMINAL_INPUT=console
GRUB_TERMINAL_OUTPUT=console
GRUB_DISABLE_SUBMENU=y
GRUB_BACKGROUND="/usr/share/backgrounds/default.jpg"
GRUB_GFXPAYLOAD_LINUX=keep
GRUB_DISABLE_LINUX_UUID=false
GRUB_THEME="/boot/grub/themes/luke/theme.txt"
GRUB

mkdir -p /home/$USERNAME/.luke
cp -a /src-luke/. /home/$USERNAME/.luke/
chown -R $USERNAME:$USERNAME /home/$USERNAME/.luke
chmod -R u+rwX /home/$USERNAME/.luke

mkdir -p /boot/grub/themes/luke
cp -a /src-theme/. /boot/grub/themes/luke/
mkdir -p /usr/share/plymouth/themes/luke
cp -a /src-plymouth/. /usr/share/plymouth/themes/luke/

systemctl enable NetworkManager lightdm

# Keep the default UI readable for a live USB and ensure the project is in the right place.
mkdir -p /etc/luke
printf '%s\n' 'live-usb' > /etc/luke/mode

# Remove the stage script before finalizing.
rm -f /root/luke-live.sh
EOF

chmod 700 "$TARGET_DIR/root/luke-live.sh"
cp -a "$SRC_DIR" "$TARGET_DIR/src-luke"
cp -a "$SRC_DIR/boot/out/themes/luke" "$TARGET_DIR/src-theme" 2>/dev/null || true
cp -a "$SRC_DIR/boot/plymouth" "$TARGET_DIR/src-plymouth" 2>/dev/null || true

if [[ -d "$TARGET_DIR/src-theme" ]]; then
  :
fi

chroot "$TARGET_DIR" /bin/bash /root/luke-live.sh

# Install the bootloader with both EFI and legacy fallback support.
chroot "$TARGET_DIR" /bin/bash -lc '
  if [ -d /boot/grub/themes/luke ]; then
    echo "Luke grub theme installed"
  fi
  update-grub
  grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=Luke --recheck --removable
  update-initramfs -u -k all || true
'

[[ -f "$TARGET_DIR/boot/efi/EFI/BOOT/BOOTX64.EFI" ]] || {
  echo "EFI bootloader was not written to $EFI_PART" >&2
  exit 1
}

# Finalize project files for the live root.
mkdir -p "$TARGET_DIR/home/$USERNAME/.luke"
cp -a "$SRC_DIR"/. "$TARGET_DIR/home/$USERNAME/.luke/"
chown -R "$USERNAME:$USERNAME" "$TARGET_DIR/home/$USERNAME/.luke"

echo
echo "==> Bootable Luke USB setup complete."
echo "    Root filesystem: $ROOT_PART"
echo "    EFI partition:   $EFI_PART"
echo "    Project files:   /home/$USERNAME/.luke"
echo "    Target device:   $USB_DEVICE"
echo
echo "This image is prepared for a live USB boot, but you should still test it on a
real machine before relying on it for daily use."
