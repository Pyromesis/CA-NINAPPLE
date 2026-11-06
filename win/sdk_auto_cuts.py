#!/usr/bin/env python3
# The address-region cuts of dm/tools/sdk_patches.py, found in an sdk build that file does not register (a game without a repository profile), for games with virtual address memory.
# Upstream registers these cuts per sdk build ID (each found by hand: docs/reference/memory.md, "The SDK's address-region node area" and "1 GB alignment of regions of 1 GB and more").
# Without them a Unity game's nninitStartup breaks in StandardAllocator::Initialize (Megabyte Punch, SDK 8.3.1, on an iPad). This finds the same instructions from the code itself:
#   node area   in the function the dynamic symbol AddressRegionManager::AddressRegionManager (C1/C2) names: exactly two loads of #0x3fe00000 into w8 / w9 (mov or orr form), the node area
#               limit and the length registered as occupied → #0x3e00000 (62 MB), as every registered build
#   alignment   in the code that follows that constructor (to its module's next 16 KB): exactly one load of #0x40000000 into a register, preceded within six instructions by a load of
#               #0x2000000 and a right shift by 30 (the size class "1 GB and more"), as AllocateAddressRegion's placement on SDK 7.3.2 / 8.2.1 / 10.4.x → #0x2000000 (32 MB)
# Anything ambiguous (another count of matches, no symbol) gives no cut for that part, and the build log says so. Registered builds keep their reviewed CUTS.
# Usage: sdk_auto_cuts.py <sdk NSO> → prints the cuts found (offset, original word, new word, reason)
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'dm/tools'))

NODE_OLD = {'08fca752': 'mov w8,#0x3fe00000', '09fca752': 'mov w9,#0x3fe00000', 'e8230b32': 'orr w8,wzr,#0x3fe00000', 'e9230b32': 'orr w9,wzr,#0x3fe00000'}
NODE_NEW = {'w8': '087ca052', 'w9': '097ca052'}   # mov w8 / w9, #0x3e00000


def dyn_symbols(img):
    """{name: (offset, size)} of the defined dynamic symbols"""
    mod0 = struct.unpack_from('<I', img, 4)[0]
    dyn = mod0 + struct.unpack_from('<i', img, mod0 + 4)[0]
    tags = {}
    for i in range(4096):
        t, v = struct.unpack_from('<qQ', img, dyn + i * 16)
        if t == 0: break
        tags.setdefault(t, v)
    symtab, strtab = tags[6], tags[5]
    out = {}
    for i in range(1, (strtab - symtab) // 24):
        name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', img, symtab + i * 24)
        if shndx: out[img[strtab + name:img.index(b'\0', strtab + name)].decode('latin1')] = (value, size)
    return out


def find(img, text_end, log=print):
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    syms = dyn_symbols(img)
    ctor = next(((n, v) for n, v in syms.items() if 'AddressRegionManagerC2E' in n or 'AddressRegionManagerC1E' in n), None)
    if not ctor: log('sdk auto cuts: no AddressRegionManager constructor symbol: none'); return []
    name, (start, size) = ctor
    size = size or 0x200
    cuts = []
    hits = [o for o in range(start, start + size, 4) if img[o:o + 4].hex() in NODE_OLD]
    if len(hits) == 2:
        for o in hits:
            w = img[o:o + 4].hex(); reg = NODE_OLD[w].split()[1].split(',')[0]
            what = 'node area limit' if o == hits[0] else 'length of the node area registered as an occupied region'
            cuts.append((o, w, NODE_NEW[reg], f'AddressRegionManager constructor: {what} {NODE_OLD[w]} → mov {reg},#0x3e00000 (found by win/sdk_auto_cuts.py)'))
    else: log(f'sdk auto cuts: {len(hits)} loads of #0x3fe00000 in {name} (two expected): no node area cut')
    md = Cs(CS_ARCH_ARM64, CS_MODE_ARM); md.detail = False
    lo, hi = start, min(text_end, (start + 0x4000) & ~0x3fff if (start + 0x4000) & ~0x3fff > start + size else start + 0x4000)
    ins = list(md.disasm(img[lo:hi], lo))
    align = []
    for i, x in enumerate(ins):
        if x.mnemonic in ('mov', 'orr') and x.op_str.endswith('#0x40000000') and x.op_str.startswith('w'):
            back = ins[max(0, i - 6):i]
            if any(b.mnemonic == 'mov' and b.op_str.endswith('#0x2000000') for b in back) and any(b.mnemonic == 'lsr' and b.op_str.endswith('#0x1e') for b in back):
                align.append(x)
    if len(align) == 1:
        x = align[0]; reg = x.op_str.split(',')[0]
        new = struct.pack('<I', 0x52a00000 | (0x200 << 5) | int(reg[1:])).hex()   # movz wN, #0x200, lsl #16 = #0x2000000
        cuts.append((x.address, img[x.address:x.address + 4].hex(), new,
                     f'AllocateAddressRegion: alignment of regions of 1 GB and more {x.mnemonic} {x.op_str} → mov {reg},#0x2000000 (32 MB, as from 32 MB up; found by win/sdk_auto_cuts.py)'))
    else: log(f'sdk auto cuts: {len(align)} 1 GB alignment loads after {name} (one expected): no alignment cut')
    return cuts


def for_nso(path, log=print):
    import nso_syms
    d = Path(path).read_bytes()
    text_end = struct.unpack_from('<III', d, 0x10)[2]
    return d[0x40:0x50].hex(), find(nso_syms.load(path), text_end, log)


if __name__ == '__main__':
    bid, cuts = for_nso(sys.argv[1])
    print(bid)
    for c in cuts: print(f'{c[0]:#x}\t{c[1]}\t{c[2]}\t{c[3]}')
