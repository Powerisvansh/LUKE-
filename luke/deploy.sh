#!/bin/bash
# Deploy the Luke platform (user-level files) from this source tree to the
# pendrive target. Requires no root: writes only into the target's $HOME.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-/media/aman/LUKE-ROOT}"
HOME_TGT="$TARGET/home/aman/.luke"

[ -d "$TARGET/home/aman" ] || { echo "ERROR: target home not found at $TARGET"; exit 1; }

cd "$SRC"
if ! python3 -m compileall -q design framework apps launcher greeter shell bin tools 2>/dev/null; then
  echo "ERROR: python syntax check failed"; exit 1
fi

mkdir -p "$HOME_TGT"
for d in framework apps tools launcher greeter shell bin design; do
  if [ -d "$SRC/$d" ]; then
    rsync -a --delete "$SRC/$d/" "$HOME_TGT/$d/"
  fi
done
cp -f "$SRC/apps.json" "$HOME_TGT/apps.json"

mkdir -p "$TARGET/home/aman/.config/autostart"
cp -f "$SRC/autostart/luke-bootstrap.desktop" \
      "$TARGET/home/aman/.config/autostart/luke-bootstrap.desktop"

chmod -R u+rwX "$HOME_TGT"
chmod +x "$HOME_TGT/bin/"* 2>/dev/null || true
[ -d "$HOME_TGT/tools" ] && chmod +x "$HOME_TGT/tools/"*.py 2>/dev/null || true
echo "Deployed Luke platform to $HOME_TGT"