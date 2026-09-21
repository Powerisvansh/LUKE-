# TEST 1 — Session Log: Luke Bootable USB Build & Repo Cleanup (Sep 21 2026)

Snapshot of the full working session for the Luke project: building a
bootable Luke live-USB stick tailored to this laptop, verifying the result,
and cleaning the repository down to build essentials.

## Goal

1. Make the 57 GB SanDisk pendrive (`/dev/sdb`) bootable with the Luke
   operating system, built fresh (no cloning of the existing system), and
   configured for this laptop.
2. Remove all unwanted files, keeping only what is used to build/run the OS.

## Hardware detected (this laptop)

| Component | Detail |
| --- | --- |
| CPU | Intel Core i3-3110M @ 2.40 GHz |
| GPU | Intel HD Graphics (3rd Gen / Ivy Bridge) |
| WiFi | Intel Centrino Advanced-N 6205 |
| Ethernet | Realtek RTL8111/8168/8211/8411 (r8169) |
| RAM | 7.3 GB |
| Boot mode | Legacy BIOS (UEFI firmware absent) |
| Internal disk | `/dev/sda` (465.8 GB, untouched) |
| Pendrive | `/dev/sdb` — SanDisk 3.2Gen1, 57.3 GB |

## Key discovery

The existing `luke/boot/build-live-usb.sh` only installed an **x86_64-efi**
(UEFI) bootloader. This laptop boots in **legacy BIOS mode**, so a pendrive
built by the old script would never boot here. It also lacked Intel WiFi
firmware and the non-free-firmware apt component.

## Changes made to luke/boot/build-live-usb.sh

1. **Partition layout** now uses a GPT layout with 3 partitions:
   - Partition 1: `biospart` (1 MiB) flagged `bios_grub`
   - Partition 2: ESP (fat32, ~1 GiB) flagged `esp` + `boot`
   - Partition 3: root (ext4, remainder of disk)
   Only the first boot attempt failed because the kernel had not yet
   registered the new partition nodes before `mkfs` ran.

2. **Partition-table reload wait** added after `parted`: `partprobe`,
   `udevadm settle`, then a loop waiting up to 30 s for the partition nodes.

3. **Apt sources**: `/etc/apt/sources.list` now includes
   `main contrib non-free-firmware` (bookworm + security + updates).

4. **Packages**: added `grub-pc-bin`, `firmware-iwlwifi` (Intel 6205 WiFi),
   `firmware-realtek` (wired NIC), `firmware-linux` (replaces
   `firmware-linux-free`).

5. **Dual bootloader install**: after `update-grub` and the existing
   UEFI install (`grub-install --target=x86_64-efi ... --removable`), the
   script now also runs
   `grub-install --target=i386-pc --boot-directory=/boot --recheck /dev/sdX`
   for legacy BIOS boot on GPT.

## Build run

```
sudo bash luke/boot/build-live-usb.sh --device /dev/sdb --username aman --suite bookworm
```

- Debian bookworm minbase rootfs via `debootstrap`.
- Kernel `linux-image-amd64` (6.1.0-53-amd64) with `initramfs-tools`.
- NetworkManager, LightDM, Plymouth, GRUB theme, Luke project copied to
  `/home/aman/.luke`.
- `/etc/luke/mode` set to `live-usb`.
- Both bootloaders reported "Installation finished. No error reported."
- Post-build: `firmware-realtek` installed into the image and the
  initramfs regenerated.

## Verification (on finished pendrive)

| Item | Result |
| --- | --- |
| Partition table | GPT: biospart / ESP / root, correct sizes |
| MBR boot code | GRUB boot sector present (starts `eb63` jmp) |
| BIOS core.img | Present in `sdb1` (bios_grub) and `/boot/grub/i386-pc/core.img` |
| UEFI loader | `/boot/efi/EFI/BOOT/BOOTX64.EFI` present |
| grub.cfg | Generated, Luke menu entry, `set root` = root partition UUID |
| GRUB theme | `/boot/grub/themes/luke` present |
| WiFi firmware | `/lib/firmware/iwlwifi-5000-5.ucode` present |
| Ethernet firmware | `rtl8411-1.fw` / `rtl8411-2.fw` present |
| fstab | UUIDs match the actual root/EFI partitions |
| Luke source | `/home/aman/.luke` populated |
| Initramfs | Rebuilt clean after firmware additions |

Build log captured at `/tmp/opencode/build-luke-usb.log`, deleted during
cleanup.

## Boot instructions (this laptop)

Insert the pendrive, power on, open the boot menu (typically **F12** on this
Dell), select the USB stick. First real boot still needs on-hardware
acceptance testing per the project policy.

## Repository cleanup

Kept only files used to build/run the OS:

- `luke/` (full source tree)
- `catalog/` (app store catalog)
- `.github/` (CI workflow)
- `.gitignore`, `README.md`

Removed (all tracked in git, recoverable):

- `TEST 2.md` – `TEST 6.md` (old pass/process logs; TEST 6 was filler)
- `PORTOS-GUIDE.md` (outdated guide for the pre-Luke Ubuntu pendrive)
- `LUKE_PROJECT_BACKUP.md` (outdated backup notes)
- `LUKE-OS-ANALYSIS.md`, `LUKE-DESKTOP-ARCHITECTURE.md` (unreferenced docs)
- `plan.md` (roadmap notes)
- `SESSION-2026-09-20.md` (session log)
- `snapshots/` (obsolete `.bak` config backups)
- `/tmp/opencode/build-luke-usb.log`

README was edited to drop the links to the removed `plan.md` and
`LUKE-OS-ANALYSIS.md` docs.

## State at end of session

- Working tree: README modified + build script modified for this laptop's
  BIOS boot support; all deletions staged as `D` in `git status`.
- Nothing committed; no changes to the laptop's internal disk (`/dev/sda`).