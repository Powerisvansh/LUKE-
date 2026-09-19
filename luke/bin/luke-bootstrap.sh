#!/bin/bash
# Luke session bootstrap — runs once per login from XDG autostart.
# Idempotent. Only touches the current user's own settings.
LUKE="$HOME/.luke"

# regenerate .desktop launchers from the registry
python3 "$LUKE/tools/gen-desktops.py" >/dev/null 2>&1 || true

# app-drawer shortcut: Super + L
if command -v xfconf-query >/dev/null 2>&1; then
  xfconf-query -c xfce4-keyboard-shortcuts \
    -p "/commands/custom/<Super>l" \
    -s "$LUKE/bin/luke-launcher" \
    --create --type string >/dev/null 2>&1 || true
fi

# quick-settings shortcut: Super + S
if command -v xfconf-query >/dev/null 2>&1; then
  xfconf-query -c xfce4-keyboard-shortcuts \
    -p "/commands/custom/<Super>s" \
    -s "$LUKE/bin/luke-quick" \
    --create --type string >/dev/null 2>&1 || true
fi

# one-time dock tweak (adds the launcher button)
if [ -f "$LUKE/tools/dock.py" ]; then
  if python3 "$LUKE/tools/dock.py" 2>/dev/null | grep -q "dock updated"; then
    command -v xfce4-panel >/dev/null 2>&1 && xfce4-panel -r &
  fi
fi

exit 0