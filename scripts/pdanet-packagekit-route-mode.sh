#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG="/etc/PackageKit/PackageKit.conf"
BACKUP="/etc/PackageKit/PackageKit.conf.pdanet-original"

if [[ $EUID -ne 0 ]]; then
    exit 1
fi

# Mint Software Manager uses PackageKit, and PackageKit normally trusts
# NetworkManager's online/offline state. pdanet0 is created outside
# NetworkManager, so PackageKit can incorrectly report "offline" while the
# machine has working Internet. Tell PackageKit to use the kernel default-route
# heuristic instead, which correctly sees pdanet0 and also works with ordinary
# WiFi/Ethernet after PdaNet disconnects.
if [[ ! -f "$CONFIG" ]]; then
    exit 0
fi

if [[ ! -f "$BACKUP" ]]; then
    cp -a "$CONFIG" "$BACKUP"
fi

changed=false

set_key() {
    local key="$1"
    local value="$2"

    if grep -Eq "^[[:space:]]*${key}[[:space:]]*=" "$CONFIG"; then
        if ! grep -Eq "^[[:space:]]*${key}[[:space:]]*=[[:space:]]*${value}[[:space:]]*$" "$CONFIG"; then
            sed -Ei "s|^[[:space:]]*${key}[[:space:]]*=.*$|${key}=${value}|" "$CONFIG"
            changed=true
        fi
    else
        # PackageKit.conf on Mint has a [Daemon] section. Insert our setting
        # directly under it so the change remains valid even if defaults differ.
        sed -i "/^[[:space:]]*\[Daemon\][[:space:]]*$/a ${key}=${value}" "$CONFIG"
        changed=true
    fi
}

set_key UseNetworkManager false
set_key UseNetworkHeuristic true

if [[ "$changed" == true ]]; then
    if command -v systemctl >/dev/null 2>&1; then
        systemctl restart packagekit.service >/dev/null 2>&1 || true
    else
        pkill -HUP -x packagekitd >/dev/null 2>&1 || true
    fi
fi

exit 0
