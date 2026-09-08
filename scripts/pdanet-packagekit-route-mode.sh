#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG="/etc/PackageKit/PackageKit.conf"
BACKUP="/etc/PackageKit/PackageKit.conf.pdanet-original"
DROPIN_DIR="/etc/systemd/system/packagekit.service.d"
DROPIN="$DROPIN_DIR/90-pdanet-network.conf"

if [[ $EUID -ne 0 ]]; then
    exit 1
fi

restore_mode() {
    rm -f "$DROPIN"
    if [[ -f "$BACKUP" && -f "$CONFIG" ]]; then
        cp -a "$BACKUP" "$CONFIG"
        rm -f "$BACKUP"
    fi
    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload >/dev/null 2>&1 || true
        systemctl restart packagekit.service >/dev/null 2>&1 || true
    fi
    exit 0
}

if [[ "${1:-}" == "--restore" ]]; then
    restore_mode
fi

# Mint Software Manager talks to PackageKit. PackageKit has two independent
# network-state paths that can both report offline when pdanet0 exists outside
# NetworkManager:
#   1. PackageKit's own NetworkManager integration.
#   2. GLib's GNetworkMonitor, which packagekitd inherits at startup.
# Configure both while PdaNet is active.
if [[ -f "$CONFIG" ]]; then
    if [[ ! -f "$BACKUP" ]]; then
        cp -a "$CONFIG" "$BACKUP"
    fi

    set_key() {
        local key="$1"
        local value="$2"

        if grep -Eq "^[[:space:]]*${key}[[:space:]]*=" "$CONFIG"; then
            sed -Ei "s|^[[:space:]]*${key}[[:space:]]*=.*$|${key}=${value}|" "$CONFIG"
        else
            sed -i "/^[[:space:]]*\[Daemon\][[:space:]]*$/a ${key}=${value}" "$CONFIG"
        fi
    }

    set_key UseNetworkManager false
    set_key UseNetworkHeuristic true
fi

if command -v systemctl >/dev/null 2>&1; then
    PACKAGEKITD="$(command -v packagekitd 2>/dev/null || true)"
    if [[ -z "$PACKAGEKITD" ]]; then
        for candidate in /usr/libexec/packagekitd /usr/lib/packagekit/packagekitd; do
            if [[ -x "$candidate" ]]; then
                PACKAGEKITD="$candidate"
                break
            fi
        done
    fi

    if [[ -n "$PACKAGEKITD" ]]; then
        mkdir -p "$DROPIN_DIR"
        cat > "$DROPIN" <<EOF
[Service]
Environment=GIO_USE_NETWORK_MONITOR=base
ExecStart=
ExecStart=$PACKAGEKITD --keep-environment
EOF
        systemctl daemon-reload >/dev/null 2>&1 || true
        systemctl restart packagekit.service >/dev/null 2>&1 || true
    else
        # Still restart PackageKit so the PackageKit.conf changes take effect.
        systemctl restart packagekit.service >/dev/null 2>&1 || true
    fi
else
    pkill -HUP -x packagekitd >/dev/null 2>&1 || true
fi

exit 0
