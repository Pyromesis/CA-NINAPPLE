#!/usr/bin/env python3
# The Mac host's decoder tool mode (dm/host/hle_oodle.c) on Windows: the game's own Oodle / LZ5 decoder, run in an emulated ARM64 machine (win/arm64_emu.py), with the same two modes and
# the same wire formats, so shader_split.py, uepak.py and the NSP script's Unreal step use it as they use the Mac host:
#   DM_OODLE_SERVE=1          requests on stdin (u64 compressed length, u64 decompressed length, the bytes), answers on stdout (u64 bytes decoded, 0 on failure, then the bytes)
#   DM_OODLE_JOB=<job file>   "DMOJ", u32 count, per record u32 compressed length, u32 raw length, the bytes → <job file>.out: "DMOR", u32 count, per record u32 decoded length (0 = failed), the bytes
# The decoder is found as the host finds it: main's LZ5_decompress_safe export (DRAGON QUEST XI S), else the one function that takes the address of the string "OodleLZ_Decompress"
# (Octopath Traveler 0, Pokémon Legends: Z-A), else Oodle's streaming decoder between the two functions that reference "oodlelzcompressors.cpp" (Bayonetta 3).
# Usage (as the host): oodle_emu.py <rewritten modules folder> — the original modules are read from the extraction beside it (<work>/extract/<version>/ExeFS), or NXW_EXEFS
import os, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arm64_emu as E


def log(msg): print(f'[dm] {msg}', file=sys.stderr, flush=True)
def die(msg): log(msg); sys.exit(1)


def exefs_for(patched):
    if os.environ.get('NXW_EXEFS'): return Path(os.environ['NXW_EXEFS'])
    p = Path(patched).resolve()
    ver = p.name.removeprefix('patched_')
    for cand in (p.parent / 'extract' / ver / 'ExeFS', p.parent.parent / 'extract' / ver / 'ExeFS'):
        if (cand / 'main').is_file(): return cand
    die(f'oodle_emu: no extracted ExeFS for {p} (set NXW_EXEFS)')


def modules(exefs):
    names = ['main'] + sorted(n.name for n in exefs.iterdir() if n.name.startswith('subsdk') and n.is_file()) + ['sdk']
    return [(n, str(exefs / n)) for n in names if (exefs / n).is_file()]


# ---- finding the decoder in main (hle_oodle.c: eh_read, func_start, func_next, str_fns) ----
def eh_table(m):
    b = m.img; m0 = m.mod0; eh = struct.unpack_from('<i', b, m0 + 16)[0]; ehs = m0 + eh
    penc, cenc, tenc = b[ehs + 1], b[ehs + 2], b[ehs + 3]; o = [ehs + 4]
    def rd(enc):
        fmt, app, at = enc & 0xF, enc & 0x70, o[0]
        if fmt == 0x3: v = struct.unpack_from('<I', b, at)[0]; o[0] += 4
        elif fmt == 0xB: v = struct.unpack_from('<i', b, at)[0]; o[0] += 4
        elif fmt == 0x4: v = struct.unpack_from('<Q', b, at)[0]; o[0] += 8
        else: die(f'oodle_emu: .eh_frame_hdr encoding {enc:#x} not handled')
        return (v + at) if app == 0x10 else (v + ehs) if app == 0x30 else v
    rd(penc); n = rd(cenc); starts = []
    for _ in range(n): starts.append(rd(tenc) & 0xffffffffffffffff); rd(tenc)
    return sorted(starts)

def func_start(starts, off):
    best = 0
    for s in starts:
        if s <= off: best = s
        else: break
    return best

def func_next(starts, off, text_end):
    for s in starts:
        if s > off: return s
    return text_end

def str_fns(m, starts, needle, whole):
    b = m.img; ro, re_ = m.ro_off, m.data_off; nb = needle.encode()
    strs, p = [], ro
    while len(strs) < 16:
        p = b.find(nb, p, re_)
        if p < 0: break
        s = p
        while s > ro and b[s - 1]: s -= 1
        if not whole or (s == p and b[p + len(nb)] == 0): strs.append(s)
        p += len(nb)
    if not strs: return []
    want, fns = set(strs), []
    te = m.text_end
    words = memoryview(b)[:te - te % 4].cast('I')
    for i in range(len(words)):
        w = words[i]
        if (w & 0x9F000000) != 0x90000000: continue
        imm = ((w >> 29) & 3) | (((w >> 5) & 0x7FFFF) << 2)
        if imm & (1 << 20): imm -= 1 << 21
        page = ((i * 4) & ~0xFFF) + (imm << 12)
        for k in range(1, 8):
            if i + k >= len(words): break
            w2 = words[i + k]
            if (w2 & 0xFF800000) != 0x91000000 or ((w2 >> 5) & 31) != (w & 31): continue
            if page + ((w2 >> 10) & 0xFFF) in want:
                f = func_start(starts, (i + k) * 4)
                if f not in fns: fns.append(f)
            break
    return sorted(fns)


class Decoder:
    def __init__(self, patched):
        exefs = exefs_for(patched)
        self.m = E.Machine(modules(exefs))
        main = self.m.module('main'); base = main.base
        self.kind = None
        if 'LZ5_decompress_safe' in main.exports:
            self.kind, self.off = 'LZ5_decompress_safe', main.exports['LZ5_decompress_safe']
            for name in ('malloc', 'free', 'calloc', 'realloc'):   # LZ5 takes its work memory from the game's malloc, which nninitStartup would set up: the emulator's allocator instead
                for mod in self.m.mods:
                    if name in mod.exports: self.redirect(mod.base + mod.exports[name], name)
        else:
            starts = eh_table(main)
            fns = str_fns(main, starts, 'OodleLZ_Decompress', True)
            if len(fns) > 1: die(f'oodle_emu: {len(fns)} functions reference "OodleLZ_Decompress" in main (expected exactly 1)')
            if fns: self.kind, self.off = 'OodleLZ_Decompress', fns[0]
            else:
                src = str_fns(main, starts, 'oodlelzcompressors.cpp', False)
                leg = str_fns(main, starts, 'OODLE ERROR : OodleLZ_Decompress: asked to decode Legacy compressor', False)
                if len(src) != 2 or len(leg) != 1 or leg[0] != src[0]:
                    die(f'oodle_emu: main has no "OodleLZ_Decompress" name and no streaming decoder to find ({len(src)} functions reference oodlelzcompressors.cpp, {len(leg)} the legacy message)')
                create = func_next(starts, src[0], main.text_end); destroy = func_next(starts, create, main.text_end)
                if func_next(starts, destroy, main.text_end) != src[1]: die('oodle_emu: not two functions between the streaming decoder\'s ends')
                self.kind, self.off = 'OodleLZDecoder_DecodeSome', src[1]
                self.lzd = (base + src[0], base + create, base + destroy, base + src[1])
        self.fn = base + self.off
        self.scratch_n = 16 << 20; self.scratch = self.m.malloc(self.scratch_n)
        self.mark = self.m.heap_mark()

    def redirect(self, addr, name):   # the function at addr jumps to the emulator's trap for name: ldr x16, #8; br x16; .quad trap
        self.m.write(addr, struct.pack('<IIQ', 0x58000050, 0xD61F0200, self.m.trap(name)))

    def run(self, comp, rl):
        m = self.m; m.heap_reset(self.mark)
        c = m.malloc(len(comp) or 1); r = m.malloc(rl + 0x10000)
        if comp: m.write(c, comp)
        cl = len(comp)
        if self.kind == 'LZ5_decompress_safe':
            got = m.call(self.fn, c, r, cl, rl) if cl < 2 ** 31 and rl < 2 ** 31 else -1
            got = got - (1 << 64) if got >= 1 << 63 else got
        elif self.kind == 'OodleLZ_Decompress':
            got = m.call(self.fn, c, cl, r, rl, 1, 0, 0, 0, 0, 0, 0, self.scratch, self.scratch_n, 3)   # fuzz safe, no CRC check, silent, unthreaded
            got = got - (1 << 64) if got >= 1 << 63 else got
        else: got = self.lzd_run(c, comp, cl, r, rl)
        return m.read(r, rl) if got == rl else None

    def lzd_run(self, c, comp, cl, r, rl):
        size, create, destroy, some = self.lzd
        if cl < 2 or (comp[0] & 0x0F) != 0x0C: return -1
        compressor = {6: 8, 10: 9, 12: 13}.get(comp[1] & 0x7F)
        if compressor is None: return -1
        m = self.m
        need = m.call(size, compressor, rl) & 0xffffffff
        if need <= 0 or need >= 1 << 31: return -1
        mem = self.scratch if need + 64 <= self.scratch_n else m.malloc(need + 64)
        dec = m.call(create, compressor, rl, mem, need + 64)
        if not dec: return -1
        out = m.malloc(16); pos = cpos = 0
        while pos < rl:
            m.write(out, b'\0' * 16)
            ok = m.call(some, dec, out, r, pos, rl, rl - pos, c + cpos, cl - cpos, 1, 0, 0, 3) & 0xffffffff
            done, used = struct.unpack('<ii', m.read(out, 8))
            if not ok or (done <= 0 and used <= 0): break
            pos += done; cpos += used
        m.call(destroy, dec)
        return pos


def read_all(f, n):
    b = bytearray()
    while len(b) < n:
        k = f.read(n - len(b))
        if not k: return None
        b += k
    return bytes(b)


def serve(dec):
    i, o = sys.stdin.buffer, sys.stdout.buffer
    n = bad = 0
    log(f'DM_OODLE_SERVE: {dec.kind} at main+{dec.off:#x} (emulated ARM64, win/oodle_emu.py), requests on stdin')
    while True:
        h = read_all(i, 16)
        if h is None: break
        cl, rl = struct.unpack('<QQ', h)
        if cl > 1 << 32 or rl > 1 << 32: die(f'DM_OODLE_SERVE: request too large ({cl:#x} → {rl:#x})')
        comp = read_all(i, cl)
        if comp is None: die('DM_OODLE_SERVE: request cut short')
        try: out = dec.run(comp, rl)
        except E.EmuError as e: out = None; log(f'[RED] DM_OODLE_SERVE: request {n}: {e}')
        if out is None and rl:
            bad += 1
            if bad <= 8: log(f'[RED] DM_OODLE_SERVE: request {n} ({cl} → {rl} bytes) failed')
        o.write(struct.pack('<Q', len(out) if out else 0))
        if out: o.write(out)
        o.flush(); n += 1
    log(f'DM_OODLE_SERVE: {n} requests, {bad} failed')
    return 1 if bad else 0


def job(dec, path):
    log(f'DM_OODLE_JOB: {dec.kind} at main+{dec.off:#x} (emulated ARM64, win/oodle_emu.py)')
    with open(path, 'rb') as f, open(path + '.out', 'wb') as out:
        magic, n = struct.unpack('<II', f.read(8))
        if magic != 0x4a4f4d44: die(f'DM_OODLE_JOB: {path} is not a job file')
        out.write(struct.pack('<II', 0x524f4d44, n))
        bad = total = 0
        for k in range(n):
            cl, rl = struct.unpack('<II', f.read(8)); comp = f.read(cl)
            if len(comp) != cl: die(f'DM_OODLE_JOB: record {k} ends early')
            try: r = dec.run(comp, rl)
            except E.EmuError as e: r = None; log(f'[RED] DM_OODLE_JOB: record {k}: {e}')
            if r is None:
                bad += 1
                if bad <= 8: log(f'[RED] DM_OODLE_JOB: record {k} ({cl} → {rl} bytes) failed')
                out.write(struct.pack('<I', 0))
            else: out.write(struct.pack('<I', rl)); out.write(r); total += rl
            if k and k % 2000 == 0: log(f'DM_OODLE_JOB: {k} / {n} records')
    log(f'DM_OODLE_JOB: {n - bad} records decoded with the game\'s {dec.kind} ({bad} failed, {total / 1048576:.1f} MB out) → {path}.out')
    return 1 if bad else 0


def main():
    if len(sys.argv) < 2: die('usage: oodle_emu.py <rewritten modules folder>   (DM_OODLE_SERVE=1 or DM_OODLE_JOB=<file>)')
    if os.environ.get('DM_OODLE_JOB'): sys.exit(job(Decoder(sys.argv[1]), os.environ['DM_OODLE_JOB']))
    if os.environ.get('DM_OODLE_SERVE'): sys.exit(serve(Decoder(sys.argv[1])))
    die('oodle_emu: neither DM_OODLE_SERVE nor DM_OODLE_JOB is set: the emulator runs only the decoder tool mode (booting a game needs a Mac with Apple silicon)')


if __name__ == '__main__':
    main()
