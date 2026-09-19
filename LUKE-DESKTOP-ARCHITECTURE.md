# Luke Desktop Architecture

This is the implementation guide for turning a Debian/Ubuntu `debootstrap --variant=minbase` root filesystem into a small, rebuildable Luke workstation. It keeps the operating system on a root partition, mounts personal data separately, uses a Wayland session, and runs Android applications through Waydroid/LXC rather than a virtual machine.

The files beside this document are templates, not a blind installer. Read each `WARNING` and adapt device names, distribution codename, GPU driver, username, and firmware package before running anything as root.

## 0. Target architecture

```text
UEFI/GRUB -> Linux kernel + initramfs -> systemd
                                  |-> Wayland compositor (Wayfire)
                                  |-> Luke shell/panel/launcher
                                  |-> Waydroid container -> Android userspace
root ext4 (/): immutable-ish OS, packages, /home if desired
data ext4 (/data): /home/<user>/Data, Downloads, media and rebuild-safe files
```

Waydroid is not a VM: Android's userspace runs in a Linux container and shares the host kernel. It still needs a compatible kernel, a working Wayland session, GPU acceleration, and a maintained Android image. Hardware acceleration is strongly preferred; software rendering is a diagnostic fallback only.

## 1. Host prerequisites and partition plan

Use a second Linux installation or a live environment to build the target. Never substitute a mounted host root for `TARGET`. Example layout:

| Partition | Filesystem | Mount | Purpose |
| --- | --- | --- | --- |
| ESP | FAT32 | `/boot/efi` | UEFI files |
| root | ext4 | `/` | Luke OS |
| data | ext4 | `/data` | persistent user files |
| swap | swap or zram | none | memory pressure |

Use UUIDs in `/etc/fstab`, not `/dev/sdX`, because disk enumeration changes between boots. The data partition should be mounted with `nosuid,nodev` unless applications explicitly need device nodes. Do not put an entire live `/home` on an exFAT volume: it lacks normal Unix ownership, permissions, symlinks, and extended attributes.

## 2. Minimal rootfs build

Install host tools first:

```bash
sudo apt-get install --no-install-recommends debootstrap arch-install-scripts \
  grub-efi-amd64 grub-pc-bin linux-image-amd64 initramfs-tools \
  dosfstools e2fsprogs rsync ca-certificates
```

Run the supplied script from a root shell. It performs the safe bind mounts, creates a non-root account, installs a deliberately small baseline, enables the required repositories, and writes a UUID-based fstab. It does not partition or format disks.

```bash
sudo ./luke/build/bootstrap-minbase.sh \
  --target /mnt/luke \
  --data-device /dev/disk/by-uuid/PUT-DATA-UUID-HERE \
  --username aman \
  --suite bookworm \
  --mirror http://deb.debian.org/debian
```

Before bootloader installation, bind-mount `/dev`, `/dev/pts`, `/proc`, `/sys`, and `/run`; copy a working resolver; then chroot. The script cleans mounts with a trap, so an interrupted build does not leave the host namespace polluted.

Inside the chroot, the essential sequence is:

```bash
dpkg --configure -a
apt-get update
apt-get install --no-install-recommends systemd systemd-sysv dbus sudo \
  network-manager wpasupplicant linux-image-amd64 initramfs-tools
passwd root
passwd aman
update-initramfs -c -k all
```

Install only services that are actually used. A small baseline normally enables `systemd-udevd`, `systemd-logind`, `dbus`, `NetworkManager`, `systemd-resolved` (or another single resolver), `ModemManager` only when required, and the display manager. Disable discovery, printing, snap services, and getty instances that are not part of the product. Profile boot with `systemd-analyze critical-chain` and `systemd-analyze blame`; do not disable `systemd-udevd`, `systemd-logind`, `dbus`, or device units merely to improve a benchmark.

## 3. Kernel and initramfs

Start from the distribution kernel unless there is a measured reason to maintain a custom one. The supplied `build/kernel-luke.fragment` is an audit checklist. Merge it with the distribution config and verify the resulting `/boot/config-$(uname -r)` after installation.

Important details:

* `CONFIG_PREEMPT_DYNAMIC=y` is a good general-purpose choice. Full `PREEMPT_RT` is a separate latency project and can reduce throughput or driver compatibility.
* Enable `CONFIG_PSI=y` and `CONFIG_PSI_DEFAULT_DISABLED=n` for pressure telemetry. PSI has no “namespace” Kconfig option; cgroup v2 scopes pressure accounting.
* Modern Waydroid prefers binderfs and `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDERFS=y`, and `CONFIG_ANDROID_BINDER_DEVICES="binder,hwbinder,vndbinder"`.
* Ashmem is legacy. Use `CONFIG_MEMFD_CREATE=y`; only enable `CONFIG_ANDROID_BINDER_IPC_32BIT` or an out-of-tree ashmem driver if the selected Android image explicitly requires it.
* Keep `CONFIG_SECCOMP`, namespaces, cgroups v2, overlayfs, veth, bridge, netfilter, and nftables enabled.

### Broadcom Bluetooth firmware warnings

Identify the adapter and firmware request first:

```bash
sudo dmesg -T | grep -iE 'bluetooth|brcm|firmware'
lsusb -nn | grep -i bluetooth
```

Install the distribution firmware package (`firmware-brcm80211` on Debian where available, or the vendor package supplied by the distribution). For a BCM20702A1 request, install the matching firmware file from the distribution's non-free-firmware repository; do not rename a random `.hcd` file. Confirm its exact requested path in `dmesg`, copy only the licensed package file under `/lib/firmware/brcm/`, then rebuild:

```bash
sudo update-initramfs -u -k all
sudo depmod -a
```

If Bluetooth is intentionally unsupported, blacklist the exact unused USB device driver only after confirming it is not the Wi-Fi function. Silencing all firmware messages or adding `nomodeset` is not a fix.

## 4. Wayland and Luke shell

Install the smallest compositor/session set supported by the target distribution:

```bash
apt-get install --no-install-recommends wayfire wayfire-plugins-extra \
  wf-shell seatd xwayland dbus-user-session pipewire wireplumber \
  xdg-desktop-portal xdg-desktop-portal-wlr \
  mesa-utils libgl1-mesa-dri
```

Add the login user to `video`, `render`, and `input` where those groups exist. Enable `seatd` only if the compositor is using seatd rather than logind. Start the session through the display manager, with `XDG_SESSION_TYPE=wayland`, `XDG_CURRENT_DESKTOP=Luke`, and a user D-Bus session.

Copy `wayland/wayfire.ini` to `~/.config/wayfire.ini`. Wayfire supplies composition, gestures, workspaces, and window placement. It does not provide an Android launcher, notification shade, or dynamic quick settings; Luke's existing launcher and quick-settings applications remain the shell layer and should be started by the session target/autostart.

## 5. Waydroid

Install the official Waydroid repository instructions for the chosen distribution, then install `waydroid`, `lxc`, `dnsmasq`, and `nftables`. Do not mix Ubuntu and Debian repository packages in one rootfs. Initialize the image as the desktop user:

```bash
sudo waydroid init -f
waydroid session start
waydroid show-full-ui
```

The supplied `waydroid/luke-waydroid.service` is a system service for the container manager only. The graphical Waydroid session belongs to the logged-in user and must not be started as root. Enable it after verifying that binderfs exists and that the compositor session is available.

The service creates binderfs when needed and starts `waydroid-container`; it refuses to proceed when the host kernel is missing binder support. The `waydroid/waydroid-nftables.conf` ruleset gives the container bridge IPv4 forwarding and masquerading without flushing unrelated firewall rules. Load it through the host firewall's supported include mechanism, then set the bridge address to the one reported by `waydroid status` if the distribution chooses a different subnet.

Required checks:

```bash
test -e /dev/binderfs/binder || sudo modprobe binder_linux devices=binder,hwbinder,vndbinder
grep -E 'ANDROID_BINDER|MEMFD_CREATE|PSI|NAMESPACES|CGROUPS' /boot/config-$(uname -r)
waydroid status
ip link show waydroid0
```

## 6. Networking and firewall model

Waydroid normally creates `waydroid0` and uses dnsmasq. Do not create a second competing NetworkManager bridge. Permit forwarding only from the Waydroid bridge to the active uplink, masquerade the bridge subnet, and allow established return traffic. The nftables template uses an `inet` table and a named chain so it can coexist with a host firewall; audit the final merged rules with `nft list ruleset`.

If a strict firewall is already installed, add equivalent rules there instead of loading two policy owners. Verify DNS and routing from both host and Android. Avoid globally enabling `net.ipv4.ip_forward` without a firewall policy.

## 7. Storage, boot, and rebuild discipline

Use `/data` for documents and application data that must survive root rebuilds. Example fstab entries:

```fstab
UUID=<root-uuid>  /      ext4  defaults,noatime,errors=remount-ro  0 1
UUID=<data-uuid>  /data  ext4  defaults,noatime,nodev,nosuid       0 2
```

Create `/data/home/aman`, then either bind-mount selected directories (`Documents`, `Downloads`, `Pictures`, `Videos`) or place the whole home there after testing display-manager permissions. Keep caches and transient Waydroid images on root or a separately sized data subdirectory; otherwise a large Android image can silently consume the OS partition.

For HDDs, prefer `noatime`, a modest swappiness (`vm.swappiness=10` is a starting point, not a law), zram where supported, and measured I/O scheduling. Do not disable write barriers or force unsafe mount options. Trim is irrelevant to a spinning disk. Keep journal size bounded and rotate logs rather than disabling journaling.

## 8. Acceptance checklist

1. Boot succeeds with the data partition absent; the system reaches a usable recovery/session target.
2. `findmnt /data` shows the intended UUID and user files survive a root-only rebuild.
3. `loginctl show-session "$XDG_SESSION_ID" -p Type` reports `Type=wayland`.
4. `glxinfo -B` or `eglinfo` reports the intended GPU renderer, not accidental software rendering.
5. `waydroid status` reports a running container and Android apps can resolve DNS and reach HTTPS.
6. `systemd-analyze critical-chain` contains no unexpected 30-second network or firmware timeout.
7. `journalctl -b -p warning..alert` is reviewed, with Broadcom firmware warnings either fixed with the correct package or intentionally explained.
8. A root partition re-image test confirms `/data` is untouched.

The existing Luke GTK applications can remain as the app drawer and quick-settings implementation while this Wayland migration is validated. Move one boundary at a time: boot/rootfs, compositor, then Waydroid, then shell polish.