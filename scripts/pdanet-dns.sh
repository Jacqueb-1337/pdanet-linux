#!/usr/bin/env bash
# Keep the system resolver usable while pdanet0 owns the default route.
# Mint/Ubuntu may otherwise keep a WiFi-provided DNS server that becomes
# unreachable through the PdaNet tunnel. Browsers with DoH can hide this while
# apt, PackageKit and other system applications fail name resolution.

set -Eeuo pipefail

MODE="${1:-apply}"
STATE_DIR="/var/lib/pdanet-linux/dns-state"
RESOLV_CONF="/etc/resolv.conf"
TEST_HOST="archive.ubuntu.com"

if [[ $EUID -ne 0 ]]; then
    exit 1
fi

resolver_works() {
    getent ahostsv4 "$TEST_HOST" >/dev/null 2>&1
}

save_original_resolver() {
    mkdir -p "$STATE_DIR"
    if [[ -e "$STATE_DIR/saved" ]]; then
        return 0
    fi

    if [[ -L "$RESOLV_CONF" ]]; then
        readlink "$RESOLV_CONF" > "$STATE_DIR/original-symlink"
    elif [[ -e "$RESOLV_CONF" ]]; then
        cp -a "$RESOLV_CONF" "$STATE_DIR/original-file"
    else
        : > "$STATE_DIR/original-missing"
    fi
    : > "$STATE_DIR/saved"
}

install_static_resolver() {
    save_original_resolver
    rm -f "$RESOLV_CONF"
    cat > "$RESOLV_CONF" <<'EOF'
# Managed temporarily by PdaNet Linux while pdanet0 is active.
nameserver 1.1.1.1
nameserver 1.0.0.1
nameserver 8.8.8.8
options timeout:2 attempts:2
EOF
    chmod 0644 "$RESOLV_CONF"
}

apply_dns() {
    # First use systemd-resolved's supported per-link API where available.
    if command -v resolvectl >/dev/null 2>&1 && resolvectl status >/dev/null 2>&1; then
        resolvectl dns pdanet0 1.1.1.1 1.0.0.1 8.8.8.8 >/dev/null 2>&1 || true
        resolvectl domain pdanet0 '~.' >/dev/null 2>&1 || true
        resolvectl default-route pdanet0 yes >/dev/null 2>&1 || true
        resolvectl flush-caches >/dev/null 2>&1 || true
    fi

    if resolver_works; then
        return 0
    fi

    # Some Mint configurations keep /etc/resolv.conf pointed at a resolver that
    # does not honor the unmanaged TUN link. Fall back to a temporary static
    # resolver. DNS packets still travel through pdanet0 because it is the
    # kernel default route.
    install_static_resolver

    command -v resolvectl >/dev/null 2>&1 && resolvectl flush-caches >/dev/null 2>&1 || true
    sleep 0.2
    resolver_works
}

restore_dns() {
    if command -v resolvectl >/dev/null 2>&1; then
        resolvectl revert pdanet0 >/dev/null 2>&1 || true
        resolvectl flush-caches >/dev/null 2>&1 || true
    fi

    if [[ ! -e "$STATE_DIR/saved" ]]; then
        return 0
    fi

    rm -f "$RESOLV_CONF"
    if [[ -f "$STATE_DIR/original-symlink" ]]; then
        ln -s "$(cat "$STATE_DIR/original-symlink")" "$RESOLV_CONF"
    elif [[ -e "$STATE_DIR/original-file" ]]; then
        cp -a "$STATE_DIR/original-file" "$RESOLV_CONF"
    elif [[ -e "$STATE_DIR/original-missing" ]]; then
        :
    fi

    rm -rf "$STATE_DIR"
    command -v resolvectl >/dev/null 2>&1 && resolvectl flush-caches >/dev/null 2>&1 || true
}

case "$MODE" in
    apply)
        apply_dns
        ;;
    restore)
        restore_dns
        ;;
    check)
        resolver_works
        ;;
    *)
        echo "Usage: $0 {apply|restore|check}" >&2
        exit 2
        ;;
esac
