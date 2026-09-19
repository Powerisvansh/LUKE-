# LUKE — Personal Operating System Guide
Backup / reference notes for the portable OS on this SanDisk pendrive.

## What this is
A full Ubuntu 24.04 system that runs entirely from the USB pendrive.
It is configured specifically for this laptop (Intel Core i3-3110M, 7.3 GB RAM)
with a lightweight Xfce desktop styled like an Android GUI, auto-login, working
WiFi, swap, and a separate data partition for user files.

> Rebranded from "PORTOS" → "NOMAD" → **Luke** (was briefly "Luke Ubuntu"; the "Ubuntu" part was dropped from all branding, boot, login, and GRUB) and given an Android-style
> look (Material You wallpaper, Roboto font, Materia-Dark GTK theme, Papirus
> icons, top status bar + bottom dock) during the Sep 2026 GUI pass.

## Pendrive layout
| Partition | Size   | Format | Label      | Purpose                          |
|-----------|--------|--------|------------|----------------------------------|
| sdb1      | 1M     | -      | (BIOS boot)| GRUB core for legacy boot        |
| sdb2      | 512M   | vfat   | LUKE-EFI   | UEFI bootloader (GRUB)           |
| sdb3      | 19.5G  | ext4   | LUKE-ROOT  | The operating system             |
| sdb4      | 37.3G  | exfat  | LUKE-DATA  | User files (safe across reboots) |

## How to boot Luke
1. Plug in the SanDisk pendrive.
2. Restart the laptop; tap **F12** at the Lenovo logo to open the boot menu.
3. Choose **"SanDisk 3.2Gen1"** (or **"UEFI: SanDisk"**).
4. In the GRUB menu pick **Luke** (appears for 5 seconds).
5. You land on the desktop automatically — user `aman`, no login prompt.
   The screen shows the Android-style home: top status bar, bottom dock.

## How to boot the normal OS (Linux Mint) later
- Without the pendrive plugged in, the laptop boots Mint as usual.
- Even with the pendrive plugged in, Luke's GRUB menu also lists
  "Linux Mint 22.3" so you can switch from the menu.

## Where to save your files
- Save important files to `File System` → `media` → `data`
  (the 37.3G exfat partition — marked 1, auto-mounted at boot).
  These survive reboots and are safe.
- Files in `/home/aman` are also on the pendrive but inside the system
  partition (19.5G) and live with the OS.
- When the pendrive is plugged into this Mint machine it shows up as
  `/media/aman/LUKE-ROOT`, `/media/aman/LUKE-EFI`, `/media/aman/LUKE-DATA`.

## Account / passwords
- User: `aman` (auto-login, no password prompt at desktop).
- Root / sudo password inside Luke: the one set when the OS was built.
- The laptop's own user (host Linux Mint) has a separate sudo password.
- Tip: keeping backups of passwords outside the machine is recommended.

## The Android-style interface
Built from normal open-source packages; nothing was copy-pasted from elsewhere.
- **Wallpaper**: a Material You-style gradient generated on the drive
  (`~/Pictures/luke-android-wallpaper.png`, made with ImageMagick).
- **Font**: Roboto (Android's typeface) for GTK, windows, and the login screen.
- **GTK theme**: Materia-dark (Material Design look), **icons**: Papirus-Dark.
- **Top panel** = Android status bar: time (HH:MM) + date, then a growing
  spacer, then system tray (WiFi), volume, battery, and power menu.
- **Bottom dock** = home-screen dock: Terminal, File Manager, Text Editor,
  and an app-drawer button (grid icon) that opens the Whisker menu.
- **Login screen** now uses the same dark theme, Papirus icons, and wallpaper.

## What was customized (base)
- Xfce desktop (light on RAM/CPU for this i3-3110M)
- Auto-login as `aman` via lightdm
- 4 GB swap file added (`/swapfile`) — no swap existed before
- `wpasupplicant` installed → Intel Centrino Advanced-N 6205 WiFi works
- Bootloader rebuilt for both UEFI and legacy BIOS
- GRUB menu: boots Luke first, Mint as secondary entry
- Fixed: EFI boot config originally pointed at the laptop's hard drive
- File manager (Thunar), Mousepad, archive tool preinstalled

## Service passes (Sep 18 2026)
First pass (NOMAD fix/cleanup):
- Kernel upgraded **6.8.0-31 → 6.8.0-139** + 131 updates; old kernel removed.
- snapd + Firefox snap-stub purged; apt cache (~1.2 GB) cleaned.
- Dev tooling removed (linux-headers/tools, bpftrace, LLVM/Clang, libc6-dev).

Second pass (Android look, named "Luke Ubuntu" then "Luke"):
- Rebranded to **Luke** (hostname `luke`, boot entry, disk labels
  LUKE-EFI/ROOT/DATA; `ID=ubuntu` kept so apt still works).
- Installed Materia, Papirus, Roboto, Whisker menu, volume plugin.
- Generated the Material wallpaper, rewrote the panel as status bar + dock,
  and themed the login screen to match.
- `apt-get autoremove --purge` leftovers + `apt-get clean`.

## Useful commands inside Luke
```bash
sudo apt update                    # refresh software lists
sudo apt install <package>         # install software
sudo apt full-upgrade              # update everything
df -h                              # see space on pendrive
free -h                            # see RAM + swap
nmtui                              # connect to WiFi (text interface)
```

## Troubleshooting
- **Doesn't boot / black screen** → in GRUB pick "Advanced options", choose the
  recovery kernel, or add `nomodeset` to the boot line.
- **Slow to start** → normal; it's a USB drive. First boot takes 1-3 min.
- **WiFi won't connect** → run `nmtui` and reconnect.
- **Pendrive full** → check `df -h`; move files to the data partition
  (`/media/aman/LUKE-DATA`).
- **Want to keep recent app list** → run `sudo apt full-upgrade` occasionally
  so the system stays secure while it's on the drive.

## Rebuild from scratch (if ever needed)
The pendrive was set up once using `debootstrap`/install steps; this file
documents the final working state, so rebuilding means redoing: 4 partitions
(GPT), root ext4, exfat data, GRUB for EFI+BIOS, Ubuntu minimal + Xfce,
auto-login, swap, WiFi packages — then applying the two cleanup passes above
plus the Android-theme installs.