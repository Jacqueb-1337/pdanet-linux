#!/usr/bin/env bash
set -u

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_PATH")")"
CONNECT="$PROJECT_DIR/pdanet-connect"
TUN_PIDFILE="/run/pdanet-linux-usb.pid"
WATCHDOG_PIDFILE="/run/pdanet-linux-watchdog.pid"
LOGFILE="/tmp/pdanet-linux-watchdog.log"

if [[ $EUID -ne 0 ]]; then
    exit 1
fi

# Keep ADB authorization working even when the watchdog was launched through
# pkexec. The Android key belongs to the desktop user, not root.
REAL_UID="${PKEXEC_UID:-}"
if [[ -z "$REAL_UID" && -n "${SUDO_USER:-}" ]]; then
    REAL_UID="$(id -u "$SUDO_USER" 2>/dev/null || true)"
fi
if [[ -n "$REAL_UID" && "$REAL_UID" != "0" ]]; then
    USER_HOME="$(getent passwd "$REAL_UID" 2>/dev/null | cut -d: -f6 || true)"
    if [[ -n "$USER_HOME" ]]; then
        export HOME="$USER_HOME"
        export ADB_VENDOR_KEYS="$USER_HOME/.android"
    fi
fi

echo $$ > "$WATCHDOG_PIDFILE"
cleanup() {
    if [[ -f "$WATCHDOG_PIDFILE" ]] && [[ "$(cat "$WATCHDOG_PIDFILE" 2>/dev/null || true)" == "$$" ]]; then
        rm -f "$WATCHDOG_PIDFILE"
    fi
}
trap cleanup EXIT INT TERM

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOGFILE"
}

apply_route_and_dns() {
    if ip link show pdanet0 >/dev/null 2>&1; then
        if ! ip route get 1.1.1.1 2>/dev/null | grep -q 'dev pdanet0'; then
            ip route replace default dev pdanet0 metric 5 >/dev/null 2>&1 || true
            log "Repaired PdaNet default route"
        fi

        if command -v resolvectl >/dev/null 2>&1 && resolvectl status >/dev/null 2>&1; then
            resolvectl dns pdanet0 1.1.1.1 1.0.0.1 8.8.8.8 >/dev/null 2>&1 || true
            resolvectl domain pdanet0 '~.' >/dev/null 2>&1 || true
            resolvectl default-route pdanet0 yes >/dev/null 2>&1 || true
        fi
    fi
}

restart_tunnel() {
    log "Restarting stalled PdaNet tunnel"
    if [[ -f "$TUN_PIDFILE" ]]; then
        local pid
        pid="$(cat "$TUN_PIDFILE" 2>/dev/null || true)"
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$TUN_PIDFILE"
    fi
    ip link del pdanet0 >/dev/null 2>&1 || true
    adb forward --remove tcp:18739 >/dev/null 2>&1 || true
    sleep 1

    if PDANET_SKIP_WATCHDOG=1 "$CONNECT" >> "$LOGFILE" 2>&1; then
        log "Tunnel restart succeeded"
        return 0
    fi
    log "Tunnel restart failed"
    return 1
}

raw_failures=0
dns_failures=0
log "Watchdog started"

while true; do
    sleep 10

    if [[ ! -f "$TUN_PIDFILE" ]]; then
        log "Tunnel PID file missing, attempting recovery"
        restart_tunnel || true
        continue
    fi

    tun_pid="$(cat "$TUN_PIDFILE" 2>/dev/null || true)"
    if [[ -z "$tun_pid" ]] || ! kill -0 "$tun_pid" 2>/dev/null || ! ip link show pdanet0 >/dev/null 2>&1; then
        raw_failures=$((raw_failures + 1))
        if (( raw_failures >= 2 )); then
            restart_tunnel || true
            raw_failures=0
            dns_failures=0
        fi
        continue
    fi

    apply_route_and_dns

    if curl -k -sS --interface pdanet0 --connect-timeout 3 --max-time 6 https://1.1.1.1/cdn-cgi/trace >/dev/null 2>&1; then
        raw_failures=0
    else
        raw_failures=$((raw_failures + 1))
        log "Raw tunnel health check failed ($raw_failures/3)"
        if (( raw_failures >= 3 )); then
            restart_tunnel || true
            raw_failures=0
            dns_failures=0
        fi
        continue
    fi

    if getent ahostsv4 example.com >/dev/null 2>&1; then
        dns_failures=0
    else
        dns_failures=$((dns_failures + 1))
        log "DNS health check failed ($dns_failures/2), reapplying PdaNet DNS"
        apply_route_and_dns
        command -v resolvectl >/dev/null 2>&1 && resolvectl flush-caches >/dev/null 2>&1 || true
        if (( dns_failures >= 2 )); then
            sleep 1
            if getent ahostsv4 example.com >/dev/null 2>&1; then
                dns_failures=0
                log "DNS recovered"
            fi
        fi
    fi
done
