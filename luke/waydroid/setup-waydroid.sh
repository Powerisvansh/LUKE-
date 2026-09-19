#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
command -v apt-get >/dev/null || { echo "This installer expects an apt-based rootfs." >&2; exit 1; }

apt-get update
apt-get install -y --no-install-recommends lxc lxc-templates dnsmasq nftables curl ca-certificates
apt-get install -y waydroid

modprobe binder_linux devices=binder,hwbinder,vndbinder 2>/dev/null || true
if [[ ! -e /dev/binderfs/binder ]]; then
  mkdir -p /dev/binderfs
  mount -t binder binder /dev/binderfs 2>/dev/null || true
fi
[[ -e /dev/binderfs/binder ]] || {
  echo "Waydroid cannot start: binderfs is unavailable in the running kernel." >&2
  echo "Enable binder_linux/binderfs and reboot; do not continue by installing a VM." >&2
  exit 1
}

install -d -m 0755 /etc/systemd/system
install -m 0644 "$(dirname "$0")/dev-binderfs.mount" /etc/systemd/system/dev-binderfs.mount
install -m 0644 "$(dirname "$0")/luke-waydroid.service" /etc/systemd/system/luke-waydroid.service
install -d -m 0755 /etc/nftables.d
install -m 0644 "$(dirname "$0")/waydroid-nftables.conf" /etc/nftables.d/waydroid.nft
systemctl daemon-reload
systemctl enable luke-waydroid.service
echo "Installed Waydroid prerequisites. Run 'waydroid init -f' as the desktop user, then reboot."