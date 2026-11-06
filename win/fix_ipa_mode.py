#!/usr/bin/env python3
# Put back the executable bit of an IPA's main binary after a signer rebuilt the ZIP with every file at 0644.
# iOS extracts Payload/<App>.app/<App> with the Unix mode stored in the ZIP's central directory; when the mode is 0644 the install fails with
#   invalid progressUpdate, missing InstallProgressDict field:+map[Error:ExtractionFailed]
# Only the central directory's external attributes change: the code signature inside the app is untouched.
# Usage: python win/fix_ipa_mode.py <IPA> [-o OUT]
import argparse, os, plistlib, shutil, struct, sys, zipfile

EOCD = b'PK\x05\x06'
CENTRAL = b'PK\x01\x02'
ZIP64_EOCD = b'PK\x06\x06'
ZIP64_LOCATOR = b'PK\x06\x07'
EXEC = 0o100755


def directory(f, size):
    """(entries, central directory size, central directory offset), reading the ZIP64 record when the EOCD fields overflow."""
    start = max(0, size - 0x10000 - 22)
    f.seek(start)
    tail = f.read()
    pos = len(tail)
    while True:
        at = tail.rfind(EOCD, 0, pos)
        if at < 0:
            sys.exit('not a ZIP (no end of central directory)')
        if at + 22 <= len(tail) and start + at + 22 + struct.unpack_from('<H', tail, at + 20)[0] == size:
            break
        pos = at
    disk, cddisk, n_disk, n, cdsize, cdoff = struct.unpack_from('<HHHHII', tail, at + 4)
    if n == 0xFFFF or cdsize == 0xFFFFFFFF or cdoff == 0xFFFFFFFF:
        f.seek(start + at - 20)
        if f.read(4) != ZIP64_LOCATOR:
            sys.exit('a ZIP64 end of central directory locator is missing')
        f.seek(4, 1)   # the disk with the ZIP64 EOCD, then its offset
        z64 = struct.unpack('<Q', f.read(8))[0]
        f.seek(z64)
        if f.read(4) != ZIP64_EOCD:
            sys.exit('a ZIP64 end of central directory record is missing')
        f.seek(z64 + 32)
        n, cdsize, cdoff = struct.unpack('<QQQ', f.read(24))
    return n, cdsize, cdoff


def main_binaries(z):
    """The main executable of each Payload/<App>.app, from its Info.plist (CFBundleExecutable)."""
    out = []
    for n in z.namelist():
        parts = n.split('/')
        if len(parts) == 3 and parts[0] == 'Payload' and parts[1].endswith('.app') and parts[2] == 'Info.plist':
            try:
                info = plistlib.loads(z.read(n))
            except Exception as e:
                sys.exit(f'{n}: {e}')
            exe = info.get('CFBundleExecutable')
            if not exe:
                sys.exit(f'{n}: no CFBundleExecutable')
            out.append(f'Payload/{parts[1]}/{exe}')
    if not out:
        sys.exit('no Payload/<App>.app/Info.plist in the IPA')
    return out


def patch(ipa, out=None):
    if out and os.path.abspath(out) != os.path.abspath(ipa):
        shutil.copyfile(ipa, out)
        ipa = out
    with zipfile.ZipFile(ipa) as z:
        want = dict.fromkeys(main_binaries(z), EXEC)
    with open(ipa, 'r+b') as f:
        size = f.seek(0, 2)
        n, cdsize, cdoff = directory(f, size)
        f.seek(cdoff)
        cd = f.read(cdsize)
        pos, done = 0, []
        for _ in range(n):
            if cd[pos:pos + 4] != CENTRAL:
                sys.exit(f'{ipa}: bad central directory entry at {pos}')
            nlen, elen, clen = struct.unpack_from('<HHH', cd, pos + 28)
            name = cd[pos + 46:pos + 46 + nlen].decode('utf-8', 'replace')
            if name in want:
                f.seek(cdoff + pos + 38)
                f.write(struct.pack('<I', want[name] << 16))
                done.append(name)
            pos += 46 + nlen + elen + clen
    print(f'{ipa}: {len(done)} executable(s) at 0755' + (': ' + ', '.join(done) if done else ''))
    missing = sorted(set(want) - set(done))
    if missing:
        sys.exit('not found in the central directory: ' + ', '.join(missing))
    with zipfile.ZipFile(ipa) as z:
        for name in want:
            mode = z.getinfo(name).external_attr >> 16
            if mode & 0o111 != 0o111:
                sys.exit(f'{ipa}: {name} still has mode {mode:o}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Set the executable bit of an IPA's main binary (a signer turned it into 0644)")
    ap.add_argument('ipa')
    ap.add_argument('-o', '--out', help='write the fixed IPA here instead of patching it in place')
    a = ap.parse_args()
    patch(a.ipa, a.out)
