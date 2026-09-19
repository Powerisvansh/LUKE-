# TEST 3 — Process Log: Android-GUI Pass (later name "Luke") (Sep 18 2026)

Record of the process that turned the portable pendrive OS into **Luke** (previously "Luke"; the "Ubuntu" name is removed)
with an Android-style interface, so it can be repeated or audited.

## 1. Context
- Host machine on which the work was done: Linux Mint 22.3 (Mint) — user `aman`.
- Target: portable Ubuntu 24.04 on SanDisk pendrive `/dev/sdb`
  (was PORTOS, then NOMAD; now **LUKE**), mounted read/write by the host at
  `/media/aman/LUKE-ROOT`.
- All system changes were made inside the target via `chroot`.
- Before this pass: NOMAD had already been updated to kernel 6.8.0-139, cleaned
  (snap purged, apt cache cleared) and was running a stock Xfce desktop.

## 2. Goal
Keep the working Xfce base but make it **look like an Android GUI**, built from
existing open-source components — nothing copy-pasted from random places.
Every component below comes from Ubuntu's own repos or was generated on the drive.

## 3. Prerequisites / access
- Root on the host: `sudo -S` with the host sudo password piped into each command.
- Bind-mount the target's virtual filesystems for the chroot:
  ```bash
  sudo mount --bind /proc <root>/proc
  sudo mount --bind /sys  <root>/sys
  sudo mount --bind /dev  <root>/dev
  sudo mount --bind /run  <root>/run
  ```

## 4. Packages installed (Ubuntu noble repos, `--no-install-recommends`)
```bash
apt-get install -y --no-install-recommends \
  materia-gtk-theme papirus-icon-theme fonts-roboto-unhinted \
  xfce4-pulseaudio-plugin xfce4-whiskermenu-plugin imagemagick
```
| Package                     | Why                                              |
|-----------------------------|--------------------------------------------------|
| materia-gtk-theme           | **Materia-dark** — Material Design GTK + xfwm4 theme |
| papirus-icon-theme          | **Papirus-Dark** — Material-style icons          |
| fonts-roboto-unhinted       | **Roboto** — Android's typeface                  |
| xfce4-whiskermenu-plugin    | app-drawer menu in the bottom dock               |
| xfce4-pulseaudio-plugin     | volume icon in the status bar (Android-style)    |
| imagemagick                 | used to **generate** the wallpaper (not download it) |

## 5. Wallpaper generated (not copied)
```bash
convert -size 1920x1080 gradient:"#141E30-#243B55"      /home/aman/Pictures/b1.png
convert -size 1920x1080 plasma:fractal -blur 0x9 -modulate 100,60,130 /home/aman/Pictures/n1.png
composite -blend 35 /home/aman/Pictures/n1.png /home/aman/Pictures/b1.png \
          /home/aman/Pictures/luke-android-wallpaper.png
rm -f /home/aman/Pictures/b1.png /home/aman/Pictures/n1.png
```
Then set it as the backdrop on every workspace in
`~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml`
(replaced the old `/usr/share/backgrounds/xfce/xfce-shapes.svg` path).

## 6. User config written (inside target, owned by user `aman`)
1. **Theme / icons / font** — `xsettings.xml` (new):
   `ThemeName=Materia-dark`, `IconThemeName=Papirus-Dark`, `FontName=Roboto 10`,
   antialias + medium hinting. Mirrored in `~/.config/gtk-3.0/settings.ini`.
2. **Window manager** — `xfwm4.xml`: theme `Materia-dark`,
   title font `Roboto Bold 9`.
3. **Panels** — `xfce4-panel.xml` rewritten as two Android-style panels:
   - **Top = status bar** (26 px): Clock `HH:MM` + date on the left,
     growing separator, then system tray (WiFi) | volume | battery | power menu.
   - **Bottom = home dock** (58 px): Terminal | File Manager | Text Editor |
     app-drawer (Whisker menu, `appgrid` icon) — centred via expand separators.
4. **Dead button fixed** — the old dock's "Web Browser" launcher
   (`panel/launcher-19/17888294463.desktop`) pointed to a browser that no
   longer exists after the snap purge; repointed to **Mousepad**.
5. Cleaned up temp helper pngs; ownership of all config files reset to uid 1000.

## 7. Login screen themed
`/etc/lightdm/lightdm-gtk-greeter.conf` → Materia-dark theme, Papirus-Dark
icons, Roboto font, the generated wallpaper as background, `%H:%M` clock,
smooth 200 ms transition, rounded user image.

## 8. Rebrand NOMAD → LUKE UBUNTU
- `/etc/hostname` → `luke`
- `/etc/hosts` → `127.0.1.1    luke`
- `/etc/os-release` + `/etc/lsb-release` → NAME="Luke",
  VERSION="1.0"; kept `ID=ubuntu`, `UBUNTU_CODENAME=noble`
  so apt/PPAs keep working.
- `update-grub` → boot menu now shows **"Luke"** (Linux Mint 22.3
  still listed second).
- Relabeled partitions (offline):
  ```bash
  e2label    /dev/sdb3 LUKE-ROOT
  fatlabel   /dev/sdb2 LUKE-EFI
  exfatlabel /dev/sdb4 LUKE-DATA
  ```
  UUIDs unchanged → fstab + GRUB (hd1,gpt3) unaffected.
  Partitions remounted under `/media/aman/LUKE-{ROOT,DATA}` (as user `aman`,
  not root — remount only counted after relabel).

## 9. Cleanup after the pass
```bash
apt-get autoremove --purge -y   # leftover auto-installed packages
apt-get clean                   # cleared apt cache again
dpkg --audit && apt-get check   # both clean
```

## 10. Results
- System partition: **6.8 GB used, 12 GB free** (38% used) on the 19.5G partition.
- OS renamed **Luke**: hostname `luke`, GRUB entry, disk labels
  LUKE-EFI/ROOT/DATA.
- Android look applied: Material-You wallpaper, Roboto font, Materia-dark theme,
  Papirus icons, top status bar, bottom dock with app drawer, themed login.
- `dpkg --audit` clean, `apt-get check` clean.
- Note: no web browser is installed (removed in the earlier pass); the dock's
  third button is the Text Editor (Mousepad).

## 12. Follow-up — drop the "Ubuntu" name (same day)
Request: remove the word "Ubuntu" from every user-visible place and use "Luke"
alone. Ubuntu's *internal* IDs were kept so apt/PPAs/drivers still work.

### 12.1 Files edited (all visible surfaces)
- `/etc/os-release` + `/usr/lib/os-release` → `NAME="Luke"`,
  `PRETTY_NAME="Luke"`. **Kept hidden in the file:** `ID=ubuntu`,
  `VERSION_ID=24.04`, `UBUNTU_CODENAME=noble` (NOT shown anywhere).
- `/etc/lsb-release` → `DISTRIB_ID=Luke`, `DISTRIB_DESCRIPTION="Luke"`,
  `DISTRIB_RELEASE=1.0` (MOTD header prints "Welcome to Luke").
- `/etc/issue` + `/etc/issue.net` → now just "Luke" (terminal login banner).
- Boot splash: `ubuntu-text.plymouth(.in)` → `title=Luke`, theme `Name=Luke`
  (module `ubuntu-text` kept internally). `update-initramfs -u -k all` re-baked
  the initrd with the new splash text.
- `update-grub` → boot menu entry now reads **"Luke GNU/Linux"** (was
  "Luke Ubuntu GNU/Linux"; Mint entry preserved).

### 12.2 Unchanged on purpose
- `ID=ubuntu`, `UBUNTU_CODENAME=noble` in os-release/lsb-release — kept hidden
  so `apt`, PPAs, `ubuntu-drivers` and WiFi firmware all keep working.
- Panel plugin/dock, wallpaper, themes — untouched (still the Android look).
- Partition labels already LUKE-ROOT / LUKE-EFI / LUKE-DATA.

### 12.3 Result — every user-visible surface says "Luke"
Boot splash, GRUB menu, login screen, MOTD, About dialog / os-release, and the
terminal banners all read **Luke**. No "Ubuntu" text can be seen when using the
OS.

## 13. Re-run checklist (if ever needed)
1. Bind-mount proc/sys/dev/run.
2. Install the 6 packages listed in section 4.
3. Regenerate the wallpaper (section 5).
4. Write the user config files: `xsettings.xml`, `gtk-3.0/settings.ini`,
   `xfwm4.xml`, `xfce4-panel.xml` (status bar + dock layout), and repoint any
   dead launchers.
5. Write the lightdm greeter theme.
6. Rebrand: hostname/hosts/os-release/lsb-release, `update-grub`.
7. Relabel partitions offline: LUKE-ROOT / LUKE-EFI / LUKE-DATA.
8. `apt-get autoremove --purge -y && apt-get clean`.
9. To re-drop "Ubuntu": edit os-release/lsb-release/issue/plymouth title
   (section 12.1), then `update-grub` and `update-initramfs -u -k all`.