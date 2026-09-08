#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/dist"
WORK_DIR="$(mktemp -d)"
cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

mkdir -p "$OUT_DIR"
GIT_VER="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
PAYLOAD="$WORK_DIR/pdanet-linux-update-$GIT_VER"
APP="$PAYLOAD/app"
mkdir -p "$APP/packaging"

# Only ship application/runtime files. Dependencies stay installed from the
# initial full offline bundle, so this update remains small and portable.
cp -a "$ROOT_DIR/src" "$APP/"
cp -a "$ROOT_DIR/config" "$APP/"
cp -a "$ROOT_DIR/scripts" "$APP/"
cp "$ROOT_DIR/pdanet-connect" "$APP/"
cp "$ROOT_DIR/pdanet-disconnect" "$APP/"
cp "$ROOT_DIR/pdanet-wifi-connect" "$APP/"
cp "$ROOT_DIR/pdanet-wifi-disconnect" "$APP/"
cp "$ROOT_DIR/pdanet-iphone-connect" "$APP/"
cp "$ROOT_DIR/pdanet-iphone-disconnect" "$APP/"
cp "$ROOT_DIR/install.sh" "$APP/"
cp "$ROOT_DIR/check_dependencies.py" "$APP/"
cp "$ROOT_DIR/packaging/runtime-packages.txt" "$APP/packaging/"

cat > "$PAYLOAD/update-info" <<EOF
SOURCE_COMMIT=$GIT_VER
EOF

RUN_FILE="$OUT_DIR/pdanet-linux-update-$GIT_VER.run"
ARCHIVE="$WORK_DIR/payload.tar.gz"
tar -C "$WORK_DIR" -czf "$ARCHIVE" "$(basename "$PAYLOAD")"

cat > "$RUN_FILE" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec /usr/bin/bash "$0" "$@"
    fi
    echo "Administrator access is required to update PdaNet Linux." >&2
    echo "Use: sudo bash $0" >&2
    exit 1
fi

INSTALL_ROOT="/opt/pdanet-linux"
if [[ ! -d "$INSTALL_ROOT/src" || ! -f "$INSTALL_ROOT/pdanet-connect" ]]; then
    echo "PdaNet Linux is not installed in $INSTALL_ROOT." >&2
    echo "Install the full offline package first." >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

MARKER_LINE="$(awk '/^__PDANET_UPDATE_ARCHIVE__$/ { print NR + 1; exit }' "$0")"
if [[ -z "$MARKER_LINE" ]]; then
    echo "Update payload marker is missing." >&2
    exit 1
fi

tail -n +"$MARKER_LINE" "$0" | tar -xz -C "$TMP_DIR"
PAYLOAD_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d -name 'pdanet-linux-update-*' -print -quit)"
if [[ -z "$PAYLOAD_DIR" || ! -d "$PAYLOAD_DIR/app/src" ]]; then
    echo "Update payload is invalid." >&2
    exit 1
fi

# Stop the GUI if it is open. Do not kill an active USB tunnel unless the
# updated connection code requires the user to reconnect later.
pkill -f '[p]danet_gui_v2.py' 2>/dev/null || true

BACKUP_DIR="/opt/pdanet-linux-backup"
rm -rf "$BACKUP_DIR"
cp -a "$INSTALL_ROOT" "$BACKUP_DIR"

# Overlay updated runtime files while preserving any files not part of this
# patch. User settings live outside /opt and are not touched.
cp -a "$PAYLOAD_DIR/app/." "$INSTALL_ROOT/"

chmod +x "$INSTALL_ROOT/pdanet-connect" \
         "$INSTALL_ROOT/pdanet-disconnect" \
         "$INSTALL_ROOT/pdanet-wifi-connect" \
         "$INSTALL_ROOT/pdanet-wifi-disconnect" \
         "$INSTALL_ROOT/pdanet-iphone-connect" \
         "$INSTALL_ROOT/pdanet-iphone-disconnect" \
         "$INSTALL_ROOT/src/pdanet_gui_v2.py" \
         "$INSTALL_ROOT/src/pdanet_usb_tunnel.py" \
         "$INSTALL_ROOT/scripts/pdanet-watchdog.sh"

# If USB tethering is already active, enable the new self-healing watchdog
# immediately. This avoids requiring a disconnect/reconnect after an update.
if ip link show pdanet0 >/dev/null 2>&1 && [[ -f /run/pdanet-linux-usb.pid ]]; then
    WATCHDOG_PID="$(cat /run/pdanet-linux-watchdog.pid 2>/dev/null || true)"
    if [[ -z "$WATCHDOG_PID" ]] || ! kill -0 "$WATCHDOG_PID" 2>/dev/null; then
        rm -f /run/pdanet-linux-watchdog.pid
        nohup "$INSTALL_ROOT/scripts/pdanet-watchdog.sh" >/dev/null 2>&1 &
    fi
fi

# Refresh files that are copied outside /opt by the full installer.
if [[ -f "$INSTALL_ROOT/config/redsocks.conf" ]]; then
    install -m 0644 "$INSTALL_ROOT/config/redsocks.conf" /etc/redsocks.conf
fi
if [[ -f "$INSTALL_ROOT/config/pdanet-linux-v2.desktop" ]]; then
    install -m 0644 "$INSTALL_ROOT/config/pdanet-linux-v2.desktop" /usr/share/applications/pdanet-linux.desktop
fi
if [[ -f "$INSTALL_ROOT/config/polkit/org.pdanetlinux.pkexec.policy" ]]; then
    install -m 0644 "$INSTALL_ROOT/config/polkit/org.pdanetlinux.pkexec.policy" /usr/share/polkit-1/actions/org.pdanetlinux.pkexec.policy
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi

COMMIT="$(sed -n 's/^SOURCE_COMMIT=//p' "$PAYLOAD_DIR/update-info" 2>/dev/null | head -1)"
echo "PdaNet Linux update installed successfully."
echo "Version: ${COMMIT:-unknown}"
echo "A rollback copy is available at $BACKUP_DIR until the next update."
echo "Open PdaNet Linux from the application menu."
exit 0
__PDANET_UPDATE_ARCHIVE__
EOF
cat "$ARCHIVE" >> "$RUN_FILE"
chmod +x "$RUN_FILE"

SIZE="$(du -h "$RUN_FILE" | awk '{print $1}')"
echo "Application-only updater created: $RUN_FILE"
echo "Size: $SIZE"
