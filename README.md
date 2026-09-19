# Luke

Luke is a small, rebuildable Linux desktop platform with an Android-inspired
shell, GTK applications, a custom greeter, Wayland support, and optional
Waydroid integration.

This repository contains the source and deployment scripts for the Luke
platform. It is designed for a Debian or Ubuntu based target system and is
currently developed against a mounted Luke root filesystem rather than as a
single-click installer.

## What is included

- LukeShell home screen, dock, launcher, quick settings, and IPC
- GTK application framework with app metadata, categories, search, icons, and
  install/uninstall helpers
- System apps including Settings, Calculator, Calendar, Clock, Monitor,
  Network, Task Manager, About, and Luke Browser
- Custom LightDM greeter and Luke visual assets
- Wayfire configuration and Waydroid service/network templates
- Minimal-rootfs bootstrap and boot branding utilities

## Repository layout

```text
luke/
  apps/          GTK applications
  framework/     Shared UI, asset, path, and browser helpers
  shell/         LukeShell and shell client
  launcher/      App launcher
  greeter/       LightDM greeter
  design/        Tokens, artwork, icons, and generated assets
  boot/          Plymouth and boot asset tooling
  build/         Minimal rootfs and kernel configuration helpers
  wayland/       Wayfire configuration
  waydroid/      Waydroid service and networking templates
  deploy.sh      Copy user-level Luke files to a mounted target
  apply-root.sh  Install root-level runtime and greeter files
```

## Requirements

The target system should provide:

- Debian or Ubuntu with Python 3
- GTK 3 and PyGObject (`python3-gi`)
- A working Wayland session, or an X11 session for development
- `rsync` for deployment
- Optional: WebKitGTK 4.1 for the full Luke Browser experience
- Optional: Wayfire, PipeWire, WirePlumber, and Waydroid for the complete
  Wayland/Android setup

The exact package names vary by distribution. Install packages from the target
distribution rather than mixing Debian and Ubuntu repositories.

## Deploy to a mounted Luke system

Mount the Luke root filesystem, inspect the target path, then run:

```bash
cd luke
./deploy.sh /media/aman/LUKE-ROOT
```

`deploy.sh` checks Python syntax, copies the user-level platform into
`/home/aman/.luke`, installs the autostart entries, and preserves the source
tree as the deployment authority.

The custom greeter and its system packages require a root operation:

```bash
sudo ./apply-root.sh /media/aman/LUKE-ROOT
```

The script is intended to be rerunnable, but always verify the target mount
before using `sudo`. It backs up the existing LightDM configuration before
changing the greeter session.

## Run components locally

For a development session, ensure the repository's `luke` directory is on the
Python import path and run an app directly:

```bash
cd luke
PYTHONPATH="$PWD/framework:$PWD/apps/calculator" \
  python3 apps/calculator/main.py
```

The shell entry point used by the autostart configuration is:

```bash
python3 luke/shell/main.py
```

Some apps interact with desktop services such as NetworkManager, PulseAudio or
LightDM and will only expose their complete functionality inside a matching
desktop session.

## App Store catalog

The built-in App Store reads `catalog/apps.json` from the configured catalog
URL. The default is the raw catalog in this GitHub repository; override it for
development with `LUKE_APP_CATALOG`.

Each catalog entry needs an HTTPS archive URL and an SHA-256 checksum:

```json
{
  "version": 1,
  "apps": [
    {
      "id": "example",
      "name": "Example",
      "version": "1.0",
      "author": "Luke",
      "desc": "An example Luke app",
      "url": "https://example.org/example.tar.gz",
      "sha256": "..."
    }
  ]
}
```

The archive must contain an `app.json` descriptor and its application files.
The store validates the app ID, checksum, and archive paths before installation.
Installed bundles are kept in `~/.luke/store/apps` so normal source deployment
does not remove them. The store supports install, update, and removal of
non-system bundles.

## Validate changes

Run the same syntax check used by deployment:

```bash
cd luke
python3 -m compileall -q design framework apps launcher greeter shell bin tools
```

Review generated assets and target paths before deploying. The repository does
not yet provide a complete automated integration-test suite; hardware, display
manager, Wayland, and Waydroid behavior must be checked on the target system.

## Architecture notes

Luke is intended to run on a minimal Linux root filesystem with a separate data
partition. Wayfire provides the Wayland compositor, Luke provides the desktop
shell and applications, and Waydroid runs Android userspace in a Linux
container rather than a virtual machine.

See [LUKE-DESKTOP-ARCHITECTURE.md](LUKE-DESKTOP-ARCHITECTURE.md) for the full
build, storage, boot, networking, and acceptance guidance. The historical USB
installation notes are in [PORTOS-GUIDE.md](PORTOS-GUIDE.md).

## Status

Luke is an active personal operating-system project. The current roadmap is
tracked in [plan.md](plan.md), including the app store, motion polish, and
device acceptance testing phases.

## License

No license has been declared yet. Until one is added, treat the repository as
all rights reserved and ask before redistributing or reusing the code.