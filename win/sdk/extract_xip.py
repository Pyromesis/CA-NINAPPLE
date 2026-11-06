#!/usr/bin/env python3
# Extract the iPhoneOS SDK from Xcode_<version>.xip on Windows (no Mac, no xar / pbzx / cpio tools needed).
# A .xip is a xar archive whose "Content" file is a pbzx stream (a series of xz-compressed chunks) of a cpio archive of Xcode.app. This streams it once, decompressing the
# chunks in parallel, and writes only the entries under Platforms/iPhoneOS.platform/Developer/SDKs/ (about 2 GB of the 40 GB app); everything else is skipped while reading.
# Symlinks inside the SDK are written as copies of their targets (Windows symlinks need extra rights); the SDK-name alias (iPhoneOS<ver>.sdk → iPhoneOS.sdk) is skipped.
# Usage: extract_xip.py <Xcode.xip> [output folder (default win/sdk/out)]
# Get Xcode from https://developer.apple.com/download/all/ (a free Apple ID); the Xcode and Apple SDKs Agreement applies to what you extract.
import concurrent.futures as cf, lzma, os, shutil, struct, sys, time, zlib
import xml.etree.ElementTree as ET
from pathlib import Path

WANT = '/Platforms/iPhoneOS.platform/Developer/SDKs/'


def xar_content(f):
    """(offset, length, encoding) of the xar archive's "Content" file"""
    hdr = f.read(28)
    if hdr[:4] != b'xar!': sys.exit('not a xar / xip archive')
    hsize, _ver, toc_c, _toc_u = struct.unpack('>HHQQ', hdr[4:24])
    f.seek(hsize); toc = zlib.decompress(f.read(toc_c))
    heap = hsize + toc_c
    for fe in ET.fromstring(toc).iter('file'):
        if (fe.findtext('name') or '') == 'Content':
            d = fe.find('data')
            enc = d.find('encoding').get('style') if d.find('encoding') is not None else ''
            return heap + int(d.findtext('offset')), int(d.findtext('length')), enc
    sys.exit('no Content file in the xip')


def pbzx_chunks(f, start, length):
    """the raw chunks of the pbzx stream, in order"""
    f.seek(start); end = start + length
    if f.read(4) != b'pbzx': sys.exit('the Content file is not a pbzx stream')
    f.read(8)   # chunk size
    while f.tell() < end:
        h = f.read(16)
        if len(h) < 16: break
        _flags, size = struct.unpack('>QQ', h)
        yield f.read(size)


def unpack(chunk):
    return lzma.decompress(chunk, format=lzma.FORMAT_XZ) if chunk[:6] == b'\xfd7zXZ\x00' else chunk


def stream(f, start, length, workers):
    """the cpio bytes, decompressed in parallel (chunks are independent xz streams) and yielded in order"""
    with cf.ThreadPoolExecutor(workers) as ex:
        pend = []
        for ch in pbzx_chunks(f, start, length):
            pend.append(ex.submit(unpack, ch))
            if len(pend) >= workers * 2: yield pend.pop(0).result()
        for p in pend: yield p.result()


class Reader:
    def __init__(self, it): self.it, self.buf, self.pos, self.total = it, bytearray(), 0, 0
    def read(self, n):
        while len(self.buf) - self.pos < n:
            try: c = next(self.it)
            except StopIteration: break
            if self.pos: del self.buf[:self.pos]; self.pos = 0
            self.buf += c
        out = bytes(self.buf[self.pos:self.pos + n]); self.pos += len(out); self.total += len(out)
        return out
    def skip(self, n):
        while n > 0:
            k = len(self.buf) - self.pos
            if k == 0:
                try: c = next(self.it)
                except StopIteration: return
                self.buf = bytearray(c); self.pos = 0; continue
            s = min(k, n); self.pos += s; self.total += s; n -= s


def entries(r):
    """(name, mode, ino, data_size) of each cpio entry; the caller reads or skips the data"""
    while True:
        magic = r.read(6)
        if not magic: return
        if magic == b'070707':   # odc
            h = r.read(70)
            ino, mode = int(h[6:12], 8), int(h[12:18], 8)
            namesize, size = int(h[53:59], 8), int(h[59:70], 8)
            name = r.read(namesize)[:-1].decode('utf-8', 'surrogateescape'); pad = 0
        elif magic in (b'070701', b'070702'):   # newc
            h = r.read(104)
            fld = [int(h[i:i + 8], 16) for i in range(0, 104, 8)]
            ino, mode, size, namesize = fld[0], fld[1], fld[6], fld[11]
            name = r.read(namesize)[:-1].decode('utf-8', 'surrogateescape')
            r.skip((-(110 + namesize)) % 4); pad = (-size) % 4
        else: sys.exit(f'unknown cpio header {magic!r} at byte {r.total}')
        if name == 'TRAILER!!!': return
        yield name, mode, ino, size, pad


CANARY = b'NULLcanary'   # the data of a hard link whose bytes another entry of the same inode carries (Xcode 27's sorted, deduplicated cpio: Metadata xbs_sortcpio)


def is_canary(head, size): return size >= len(CANARY) and head.startswith(CANARY) and not head[len(CANARY):].strip(b'\0')


def scan(f, start, length):
    """Pass 1: for each SDK file whose data is a canary, the inode key (ino, size) it needs, and which keys some entry carries real bytes for"""
    need, have, r = {}, set(), Reader(stream(f, start, length, os.cpu_count() or 4))
    for name, mode, ino, size, pad in entries(r):
        if mode & 0o170000 == 0o100000 and size:
            head = r.read(min(size, 64)); r.skip(size - len(head))
            i = name.find(WANT)
            if is_canary(head, size):
                if i >= 0: need.setdefault((ino, size), []).append(name[i + len(WANT):])
            else: have.add((ino, size))
        else: r.skip(size)
        r.skip(pad)
    return need, have


def materialize(out, links):
    """write each symlink as a copy of its target, resolving links through links (Versions/Current → A) until nothing more resolves"""
    todo = [(rel, t) for rel, t in links if '/' in rel.rstrip('/')]   # not the SDK-name alias next to the SDK folder
    while True:
        left = []
        for rel, target in todo:
            dst = out / rel
            src = (dst.parent / target) if not target.startswith('/') else None
            if src is None: print(f'  link {rel} → {target}: absolute, skipped'); continue
            src = Path(os.path.normpath(src))   # collapse '..': the raw path can pass MAX_PATH while the real one fits
            if dst.exists(): continue
            if not src.exists(): left.append((rel, target)); continue
            if src.is_dir(): shutil.copytree(src, dst)
            else: dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
        if len(left) == len(todo):
            for rel, target in left: print(f'  link {rel} → {target}: target not in the SDK, skipped')
            return
        todo = left


def main():
    if len(sys.argv) < 2: sys.exit(__doc__ or 'usage: extract_xip.py <Xcode.xip> [out]')
    xip = Path(sys.argv[1]); out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / 'out'
    out.mkdir(parents=True, exist_ok=True)
    t0, n, links = time.time(), 0, []
    with open(xip, 'rb') as f:
        start, length, enc = xar_content(f)
        print(f'xip: Content {length / 2**30:.1f} GB ({enc or "raw"}); writing the iPhoneOS SDK to {out}', flush=True)
        need, have = scan(f, start, length)
        lost = sum(len(v) for k, v in need.items() if k not in have)
        print(f'  pass 1: {sum(map(len, need.values()))} SDK files are hard links whose bytes another entry carries' + (f' ({lost} with no carrier)' if lost else ''), flush=True)
        r = Reader(stream(f, start, length, os.cpu_count() or 4))
        last, done = time.time(), set()
        for name, mode, ino, size, pad in entries(r):
            i = name.find(WANT)
            rel = name[i + len(WANT):] if i >= 0 else None
            kind, key = mode & 0o170000, (ino, size)
            if rel and kind == 0o120000:   # symlink: its target is the data
                links.append((rel, r.read(size).decode('utf-8', 'surrogateescape')))
            elif kind == 0o100000:
                head = r.read(min(size, 64))
                canary = is_canary(head, size)
                dsts = [out / rel] if rel and not canary else []
                if not canary and key in need and key not in done: dsts += [out / p for p in need[key]]; done.add(key)   # the carrier: also every canary link of this inode
                if dsts:
                    for d in dsts: d.parent.mkdir(parents=True, exist_ok=True)
                    for d in dsts: d.write_bytes(head)
                    if size > len(head):
                        fs = [open(d, 'ab') for d in dsts]
                        try:
                            left = size - len(head)
                            while left:
                                b = r.read(min(left, 1 << 22))
                                if not b: sys.exit('the cpio stream ended inside a file')
                                for o in fs: o.write(b)
                                left -= len(b)
                        finally:
                            for o in fs: o.close()
                    n += len(dsts)
                else: r.skip(size - len(head))
            else:
                if rel and kind == 0o040000: (out / rel).mkdir(parents=True, exist_ok=True)
                r.skip(size)
            r.skip(pad)
            if time.time() - last > 10: last = time.time(); print(f'  {r.total / 2**30:.1f} GB read, {n} SDK files', flush=True)
    materialize(out, links)
    bad = [p for p in out.rglob('*') if p.is_file() and p.stat().st_size >= len(CANARY) and is_canary(p.open('rb').read(64), p.stat().st_size)]
    if bad: print(f'  WARNING: {len(bad)} files still hold a canary, e.g. {bad[0]}')
    sdks = sorted(p for p in out.iterdir() if p.suffix == '.sdk' and p.is_dir())
    print(f'done in {time.time() - t0:.0f} s: {n} files; SDK folders: {", ".join(p.name for p in sdks) or "none"}')
    if sdks: print(f'set it with: NXW_IOS_SDK={sdks[-1]}  (or "ios_sdk" in win/toolchain.json)')


if __name__ == '__main__':
    main()
