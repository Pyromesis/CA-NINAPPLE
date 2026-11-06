# Game mods for the Windows build, in the layout Switch emulators and Atmosphere use, from a "mods" folder beside the game files:
#   mods/<any name>/exefs/<build ID>.ips | *.pchtxt     code patches (IPS / IPS32 by the module's build ID; pchtxt with @nsobid-<build ID>, @enabled / @disabled blocks)
#   mods/<any name>/romfs/...                          files that replace the game's (or add to them)
#   mods/atmosphere/contents/<title ID>/exefs|romfs    the same, as on a console's SD card
# Code patches become rewriter cuts (dm/tools/patch_nso.py "Registered patches": the original bytes are asserted, then replaced before the rewrite), so they reach the iPhone
# as the profile's own patches do: they apply only to the module whose build ID they name, and a patch for another game version is reported and skipped.
# A patch overlapping a cut the game profile already makes is skipped too (the profile's fix wins). RomFS files are overlaid on the packed version's RomFS by hard links.
import os, re, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'dm/tools'))
NSO_HEADER = 0x100   # IPS offsets count the NSO header (Atmosphere's convention)


def find(mods_dir):
    """(code patch files, romfs folders) under mods_dir"""
    mods_dir = Path(mods_dir)
    if not mods_dir.is_dir(): return [], []
    patches, romfs = [], []
    for dp, dns, fns in os.walk(mods_dir):
        for d in list(dns):
            if d.lower() == 'romfs': romfs.append(Path(dp) / d); dns.remove(d)   # its contents are files to overlay, not more mods
        for f in fns:
            if f.lower().endswith(('.ips', '.pchtxt')) and Path(dp).name.lower() == 'exefs' or f.lower().endswith('.pchtxt'):
                patches.append(Path(dp) / f)
    return sorted(set(patches)), sorted(romfs)


def parse_ips(data):
    if data[:5] == b'PATCH': n, end = 3, b'EOF'
    elif data[:5] == b'IPS32': n, end = 4, b'EEOF'
    else: raise ValueError('not an IPS / IPS32 file')
    i, out = 5, []
    while i < len(data):
        if data[i:i + len(end)] == end and i + len(end) >= len(data) - 3: break
        off = int.from_bytes(data[i:i + n], 'big'); i += n
        size = int.from_bytes(data[i:i + 2], 'big'); i += 2
        if size == 0:   # RLE record
            rl = int.from_bytes(data[i:i + 2], 'big'); out.append((off, data[i + 2:i + 3] * rl)); i += 3
        else: out.append((off, data[i:i + size])); i += size
    return out


def parse_pchtxt(text):
    """[(build ID, [(offset in the IPS sense, bytes)])]"""
    groups, bid, shift, on, recs = [], None, 0, False, []
    def flush():
        if bid and recs: groups.append((bid, list(recs)))
        recs.clear()
    for raw in text.splitlines():
        line = raw.split('//')[0].strip()
        if not line: continue
        low = line.lower()
        if low.startswith('@nsobid-'): flush(); bid = re.sub(r'[^0-9a-f]', '', low[8:]); on = False
        elif low.startswith('@flag offset_shift'): shift = int(line.split()[-1], 0)
        elif low.startswith('@enabled'): on = True
        elif low.startswith('@disabled'): on = False
        elif low.startswith('@stop'): break
        elif low.startswith('@'): continue
        elif on:
            m = re.match(r'([0-9a-fA-F]+)\s+(?:"((?:[^"\\]|\\.)*)"|([0-9a-fA-F]+))', line)
            if not m: continue
            off = int(m.group(1), 16) + shift
            val = bytes(m.group(2), 'utf-8').decode('unicode_escape').encode('latin1') + b'\0' if m.group(2) is not None else bytes.fromhex(m.group(3))
            recs.append((off, val))
    flush()
    return groups


def module_images(exe_dir, names):
    import nso2elf
    out = {}
    for n in names:
        p = Path(exe_dir) / n
        if p.is_file():
            img, segs, bss, bid = nso2elf.load(str(p))
            out[bid.hex()[:32]] = (n, img, segs[0][0] + segs[0][1])
    return out


def cuts_for(patch_files, exe_dir, names, registered=None, log=print):
    """{build ID: [[offset, original hex, new hex, reason]]} for the modules in exe_dir; registered: {build ID: profile cuts} to keep clear of"""
    mods = module_images(exe_dir, names)
    out = {}
    for pf in patch_files:
        try:
            if pf.suffix.lower() == '.pchtxt': groups = parse_pchtxt(pf.read_text(encoding='utf-8', errors='replace'))
            else: groups = [(re.sub(r'[^0-9a-f]', '', pf.stem.lower()), parse_ips(pf.read_bytes()))]
        except ValueError as e: log(f'[RED] mod {pf}: {e}; skipped'); continue
        for bid, recs in groups:
            hit = next((k for k in mods if bid and (bid.startswith(k) or k.startswith(bid[:32]))), None)
            if not hit:
                log(f'mod {pf.parent.parent.name}/{pf.name}: for build {bid[:16] or "?"}, which is not a module of this game version ({", ".join(m[0] + " " + k[:16] for k, m in mods.items())}); skipped')
                continue
            name, img, text_end = mods[hit]
            taken = [(o, o + len(bytes.fromhex(ob))) for o, ob, nb, why in (registered or {}).get(hit, [])]
            n = 0
            for off, val in recs:
                o = off - NSO_HEADER
                if o < 0 or o + len(val) > len(img): log(f'[RED] mod {pf.name}: patch at {off:#x} is outside {name}; skipped'); continue
                if any(o < b and a < o + len(val) for a, b in taken): log(f'mod {pf.name}: patch at {name}+{o:#x} overlaps a cut the game profile makes; the profile\'s fix is kept'); continue
                old = bytes(img[o:o + len(val)])
                if old == val: continue
                out.setdefault(hit, []).append([o, old.hex(), val.hex(), f'mod {pf.parent.parent.name}/{pf.name}'])
                taken.append((o, o + len(val))); n += 1
            log(f'mod {pf.parent.parent.name}/{pf.name}: {n} patch(es) for {name} ({hit[:16]})')
    return out


def overlay_romfs(romfs, mod_dirs, dest, log=print):
    """romfs with each mod folder's files laid over it (later mods win), as hard links in dest; dest is reused when nothing changed"""
    import concurrent.futures as cf, shutil
    files = {}
    for dp, _, fns in os.walk(romfs):
        for f in fns:
            p = os.path.join(dp, f); files[os.path.relpath(p, romfs).replace(os.sep, '/').lower()] = (p, os.path.relpath(p, romfs).replace(os.sep, '/'))
    replaced = added = 0
    for md in mod_dirs:
        for dp, _, fns in os.walk(md):
            for f in fns:
                p = os.path.join(dp, f); rel = os.path.relpath(p, md).replace(os.sep, '/')
                if rel.lower() in files: replaced += 1; files[rel.lower()] = (p, files[rel.lower()][1])
                else: added += 1; files[rel.lower()] = (p, rel)
    sig = f'{len(files)} {replaced} {added} ' + ' '.join(f'{md}:{max((os.path.getmtime(os.path.join(dp, f)) for dp, _, fns in os.walk(md) for f in fns), default=0)}' for md in mod_dirs)
    dest = Path(dest); stamp = dest.with_name(dest.name + '.stamp')   # beside the folder, so it is no game file
    if stamp.is_file() and stamp.read_text(encoding='utf-8') == sig:
        log(f'mods: reusing the RomFS with {replaced} file(s) replaced and {added} added ({dest})'); return dest
    tmp = dest.with_name(dest.name + '.partial')
    if tmp.exists(): shutil.rmtree(tmp)
    for d in sorted({os.path.dirname(r) for _, r in files.values()}): (tmp / d).mkdir(parents=True, exist_ok=True)
    def one(item):
        src, rel = item
        try: os.link(src, tmp / rel)
        except OSError: shutil.copy2(src, tmp / rel)
    with cf.ThreadPoolExecutor(min(32, (os.cpu_count() or 4) * 2)) as ex: list(ex.map(one, files.values(), chunksize=256))
    if dest.exists(): shutil.rmtree(dest)
    os.replace(tmp, dest)
    stamp.write_text(sig, encoding='utf-8')
    log(f'mods: RomFS with {replaced} file(s) replaced and {added} added ({len(files):,} files, hard links)')
    return dest
