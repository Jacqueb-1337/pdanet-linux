#!/usr/bin/env bash
set -Eeuo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SELF_DIR/app"
DEB_DIR="$SELF_DIR/debs"
INFO_FILE="$SELF_DIR/bundle-info"
DIRECT_FILE="$SELF_DIR/direct-packages.txt"

if [[ $EUID -ne 0 ]]; then
    echo "This installer must run as root. Use sudo." >&2
    exit 1
fi

if [[ ! -d "$APP_DIR" || ! -d "$DEB_DIR" || ! -f "$INFO_FILE" || ! -f "$DIRECT_FILE" ]]; then
    echo "Offline bundle is incomplete." >&2
    exit 1
fi

# shellcheck disable=SC1090
. "$INFO_FILE"

if [[ ! -f /etc/os-release ]]; then
    echo "Cannot detect target Linux distribution." >&2
    exit 1
fi
. /etc/os-release

TARGET_ARCH="$(dpkg --print-architecture)"
TARGET_BASE="${UBUNTU_CODENAME:-${VERSION_CODENAME:-unknown}}"

if [[ "$TARGET_ARCH" != "$ARCH" ]]; then
    echo "Wrong bundle architecture. Bundle: $ARCH, system: $TARGET_ARCH" >&2
    exit 1
fi

if [[ "$BASE_CODENAME" != "unknown" && "$TARGET_BASE" != "unknown" && "$TARGET_BASE" != "$BASE_CODENAME" ]]; then
    echo "This bundle was built for the $BASE_CODENAME package base." >&2
    echo "This system reports $TARGET_BASE." >&2
    echo "Build an offline bundle on the same Ubuntu/Mint base release." >&2
    exit 1
fi

mapfile -t DEBS < <(find "$DEB_DIR" -maxdepth 1 -type f -name '*.deb' -print | sort)
mapfile -t DIRECT_PACKAGES < <(grep -Ev '^[[:space:]]*(#|$)' "$DIRECT_FILE")
if [[ ${#DEBS[@]} -eq 0 || ${#DIRECT_PACKAGES[@]} -eq 0 ]]; then
    echo "Dependency payload is missing from the bundle." >&2
    exit 1
fi
if [[ ! -f "$DEB_DIR/Packages" && ! -f "$DEB_DIR/Packages.gz" ]]; then
    echo "Local apt repository metadata is missing." >&2
    exit 1
fi

APT_TMP="$(mktemp -d)"
cleanup_apt() { rm -rf "$APT_TMP"; }
trap cleanup_apt EXIT
mkdir -p "$APT_TMP/lists/partial" "$APT_TMP/sourceparts"
printf 'deb [trusted=yes] file:%s ./\n' "$DEB_DIR" > "$APT_TMP/sources.list"
APT_OPTS=(
    -o "Dir::Etc::sourcelist=$APT_TMP/sources.list"
    -o "Dir::Etc::sourceparts=$APT_TMP/sourceparts"
    -o "Dir::State::lists=$APT_TMP/lists"
    -o "APT::Get::List-Cleanup=0"
)

echo "PdaNet Linux offline installation"
echo "================================="
echo "Package base: $BASE_CODENAME"
echo "Architecture: $ARCH"
echo "Bundled dependency packages: ${#DEBS[@]}"
echo
echo "[1/2] Installing bundled dependencies without network access..."
apt-get "${APT_OPTS[@]}" update -qq
DEBIAN_FRONTEND=noninteractive apt-get "${APT_OPTS[@]}" install -y --no-install-recommends "${DIRECT_PACKAGES[@]}"

echo
echo "[2/2] Installing PdaNet Linux..."
INSTALL_ROOT="/opt/pdanet-linux"
INSTALL_STAGE="/opt/.pdanet-linux-install-$$"
rm -rf "$INSTALL_STAGE"
mkdir -p "$INSTALL_STAGE"
cp -a "$APP_DIR/." "$INSTALL_STAGE/"
rm -rf "$INSTALL_ROOT"
mv "$INSTALL_STAGE" "$INSTALL_ROOT"
chmod +x "$INSTALL_ROOT/install.sh"
"$INSTALL_ROOT/install.sh" --offline

echo
echo "Offline installation complete."
echo "Application files: $INSTALL_ROOT"
echo "You can open PdaNet Linux from the application menu."
