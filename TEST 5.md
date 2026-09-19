# TEST 5 — Process Log: The Luke app platform, launcher and login screen (Sep 18 2026)

Full record of the pass that built the **Luke** user-facing platform on top of the
rebranded Ubuntu 24.04 + Xfce base: a shared GTK3 design language, a set of real
built-in apps, a fullscreen app-launcher (drawer), and a custom LightDM greeter.

> What you get after applying everything: login lands on the Luke greeter
> (no auto-login), the desktop keeps its working Xfce panel + dock, and a
> Super+L shortcut or a dock button opens the Luke app drawer.

## 1. Scope / goal
- Give the OS an **original identity + Android-inspired UX**: dark theme, teal
  accent (`#4FD1C5`), card-based UI, one press-to-launch drawer.
- **Real functionality only** — no fake settings, no dead buttons. Every app
  does something real against the system (proc, xfconf, nmcli, xrandr, pactl).
- Preserve the working Xfce base: no broken panel, no auto-login, no missing
  packages.
- Stack: **Python 3 + GTK3 (PyGObject)** — already present, no compiler needed.

## 2. Layout on the pendrive
- Source: `/home/aman/Desktop/operating/luke/`
- Deployed (no sudo needed) to `/media/aman/LUKE-ROOT/home/aman/.luke/`
- System level (needs sudo) → staged in `luke/apply-root.sh`

```
luke/
├── apps.json                # app registry (id, name, icon, exec, category)
├── deploy.sh                # rsyncs sources to ~/.luke on the pendrive
├── apply-root.sh            # root changes: packages, greeter, lightdm (USER RUNS)
├── framework/
│   ├── luke.css             # design system (cards, chips, buttons, launcher)
│   ├── lukeui.py            # LukeWindow (borderless + cairo header), css, errors
│   └── lukeapps.py          # registry loader, App, launch, favorites/recents
├── apps/
│   ├── calculator/  calc_core.py (pure, tested engine) + main.py
│   ├── monitor/     main.py       # CPU/MEM/LOAD/UPTIME/DISKS from /proc
│   ├── taskmanager/ main.py       # live process table + kill
│   ├── settings/    main.py       # real xfconf theme/icon/font + tweaks
│   ├── network/     main.py       # nmcli: connect/saved/scan/toggle/status
│   └── about/       main.py       # system info + cairo Luke logo + clipboard
├── launcher/  main.py      # fullscreen drawer: search, chips, favorites, grid
├── greeter/   main.py + greeter.css   # Luke login screen (LightDM GI)
├── bin/       luke-launcher, luke-bootstrap.sh
├── tools/     gen-desktops.py (XDG .desktop files), dock.py (panel button)
└── autostart/ luke-bootstrap.desktop  # runs once per login
```

## 3. The apps (all real)
| App | What it truly does |
|---|---|
| Calculator | Full expression engine (`calc_core.py`) — ops, parens, %, ^, negation, decimal guards; 21/21 eval cases PASS on host |
| Monitor | Per-core CPU %, memory/swap, load, uptime, disk usage all read from `/proc` — verified reasonable values on host |
| Task Manager | 241 processes parsed from `/proc`; live CPU% delta (3 snapshots), RAM, search, unicode rows, SIGTERM kill with result feedback |
| Settings | Real xfconf changes (gtk-theme/icon-theme/xfwm-theme/font); display resolution via xrandr against current output; NetworkManager data via nmcli; volume via pactl (graceful if missing); storage; users; privacy/firewall (honest per available tools); updates via apt; About |
| Network | nmcli: connect to WiFi (with password prompt), saved networks, full scan list with signals, real toggle |
| About | os-release/CPU/mem/disk facts + original cairo "L" monogram + copy-to-clipboard |

## 4. The launcher (drawer)
- Super+L (or dock button) opens a fullscreen overlay: search-as-you-type,
  category chips, favorites row, recent apps row (persisted), icon grid, and
  keyboard navigation (Esc / arrows / Enter).
- Fades in via GLib timeouts; **exits the process** once hidden (no lingering
  background python).
- Launches apps through `lukeapps.launch` with `~` expansion and detached
  processes.

## 5. The greeter (login screen)
- Self-contained GTK UI: animated gradient background, live clock, avatar
  monogram per-user, user list + custom login, password field with show/paste/
  caps-lock hints, spinner while authenticating, error text from LightDM, power
  buttons (Restart / Shut Down via `org.freedesktop.DisplayManager` D-Bus,
  systemctl fallback).
- Registers session from `/usr/share/xsessions/` (expects `xfce`).
- Deployed as root: `/usr/local/lib/luke/greeter/`, wrapper
  `/usr/local/bin/luke-greeter`, xgreeter `/usr/share/xgreeters/luke.desktop`.

## 6. Integration on the desktop (all user-level, applied at first login)
- Autostart `luke-bootstrap.desktop` → runs on login:
  1. `gen-desktops.py` → writes `~/.local/share/applications/luke-*.desktop`
     for all 10 registry apps (Whisker menu + docks can open them).
  2. xfsexf `xfce4-keyboard-shortcuts` → Super+L bound (absolute path,
     survives because it's in the shortcuts channel).
  3. `dock.py` → one-time panel tweak: the idle separator beside the App Menu
     becomes a Luke launcher button (only if it's still a plain separator;
     file backed up; marker prevents re-runs; panel restarts once).
- Loose ends handled: launcher hides→quits, no daemons left running.

## 7. Verification done (host-side)
- All target copies `python3 -m py_compile` OK (framework, launcher, greeter,
  all 6 apps, tools).
- `gen-desktops.py` ran for real against a scratch HOME → wrote all 10
  `.desktop` launchers correctly.
- `dock.py` ran on a copy of the actual panel XML → plugin-11 converted to
  `launcher` + `.desktop` item; second run no-op; marker created.
- `lukeapps.load_apps()` reads the deployed registry: 10 apps, categories
  System/Utilities.
- Calculator engine: 21/21 eval cases PASS. Monitor/taskmanager/about reads
  verified against real host /proc and /etc/os-release.

## 8. Blocker — root changes are staged for the user to run (no sudo here)
Inside the pendrive, `/etc/lightdm/lightdm.conf` still has:

```
[Seat:*]
autologin-user=aman
autologin-user-timeout=0
greeter-session=lightdm-gtk-greeter
```

Until `apply-root.sh` runs you keep the old auto-login + gtk greeter. The
script (idempotent, with backups) will:

```
sudo bash /home/aman/Desktop/operating/luke/apply-root.sh
```

and it will: chroot-install `gir1.2-lightdm-1` + `pulseaudio-utils`, copy the
greeter to /usr/local, register the xgreeter, and rewrite lightdm.conf to
`greeter-session=luke` with auto-login removed (backup `lightdm.conf.lukebak`).

## 9. What still needs a real device (cannot be done from this host)
- Full GUI run-through of every app on the pendrive (the host cannot display
  the target's GI sessions).
- First real boot → greeter appears; then autostart bootstrap; then Super+L /
  dock launcher; then app launches from the drawer.
- Any visual polish passes (animations, spacing, icon swaps) after seeing it
  live.

## 10. Next session-1 checklist (after booting Luke)
1. Run `sudo bash /home/aman/Desktop/operating/luke/apply-root.sh` while the
   pendrive is mounted on the host (or run it before the first boot).
2. Boot Luke; expect the Luke greeter (login as `aman`).
3. Press Super+L → drawer opens; favourite apps, run calculator/monitor/etc.
4. Test the dock Luke button, Whisker → Luke apps, and the launcher last-app
   recents.
5. Report anything broken → iterate in this source tree, rerun `deploy.sh`,
   re-run apply-root.sh only if the greeter changes.