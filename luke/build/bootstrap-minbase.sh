#!/usr/bin/env bash
set -Eeuo pipefail

TARGET=/mnt/luke
DATA_DEVICE=
USERNAME=aman
SUITE=bookworm
MIRROR=http://deb.debian.org/debian

usage() { echo "Usage: $0 --target DIR --data-device UUID_OR_DEVICE [--username NAME] [--suite SUITE] [--mirror URL]" >&2; exit 2; }
while (($#)); do
  case "$1" in
    --target) TARGET=$2; shift 2;;
    --data-device) DATA_DEVICE=$2; shift 2;;
    --username) USERNAME=$2; shift 2;;
    --suite) SUITE=$2; shift 2;;
    --mirror) MIRROR=$2; shift 2;;
    *) usage;;
  esac
done

[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
[[ -n $DATA_DEVICE ]] || usage
command -v debootstrap >/dev/null || { echo "Install debootstrap first." >&2; exit 1; }
[[ -d $TARGET ]] || mkdir -p "$TARGET"

mounted=()
cleanup() {
  for path in "${mounted[@]:-}"; do
    mountpoint -q "$path" && umount -R "$path" || true
  done
}
trap cleanup EXIT

if [[ ! -e "$TARGET/bin/bash" ]]; then
  debootstrap --variant=minbase "$SUITE" "$TARGET" "$MIRROR"
fi

mount --rbind /dev "$TARGET/dev"; mount --make-rslave "$TARGET/dev"; mounted+=("$TARGET/dev")
mount -t proc proc "$TARGET/proc"; mounted+=("$TARGET/proc")
mount --rbind /sys "$TARGET/sys"; mount --make-rslave "$TARGET/sys"; mounted+=("$TARGET/sys")
mount --rbind /run "$TARGET/run"; mount --make-rslave "$TARGET/run"; mounted+=("$TARGET/run")
install -m 644 /etc/resolv.conf "$TARGET/etc/resolv.conf"

cat > "$TARGET/root/luke-stage1.sh" <<EOF
#!/bin/bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends systemd systemd-sysv dbus sudo \
  network-manager wpasupplicant ca-certificates locales linux-image-amd64 \
  initramfs-tools firmware-linux-free nftables
echo 'luke' > /etc/hostname
printf '127.0.0.1 localhost\n127.0.1.1 luke\n' > /etc/hosts
locale-gen en_US.UTF-8
useradd --create-home --shell /bin/bash --groups sudo,video,render,input '$USERNAME' 2>/dev/null || true
# useradd leaves the account locked until the administrator sets a password.
install -d -m 0755 /data
DATA_DEVICE='$DATA_DEVICE'
if [[ -e "\$DATA_DEVICE" ]]; then
  DATA_UUID=\$(blkid -s UUID -o value "\$DATA_DEVICE" || true)
  [[ -n "\$DATA_UUID" ]] && printf 'UUID=%s /data ext4 defaults,noatime,nodev,nosuid 0 2\\n' "\$DATA_UUID" >> /etc/fstab
fi
systemctl enable NetworkManager
update-initramfs -c -k all || update-initramfs -u -k all
rm -f /root/luke-stage1.sh
EOF
chmod 700 "$TARGET/root/luke-stage1.sh"
chroot "$TARGET" /root/luke-stage1.sh
echo "Rootfs prepared at $TARGET. Set a password and install the bootloader before first boot."