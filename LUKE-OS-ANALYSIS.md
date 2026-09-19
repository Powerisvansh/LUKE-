# Luke OS — Current State Analysis & Rebuild Roadmap

Date: 2026-09-19
Author: rebuild session

This document records exactly what the Luke OS is today, what can be safely
reused, what must be replaced, and the ordered implementation roadmap. It is
the working reference for the rebuild. Every subsystem decision below follows
the master rules: keep working kernel/drivers/filesystem, replace the visible
experience, real functionality only, original design, no fake buttons, and
never break a working boot.

## 0. Executive summary

There are two Linux installs involved:

- The **developer host** = this Lenovo ThinkPad L430 running Linux Mint 22.3
  (Cinnamon, X11). It is used purely to build and deploy. Not the product.
- The **product** = the Luke OS on the SanDisk USB pendrive (`/dev/sdb`):
  Ubuntu 24.04 noble base + Xfce, branded "Luke", with a custom Python/GTK3
  app registry, launcher and greeter already staged.

The rebuild targets the **pendrive Luke OS**. Strategy: keep the proven
underlying base (kernel, initramfs, systemd, drivers, filesystem, GRUB
mechanism, X11, xfwm4 window management, Python3/GTK3 runtime) and replace
the entire visible/user-facing experience with an original, app-centric,
single-team design language. Nothing that the user sees stays "generically
Linux".

## 1. Current architecture (layered)

| Layer            | Today                                                  | Decision |
|------------------|--------------------------------------------------------|----------|
| Boot menu        | GRUB 2.06, text menu, 5 s timeout, "Luke GNU/Linux"    | Replace visuals (custom GRUB theme + font + logo) |
| Boot splash      | plymouth `ubuntu-text` module retitled "Luke"          | Replace with original Luke splash + animation |
| Kernel           | 6.8.0-139-generic + initramfs (single kernel)          | Keep, do not touch |
| Drivers           | i915/crocus (Intel HD4000), iwlwifi (Centrino 6205), r8169, snd-hda, btrfs none | Keep as-is |
| System services  | systemd, udev, logind, dbus, NetworkManager, wpasupplicant, lightdm | Keep; lightdm config changes only |
| Display server   | X.Org (X11), modesetting driver                       | Keep |
| Window manager   | xfwm4 (composition off)                               | Keep as the WM underneath the new shell |
| Desktop shell    | xfdesktop + xfce4-panel + Whisker (status bar top / dock bottom) | **Replace entirely with LukeShell** |
| GTK theme        | Materia-dark, Papirus icons, Roboto font              | **Replace** with original design system |
| Greeter          | lightdm-gtk-greeter, **auto-login still enabled**     | Replace with custom Luke greeter (already written, not yet activated) |
| App platform     | registry `apps.json` + `lukeapps.py` + 7 real GTK apps | Keep the concept, evolve to full manifest format |
| Android (Waydroid)| documented architecture only, not deployed           | Out of scope for this rebuild |

## 2. Current boot method

1. Firmware (Lenovo UEFI 2.76) → boot choice to the pendrive.
2. GRUB 2.06: `GRUB_TIMEOUT_STYLE=menu`, `GRUB_TIMEOUT=5`,
   `GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"`. Entries: "Luke GNU/Linux"
   (default), "Advanced options", "Linux Mint 22.3".
3. Kernel 6.8.0-139-generic with splash → plymouth (`ubuntu-text` module,
   title relabeled to "Luke") → systemd → multi-user → lightdm → Xfce.
   Auto-login is still active (`autologin-user=aman`).

Dual media: UEFI boot uses `sdb2` (LUKE-EFI); legacy BIOS uses `sdb1`
(BIOS boot partition). Both are GRUB. Recovery paths already exist via the
"Advanced options" menu; these must be preserved in the new theme.

## 3. Current GUI technology

- X11 / X.Org 21.1, xfwm4, xfdesktop, xfce4-panel, xfce4-whiskermenu-plugin.
- Python 3.12 + PyGObject (GTK 3.24 typelib verified on target) + python3-dbus.
- Custom layer: `framework/lukeui.py` (borderless + cairo header),
  `framework/luke.css` (card/chip/button/launcher styles), `launcher/main.py`
  (fullscreen drawer with search/chips/favorites/recents/grid + keyboard nav),
  `greeter/main.py` (LightDM greeter via GI, not yet installed),
  apps: calculator, monitor, taskmanager, settings, network, quicksettings,
  about.
- WebKit2 / Libnotify **verified present on the host**, missing on the target
  (browser will need `gir1.2-webkit2-4.1` + `gir1.2-notify-0.7` installed on
  the target).

## 4. Current desktop / window system

Xfce 4.18 session on X11 (`/usr/share/xsessions/xfce.desktop`), started by
lightdm (auto-login as `aman`). xfwm4 handles window management, placement,
snapping, maximize/restore, Alt+Tab. Panels are Xfce widgets. This is the
"generic Linux desktop" look the rebuild must remove.

## 5. Current filesystem

| Partition | Filesystem | Size  | Mount    | Purpose |
|-----------|-----------|-------|----------|---------|
| sdb1      | (BIOS boot grub) | 1M    | —        | legacy GRUB core |
| sdb2      | vfat (LUKE-EFI)  | 512M  | (EFI)    | UEFI GRUB |
| sdb3      | ext4 (LUKE-ROOT) | 19.5G | `/`      | OS (7.0 G used) |
| sdb4      | exfat (LUKE-DATA)| 37.3G | /home/aman/media/... | user data |

`/home` lives on the root partition; the data partition auto-mounts under the
user's media dir. fstab uses UUIDs (safe against re-block-device). 4 GB
swapfile exists. This layout is sane and must not be disturbed.

## 6. Current application system

Registry-driven (good): `apps.json` → `lukeapps.load_apps()` → `App`
(id/name/exec/icon/color/category/desc), favorites + recents persisted in
`~/.luke/state/`, launch via `subprocess.Popen` with `~` expansion and
terminal wrapping, and `tools/gen-desktops.py` generates XDG `.desktop`
files for non-Luke menus. There is **no hard-coded desktop**; anything added
to the registry appears in the launcher automatically. Apps are launched as
detached processes.

This is the right architecture to evolve (manifest v2 with version, app-id,
permissions, description, executables) instead of rewriting.

## 7. Current dependencies (target, notable)

Ubuntu noble base; xfce4-session/panel/whisker; xfwm4; xfdesktop; lightdm +
lightdm-gtk-greeter; python3, python3-gi, gir1.2-gtk-3.0, python3-dbus;
thunar; mousepad; xfce4-terminal; network-manager, wpasupplicant;
mesa/libgl1-mesa-dri; linux-firmware (wifi/GPU); imagemagick; materia-gtk-theme,
papirus-icon-theme, fonts-roboto-unhinted (to be uninstalled or simply no
longer used); 4 GB swapfile.

## 8. What can be reused safely

- **Base system**: kernel, initramfs, systemd/udev/logind/dbus, NetworkManager,
  wpasupplicant, Mesa + i915/crocus, wifi/GPU firmware, filesystem + fstab,
  swapfile.
- **Boot mechanics**: GRUB (keep mechanism, replace visuals), plymouth
  (keep framework, replace theme), dual-boot entries, Advanced options.
- **Display/WM**: X.Org, xfwm4 (window management/maximize/snap/Alt-Tab).
  Xfce session as the *launch vehicle* only.
- **Runtime**: Python 3.12 + PyGObject GTK3 + python3-dbus (all present).
- **Proven code to carry over**: calculator engine (`calc_core.py`), the
  registry concept + launcher skeleton + greeter skeleton + system readers
  (proc, nmcli, pactl, xrandr, xfconf-free logic), autostart bootstrap,
  deploy/apply-root conventions, `gen-desktops.py`.
- **Audio/Net/utility logic**: pactl, nmcli, rfkill patterns.

## 9. What should be replaced (the visible experience)

Everything a user sees must become original:

1. **GRUB screen** → original Luke boot theme (custom font generated with
   `grub-mkfont`, own logo, own palette, timeout bar, keyboard nav preserved).
2. **Boot splash** → original plymouth theme with Luke mark + loader.
3. **Login screen** → custom Luke greeter (already built, must be activated;
   auto-login removed) restyled under the new design system.
4. **Desktop shell** → `xfdesktop`, panels, Whisker, tray, window-list all
   replaced by one fullscreen **LukeShell** (home surface, dock, status bar,
   quick settings shade, notification center, launcher, task switcher).
5. **GTK theme/icons/font** → Materia/Papirus/Roboto removed from active use;
   new design tokens (original typography, colors, radii, spacing), original
   icon set drawn for Luke, original wallpaper generator.
6. **App set** → expanded to the full product list, every app real and
   functional under the base OS, none fake.
7. **Browser** → original UI wrapping WebKitGTK (real engine, permissive
   license), no Chrome/Firefox look-alike.
8. **Notifications/quick settings** → original system built into the shell,
   real controls only.

## 10. Implementation roadmap (one subsystem at a time)

Each phase ends: built → deployed to pendrive → (root parts) staged script →
user runs → verified on device. A recovery path (backed-up GRUB/lightdm/
theme copies + "Advanced options") is created *before* the boot layer is
touched.

- **Phase 0 — Recovery + workspace**: back up GRUB cfg, lightdm conf,
  initramfs images, current theme files; init a git/rsync snapshot; define
  the deploy + verify workflow.
- **Phase 1 — Design system**: name-check branding, original logo/mark,
  color palette, two weights of original-feel typography (system fonts),
  spacing/radius/motion tokens, wallpaper generator, icon set, GTK3 component
  library (button/card/chip/field/dialog/switch/slider) on the new tokens.
- **Phase 2 — Boot experience**: custom GRUB theme + custom plymouth theme
  (staged as root scripts with backups and a recovery entry).
- **Phase 3 — Login**: activate the Luke greeter, remove auto-login, smooth
  login → home transition.
- **Phase 4 — Shell / home**: LukeShell fullscreen in GTK3 — status bar
  (clock, wifi, volume, battery, notifications icon), home surface with
  wallpaper + app grid, dock, launcher, quick settings shade, notification
  center, recents/task switcher. Xfce session reduced to a thin bootstrap.
- **Phase 5 — App framework v2**: manifest format (app-id, name, version,
  icon, exec, permissions, category, description), registry upgrade, install/
  update/uninstall helpers, XDG integration.
- **Phase 6 — System applications**: Files, Settings, Terminal (VTE or
  xfce4-terminal), Calculator, Editor, Monitor, Task Manager, Image Viewer,
  Media Viewer, Clock, Calendar, About, Network, Software Update (all real).
- **Phase 7 — Web browser**: WebKitGTK engine + original UI (tabs, address,
  back/forward/reload/home, bookmarks, history, downloads, private mode).
- **Phase 8 — App Store / Updates**: catalog repository format, install/
  uninstall/update UI backed by real mechanisms (apt for system, bundles for
  Luke apps).
- **Phase 9 — Motion + multitasking polish**: standardised short interruptible
  animations, snapping, minimize/maximize, app-centric fullscreen mode flag.
- **Phase 10 — Performance + acceptance**: boot-time profile, memory/RAM
  budget, no background daemons, full on-device test of every subsystem.

## 11. Risk & recovery

- Root-level changes (GRUB theme, plymouth, greeter, lightdm config) are
  **staged as scripts** and always create `.bak` copies first. The dual-boot
  Mint entry + "Advanced options" recovery entries remain reachable from the
  new GRUB theme.
- The developer host cannot run `sudo` non-interactively, so root installs
  are executed by the user, exactly as prior LUKE passes did
  (`apply-root.sh` pattern).
- Every significant change is followed by `python3 -m compileall`, syntax
  check, and a deploy; device testing happens on the booted pendrive.