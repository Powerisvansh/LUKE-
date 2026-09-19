# TEST 4 — Process Log: Dropping the "Ubuntu" name, final rebrand to **Luke** (Sep 18 2026)

Full record of the pass that removed **every user-visible "Ubuntu" mention**
from the pendrive OS and left only **Luke** on screen.

> What "Luke" is now: a full Ubuntu 24.04 base, rebuilt with an Android-style
> Xfce GUI宣, that shows **only the name Luke** — on boot splash, GRUB, login,
> desktop, terminal, and login screen. The word "Ubuntu" no longer appears
> anywhere a person can read it.

## 1. Scope / goal
- Kill every **visible** occurrence of "Ubuntu" / "ubuntu" in branding.
- **Keep** the internal technical identifiers that make apt/PPAs/drivers/firmware
  work: `ID=ubuntu`, `ID_LIKE=debian`, `VERSION_ID=24.04`,
  `VERSION_CODENAME=noble`, `UBUNTU_CODENAME=noble`. These stay hidden in the
  identity files but are never shown to a user.
- Screens covered: boot splash (plymouth), GRUB menu + GRUB config, text-mode
  GRUB, login screen + greeter indicators, MOTD/About dialog, MOTD login banner,
  terminal `/etc/issue` + `/etc/issue.net`, lsb_release output, os-release,
  hostname, and disk labels.

## 2. Guardrail (so nothing breaks)
- `ID=ubuntu` + `UBUNTU_CODENAME=noble` are **required by apt** (apt reads
  `/etc/apt/sources.list.d/ubuntu.sources` for the noble release) — kept but
  hidden. `lsb_release` reads `DISTRIB_ID` / `DISTRIB_DESCRIPTION` from
  `/etc/lsb-release` for display; the `name="ubuntu"` in os-release would have
  shown in the About dialog → changed. `PRETTY_NAME`/`NAME` on screen.
- `GRUB_DISTRIBUTOR` reads `NAME` from os-release → splash + boot menu.
- `update-grub` regenerates both the boot menu and the grub.cfg distributor
  name; `update-initramfs -u` re-packs the initrd with the new boot splash
  title.

## 3. Files edited (NOMAD-ROOT — previously NOMAD, now LUKE-ROOT)
All paths are inside the pendrive root /media/aman/LUKE-ROOT.

### 3.1 os-release (both copies)
`/etc/os-release` and `/usr/lib/os-release` are set to the same content:
```
PRETTY_NAME="Luke"
NAME="Luke"
VERSION_ID="24.04"
VERSION="1.0"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://localhost/"
SUPPORT_URL="https://localhost/"
BUG_REPORT_URL="https://localhost/"
PRIVACY_POLICY_URL="https://localhost/"
UBUNTU_CODENAME=noble
```
`/etc/os-release` on this install is a real file (not a symlink), so BOTH files
must be updated — `/usr/lib/os-release` still carried the old "Nomad" name.

### 3.2 lsb-release
```
DISTRIB_ID=Luke
DISTRIB_RELEASE=1.0
DISTRIB_CODENAME=noble
DISTRIB_DESCRIPTION="Luke"
```
This is what the login MOTD header prints ("Welcome to Luke ...").

### 3.3 Terminal banners
- `/etc/issue` → `Luke \n \l`
- `/etc/issue.net` → `Luke`

### 3.4 Boot splash (plymouth)
- `title=Ubuntu 24.04` → `title=Luke`
- theme `Name=Ubuntu Text` → `Name=Luke`
- `Description=Text mode theme based on ubuntu-logo theme` → plain description
- Done in BOTH `ubuntu-text.plymouth` and `ubuntu-text.plymouth.in`.
- The file/dir name `ubuntu-text` and module `ubuntu-text` kept (internal).

### 3.5 GRUB menu entry
- `/etc/default/grub` already reads `NAME` from os-release → entry regenerates
  as **"Luke GNU/Linux"** automatically; Mint entry preserved.

## 4. Regenerating boot files (bind mounts required)
```
sudo mount --bind /proc <root>/proc
sudo mount --bind /sys  <root>/sys
sudo mount --bind /dev  <root>/dev
sudo mount --bind /run  <root>/run
sudo chroot <root> /bin/bash
```
Inside the chroot:
```
update-grub
update-initramfs -u -k all
```
- Note: must mount the binds from the HOST first; running `mount` from inside
  the chroot stacked duplicate binds → `/dev/null` broken, grub-probe "cannot
  find a device", fnf update-initramfs fail. Fix: bind from host, then chroot.

## 5. Long-only rename (no visible change, but full owner reset)
- `dpkg -l | grep -iE '(linux-image|linux-modules|linux-headers)-6.8.0-31'`
  → none (old kernel already gone in pass 2).
- `apt-get autoremove --purge -y` leftovers + `apt-get clean` → disk clean.

## 6. Branding checklist — every screen now says "Luke"
- Boot splash: **Luke**
- GRUB menu: **Luke GNU/Linux** (Mint second)
- Login/lightdm greeter: greeter `indicators=~session;~host;~clock;~power`
  → shows host **luke**, no Ubuntu
- MOTD / About dialog: **Luke**
- Terminal MOTD + issue: **Luke**
- `lsb_release -a`:
  ```
  Distributor ID:	Luke
  Description:	Luke
  Release:	1.0
  Codename:	noble
  ```
- `cat /etc/os-release` → NAME="Luke" (no "Ubuntu" on screen); internals kept.

## 7. Confirmed working after the pass
- `dpkg --audit` clean; `apt-get check` clean.
- `update-grub` regenerated the menu — "Luke GNU/Linux" present.
- `update-initramfs` rebuilt all initrd images with the "Luke" splash title.
- UUIDs unchanged → fstab + GRUB (hd1,gpt3) unaffected.
- apt/update-grub still work with `ID=ubuntu` kept hidden.

## 8. RE-RUN checklist (if ever needed)
1. Bind-mount proc/sys/dev/run (from host, not chroot).
2. Edit the branding files listed in section 3.
3. `update-grub` and `update-initramfs -u -k all` (inside chroot).
4. `autoremove --purge -y && apt-get clean`.
5. Unmount binds.

## 9. Clarification given during this pass
- To run it in a VM: it's an ordinary Ubuntu install, so it boots in
  VirtualBox/VMware either by USB passthrough of the pendrive, or by making a
  raw-disk image (`dd if=/dev/sdb of=luke.img`) and booting that image as the
  VM's disk. Note: no web browser is installed after the earlier purge — the
  dock's third button is the Text Editor (Mousepad).