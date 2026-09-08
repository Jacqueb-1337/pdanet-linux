#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$ROOT_DIR/dist}"
PKG_LIST="$ROOT_DIR/packaging/runtime-packages.txt"

if [[ ! -f /etc/os-release ]]; then
    echo "Cannot detect Linux distribution." >&2
    exit 1
fi
. /etc/os-release

if ! command -v apt-get >/dev/null 2>&1 || ! command -v apt-cache >/dev/null 2>&1; then
    echo "This builder currently supports Debian/Ubuntu/Mint apt-based systems." >&2
    exit 1
fi

ARCH="$(dpkg --print-architecture)"
BASE_CODENAME="${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}}"
DIST_ID="${ID:-linux}"
DIST_VER="${VERSION_ID:-unknown}"
GIT_VER="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d)"
BUNDLE_NAME="pdanet-linux-offline-${BASE_CODENAME}-${ARCH}-${GIT_VER}"
WORK_DIR="$(mktemp -d)"
PAYLOAD_DIR="$WORK_DIR/$BUNDLE_NAME"
DEB_DIR="$PAYLOAD_DIR/debs"
APP_DIR="$PAYLOAD_DIR/app"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$DEB_DIR" "$APP_DIR" "$OUT_DIR"

if [[ ! -f "$PKG_LIST" ]]; then
    echo "Missing package list: $PKG_LIST" >&2
    exit 1
fi

mapfile -t DIRECT_PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$PKG_LIST")

if apt-cache show gir1.2-appindicator3-0.1 >/dev/null 2>&1; then
    DIRECT_PACKAGES+=(gir1.2-appindicator3-0.1)
elif apt-cache show gir1.2-ayatanaappindicator3-0.1 >/dev/null 2>&1; then
    DIRECT_PACKAGES+=(gir1.2-ayatanaappindicator3-0.1)
else
    echo "Warning: no AppIndicator package is available in the configured repositories." >&2
fi

echo "Refreshing apt metadata..."
if [[ $EUID -eq 0 ]]; then
    apt-get update -qq
elif command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -qq
else
    echo "sudo is required to refresh apt metadata." >&2
    exit 1
fi

if ! command -v dpkg-scanpackages >/dev/null 2>&1; then
    echo "Installing build-only dpkg-dev helper..."
    if [[ $EUID -eq 0 ]]; then
        apt-get install -y -qq dpkg-dev
    else
        sudo apt-get install -y -qq dpkg-dev
    fi
fi

echo "Resolving complete dependency closure for $ARCH..."
EMPTY_STATUS="$WORK_DIR/empty-dpkg-status"
SIM_OUTPUT="$WORK_DIR/apt-simulation.txt"
: > "$EMPTY_STATUS"

# Simulate installation against an empty dpkg database. This makes apt choose
# one real provider for alternatives and gives us the full target-architecture
# dependency closure instead of recursively collecting every possible provider.
if ! apt-get -s \
    -o Dir::State::status="$EMPTY_STATUS" \
    --no-install-recommends \
    install "${DIRECT_PACKAGES[@]}" > "$SIM_OUTPUT" 2>&1; then
    cat "$SIM_OUTPUT" >&2
    echo "Dependency resolution failed." >&2
    exit 1
fi

mapfile -t ALL_PACKAGES < <(grep '^Inst ' "$SIM_OUTPUT" | awk '{print $2}' | sort -u)
if [[ ${#ALL_PACKAGES[@]} -eq 0 ]]; then
    echo "Dependency resolution returned no packages." >&2
    exit 1
fi

echo "Downloading ${#ALL_PACKAGES[@]} packages..."
pushd "$DEB_DIR" >/dev/null
if ! apt-get download "${ALL_PACKAGES[@]}"; then
    echo "One or more dependency packages could not be downloaded." >&2
    exit 1
fi
popd >/dev/null

if ! compgen -G "$DEB_DIR/*.deb" >/dev/null; then
    echo "No .deb packages were downloaded." >&2
    exit 1
fi

echo "Creating local apt repository metadata..."
pushd "$DEB_DIR" >/dev/null
dpkg-scanpackages . /dev/null > Packages
gzip -9c Packages > Packages.gz
popd >/dev/null

printf '%s\n' "${DIRECT_PACKAGES[@]}" > "$PAYLOAD_DIR/direct-packages.txt"

echo "Copying application files..."
tar -C "$ROOT_DIR" \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='.tmp*' \
    --exclude='*.deb' \
    -cf - . | tar -C "$APP_DIR" -xf -

cat > "$PAYLOAD_DIR/bundle-info" <<EOF
DIST_ID=$DIST_ID
DIST_VERSION=$DIST_VER
BASE_CODENAME=$BASE_CODENAME
ARCH=$ARCH
SOURCE_COMMIT=$GIT_VER
EOF

cp "$ROOT_DIR/packaging/install-offline.sh" "$PAYLOAD_DIR/install-offline.sh"
chmod +x "$PAYLOAD_DIR/install-offline.sh"

RUN_FILE="$OUT_DIR/$BUNDLE_NAME.run"
ARCHIVE="$WORK_DIR/payload.tar.gz"
tar -C "$WORK_DIR" -czf "$ARCHIVE" "$BUNDLE_NAME"

cat > "$RUN_FILE" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $EUID -ne 0 ]]; then
    if command -v pkexec >/dev/null 2>&1; then
        exec pkexec /usr/bin/bash "$0" "$@"
    fi
    echo "Administrator access is required to install PdaNet Linux." >&2
    echo "Run this file as administrator, or use: sudo bash $0" >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

MARKER_LINE="$(awk '/^__PDANET_OFFLINE_ARCHIVE__$/ { print NR + 1; exit }' "$0")"
if [[ -z "$MARKER_LINE" ]]; then
    echo "Offline payload marker is missing." >&2
    exit 1
fi

tail -n +"$MARKER_LINE" "$0" | tar -xz -C "$TMP_DIR"
INSTALLER="$(find "$TMP_DIR" -mindepth 2 -maxdepth 2 -name install-offline.sh -print -quit)"
if [[ -z "$INSTALLER" ]]; then
    echo "Offline installer payload is invalid." >&2
    exit 1
fi
"$INSTALLER"
STATUS=$?
exit "$STATUS"
__PDANET_OFFLINE_ARCHIVE__
EOF
cat "$ARCHIVE" >> "$RUN_FILE"
chmod +x "$RUN_FILE"

SIZE="$(du -h "$RUN_FILE" | awk '{print $1}')"
echo
echo "Offline bundle created:"
echo "  $RUN_FILE"
echo "  Size: $SIZE"
echo "  Target base: $BASE_CODENAME / $ARCH"
echo
echo "On the offline machine, install with:"
echo "  sudo ./$BUNDLE_NAME.run"
