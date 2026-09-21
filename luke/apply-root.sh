#!/bin/bash
# apply-root.sh — root-level installation for the Luke desktop platform.
#
# Run ON THIS HOST with sudo, while the Luke pendrive is mounted:
#     sudo bash /home/aman/Desktop/operating/luke/apply-root.sh
#
# What it does:
#   1. Installs small runtime packages inside Luke:
#        gir1.2-lightdm-1   -> LightDM Python bindings for the custom greeter
#        python3-cairo      -> cairo module needed for drawing (avatar, graphs)
#        pulseaudio-utils   -> pactl, so the Settings app can set volume
#   2. Clears the login password for $LUKE_USER so the greeter is passwordless.
#   3. Installs the custom Luke greeter (login screen) into /usr/local.
#   4. Registers the greeter with LightDM and turns off auto-login.
#
# It is idempotent: safe to run twice.

set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-/media/aman/LUKE-ROOT}"
LUKE_USER="${LUKE_USER:-aman}"

[ -d "$TARGET/etc" ] || { echo "ERROR: Luke root not found at $TARGET"; exit 1; }
[ -x "$TARGET/usr/bin/python3" ] || { echo "ERROR: no python3 inside $TARGET"; exit 1; }

echo "==> bind mounts for chroot"
for d in proc sys dev run; do
  mountpoint -q "$TARGET/$d" || mount --bind "/$d" "$TARGET/$d"
done
cp -f /etc/resolv.conf "$TARGET/etc/resolv.conf" 2>/dev/null || true

echo "==> installing packages inside Luke (gir1.2-lightdm-1, python3-cairo, pulseaudio-utils)"
chroot "$TARGET" /bin/bash -c '
  export DEBIAN_FRONTEND=noninteractive LANG=C
  apt-get update -q
  apt-get install -y --no-install-recommends gir1.2-lightdm-1 python3-cairo pulseaudio-utils
'

echo "==> enabling passwordless sign-in for $LUKE_USER"
chroot "$TARGET" /bin/bash -c "
  if id -u '$LUKE_USER' >/dev/null 2>&1; then
    groupadd -f nopasswdlogin
    usermod -aG nopasswdlogin '$LUKE_USER'
    passwd -d '$LUKE_USER' >/dev/null 2>&1 || true
    echo '    password cleared and nopasswdlogin set for $LUKE_USER'
  else
    echo '    user $LUKE_USER not found; leaving passwords unchanged' >&2
  fi
"

echo "==> installing the Luke greeter (login screen)"
mkdir -p "$TARGET/usr/local/lib/luke/greeter" "$TARGET/usr/local/lib/luke/assets" "$TARGET/usr/local/bin" "$TARGET/usr/share/xgreeters"
cp -f "$SRC/greeter/main.py" "$TARGET/usr/local/lib/luke/greeter/main.py"
cp -f "$SRC/greeter/greeter.css" "$TARGET/usr/local/lib/luke/greeter/greeter.css"
cp -f "$SRC/design/assets/brand/luke-mark-1024.png" "$TARGET/usr/local/lib/luke/assets/luke-mark.png"
cp -f "$SRC/design/assets/wallpapers/luke-wallpaper-1366x768.png" "$TARGET/usr/local/lib/luke/assets/wallpaper.png"
chown -R root:root "$TARGET/usr/local/lib/luke"
chmod 644 "$TARGET/usr/local/lib/luke/greeter"/*.py "$TARGET/usr/local/lib/luke/greeter"/*.css
chmod 644 "$TARGET/usr/local/lib/luke/assets"/*.png

cat > "$TARGET/usr/local/bin/luke-greeter" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/local/lib/luke/greeter/main.py
EOF
chmod 755 "$TARGET/usr/local/bin/luke-greeter"

cat > "$TARGET/usr/share/xgreeters/luke.desktop" <<'EOF'
[Desktop Entry]
Name=Luke Greeter
Comment=Luke login screen
Exec=/usr/local/bin/luke-greeter
Type=Application
EOF
chmod 644 "$TARGET/usr/share/xgreeters/luke.desktop"

echo "==> configuring LightDM (backup + greeter-session=luke, auto-login off)"
CONF="$TARGET/etc/lightdm/lightdm.conf"
if [ -f "$CONF" ]; then
  [ -f "$CONF.lukebak" ] || cp -f "$CONF" "$CONF.lukebak"
fi
grep -vE '^\s*(autologin-user|greeter-session)' "$CONF" 2>/dev/null > "$CONF.new" || true
cat >> "$CONF.new" <<'EOF'
greeter-session=luke
EOF
mv -f "$CONF.new" "$CONF"

echo
echo "==> done."
echo "    Packages installed: gir1.2-lightdm-1, pulseaudio-utils"
echo "    Greeter installed at /usr/local/lib/luke/greeter"
echo "    Passwordless sign-in enabled for $LUKE_USER"
echo "    lightdm.conf updated (auto-login removed, greeter-session=luke)."
echo "    Backup of the old lightdm.conf: $CONF.lukebak"
echo
echo "    NEXT: boot the pendrive. You will land on the new Luke login screen."
echo "    (If anything goes wrong at boot: pick a recovery kernel in GRUB,"
echo "     or restore $CONF.lukebak and rerun.)"