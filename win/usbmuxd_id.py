#!/usr/bin/env python3
# Print the DeviceID that PlumeSign expects in --udid/-u, with the tail of each device's UDID to tell them apart.
# PlumeSign's get_device_for_id compares usbmuxd's numeric DeviceID with the argument, not the UDID: passing the real UDID
# fails with "Other error: Device ID <UDID> not found" even though the iPhone is connected. The number printed here is the
# one to pass, and with several devices connected the UDID tail says which phone each line belongs to.
# Usage: python win/usbmuxd_id.py [--host 127.0.0.1] [--port 27015]
import argparse
import plistlib
import socket
import struct
import sys


def devices(host, port):
    msg = plistlib.dumps({'MessageType': 'ListDevices', 'ClientVersionString': '1.0', 'ProgName': 'usbmuxd_id', 'kLibUSBMuxVersion': 3},
                         fmt=plistlib.FMT_XML)
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(struct.pack('<IIII', 16 + len(msg), 1, 8, 1) + msg)
        header = b''
        while len(header) < 16:
            chunk = s.recv(16 - len(header))
            if not chunk:
                sys.exit('usbmuxd closed the connection')
            header += chunk
        length = struct.unpack('<IIII', header)[0]
        body = b''
        while len(body) < length - 16:
            chunk = s.recv(length - 16 - len(body))
            if not chunk:
                break
            body += chunk
    return plistlib.loads(body).get('DeviceList') or []


def main():
    ap = argparse.ArgumentParser(description='List the usbmuxd DeviceID of each connected iPhone/iPad (the number PlumeSign wants in --udid).')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=27015)
    a = ap.parse_args()
    found = devices(a.host, a.port)
    if not found:
        sys.exit('usbmuxd sees no device: cable, locked screen, or "Trust This Computer" not accepted')
    for d in found:
        p = d.get('Properties') or {}
        udid = str(p.get('SerialNumber') or '')
        print(f"{d.get('DeviceID')}\t{p.get('ConnectionType') or '?'}\t...{udid[-6:]}")


if __name__ == '__main__':
    main()
