#!/usr/bin/env python3
import argparse
import fcntl
import os
import select
import signal
import socket
import struct
import subprocess
import sys
import time

TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
PHONE_PORT = 8739
LOCAL_PORT = 18739
TUN_NAME = 'pdanet0'
TUN_IP = '10.1.19.2'
CLIENT_VERSION = 5030
USB_FLAGS = 0x100

running = True

def log(msg):
    print(msg, flush=True)

def run(cmd, check=True, capture=False):
    return subprocess.run(cmd, check=check, text=True,
                          capture_output=capture)

def adb(*args, check=True, capture=False):
    return run(['adb', *args], check=check, capture=capture)

def make_tun(name=TUN_NAME):
    fd = os.open('/dev/net/tun', os.O_RDWR)
    ifr = struct.pack('16sH', name.encode(), IFF_TUN | IFF_NO_PI)
    res = fcntl.ioctl(fd, TUNSETIFF, ifr)
    actual = res[:16].split(b'\0', 1)[0].decode()
    run(['ip', 'addr', 'replace', f'{TUN_IP}/32', 'dev', actual])
    run(['ip', 'link', 'set', 'dev', actual, 'mtu', '1400', 'up'])
    return fd, actual

def recv_exact(sock, n):
    out = bytearray()
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise ConnectionError('PdaNet phone connection closed')
        out.extend(chunk)
    return bytes(out)

def send_frame(sock, cmd, payload=b'', seq=0, b=0, e=0, f=0, g=0, h=0):
    # Desktop -> Android headers are big-endian and payload length is field d.
    header = struct.pack('>8I', cmd, b, seq, len(payload), e, f, g, h)
    sock.sendall(header + payload)

def recv_frame(sock):
    # Android -> desktop headers are little-endian. In this direction the
    # payload length occupies the fifth integer (field d in Android's frame object).
    header = recv_exact(sock, 32)
    fields = struct.unpack('<8I', header)
    length = fields[4]
    if length > 1024 * 1024:
        raise ValueError(f'Invalid PdaNet frame length {length}')
    payload = recv_exact(sock, length) if length else b''
    return fields, payload

def connect_phone():
    devices = adb('devices', capture=True).stdout.splitlines()
    authorized = [x for x in devices[1:] if x.strip().endswith('\tdevice')]
    if not authorized:
        raise RuntimeError('No authorized Android device found by adb')

    adb('forward', '--remove', f'tcp:{LOCAL_PORT}', check=False)
    adb('forward', f'tcp:{LOCAL_PORT}', f'tcp:{PHONE_PORT}')
    s = socket.create_connection(('127.0.0.1', LOCAL_PORT), timeout=5)
    s.settimeout(None)
    # Initial USB desktop hello. This is the frame PdaNet+ expects from its desktop client.
    s.sendall(struct.pack('>8I', 15, CLIENT_VERSION, 0, 0, 0, 0, 0, USB_FLAGS))
    return s

def cleanup(iface=None):
    try:
        adb('forward', '--remove', f'tcp:{LOCAL_PORT}', check=False)
    except Exception:
        pass
    if iface:
        subprocess.run(['ip', 'link', 'del', iface], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

def main():
    global running
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', action='append', default=[],
                    help='Route CIDR through PdaNet tunnel. May be repeated.')
    ap.add_argument('--default-route', action='store_true',
                    help='Install a low-metric default route through PdaNet.')
    args = ap.parse_args()

    if os.geteuid() != 0:
        print('This tunnel helper must run as root.', file=sys.stderr)
        return 1

    signal.signal(signal.SIGINT, lambda *_: globals().__setitem__('running', False))
    signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__('running', False))

    tun_fd = None
    iface = None
    phone = None
    seq = 1
    try:
        log('[1/4] Creating TUN interface...')
        tun_fd, iface = make_tun()
        log(f'      {iface} = {TUN_IP}')

        log('[2/4] Connecting to PdaNet+ over ADB...')
        phone = connect_phone()
        log(f'      ADB tcp:{LOCAL_PORT} -> phone tcp:{PHONE_PORT}')

        for route in args.route:
            run(['ip', 'route', 'replace', route, 'dev', iface, 'src', TUN_IP])
            log(f'      Route: {route} -> {iface}')
        if args.default_route:
            run(['ip', 'route', 'replace', 'default', 'dev', iface, 'metric', '5'])
            log(f'      Default route -> {iface}')

        log('[3/4] PdaNet USB protocol active.')
        log('[4/4] Forwarding packets. Press Ctrl+C to stop.')

        while running:
            r, _, _ = select.select([tun_fd, phone], [], [], 1.0)
            if tun_fd in r:
                pkt = os.read(tun_fd, 65535)
                if pkt:
                    send_frame(phone, 64, pkt, seq=seq)
                    seq = (seq + 1) & 0xffffffff
            if phone in r:
                fields, payload = recv_frame(phone)
                cmd = fields[0]
                if cmd == 64:
                    if payload:
                        os.write(tun_fd, payload)
                elif cmd == 31:
                    try:
                        log(f'      Phone info[{fields[1]}]: {payload.decode(errors="replace")}')
                    except Exception:
                        pass
                elif cmd == 30:
                    log(f'      Phone ready, app version={fields[5]}')
                elif cmd == 16:
                    raise ConnectionError('PdaNet+ requested disconnect')
        return 0
    except Exception as exc:
        log(f'ERROR: {exc}')
        return 1
    finally:
        if phone:
            try: phone.close()
            except Exception: pass
        if tun_fd is not None:
            try: os.close(tun_fd)
            except Exception: pass
        cleanup(iface)

if __name__ == '__main__':
    raise SystemExit(main())
