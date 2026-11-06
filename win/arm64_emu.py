#!/usr/bin/env python3
# A small ARM64 machine (Unicorn) that loads a game's NSO modules and calls their functions, for the build steps upstream runs in the Mac host's tool mode, where the game's own
# arm64 code runs natively (a Windows PC cannot run it): its Oodle / LZ5 decoders (win/oodle_emu.py) and GLSLC (win/glslc_emu.py).
# Each module is decompressed, mapped at its own base with its bss, and relocated (RELATIVE, ABS64, GLOB_DAT, JUMP_SLOT). An import binds to another loaded module's export, or to a trap:
# the C library's memory and string functions and an allocator run in Python (traps), anything else stops the call with the import's name (nothing is guessed). A supervisor call stops it too.
# The machine has no kernel: only code that computes (decoders, compilers) can run here, which is all these steps need.
import struct
from pathlib import Path
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_MEM_INVALID, UC_PROT_ALL
from unicorn.arm64_const import *

PAGE = 0x1000
def up(n, a=PAGE): return (n + a - 1) & ~(a - 1)

STOP = 0xFFFF_0000          # return address of every call: emulation ends there
TRAP_BASE = 0xFFFE_0000     # one 4-byte slot (a ret) per trapped import
STACK_TOP, STACK_SIZE = 0x7F00_0000_0000, 32 << 20
HEAP_BASE = 0x6000_0000_0000
TLS_BASE = 0x5F00_0000_0000


class EmuError(RuntimeError): pass


def nso_load(path):
    """(image with bss, text end, ro offset, data offset): an NSO decompressed into its module layout"""
    import lz4.block
    d = Path(path).read_bytes()
    if d[:4] != b'NSO0': raise EmuError(f'{path}: not an NSO')
    flags = struct.unpack_from('<I', d, 0xc)[0]
    segs = [struct.unpack_from('<III', d, 0x10 + i * 0x10) for i in range(3)]
    csz = struct.unpack_from('<III', d, 0x60)
    bss = struct.unpack_from('<I', d, 0x3c)[0]
    img = bytearray(segs[2][1] + segs[2][2] + bss)
    for i, (fo, mo, sz) in enumerate(segs):
        raw = d[fo:fo + csz[i]]
        if flags >> i & 1: raw = lz4.block.decompress(raw, uncompressed_size=sz)
        img[mo:mo + sz] = raw
    return img, segs[0][1] + segs[0][2], segs[1][1], segs[2][1]


class Module:
    def __init__(self, name, path, base):
        self.name, self.base = name, base
        self.img, self.text_end, self.ro_off, self.data_off = nso_load(path)
        mod0 = struct.unpack_from('<I', self.img, 4)[0]
        if self.img[mod0:mod0 + 4] != b'MOD0': raise EmuError(f'{name}: no MOD0')
        self.mod0 = mod0
        dyn = mod0 + struct.unpack_from('<i', self.img, mod0 + 4)[0]
        self.tags = {}
        for i in range(4096):
            t, v = struct.unpack_from('<qQ', self.img, dyn + i * 16)
            if t == 0: break
            self.tags.setdefault(t, v)
        symtab, strtab = self.tags[6], self.tags[5]
        self.syms = []   # (name, value, shndx)
        for i in range((strtab - symtab) // 24):
            nm, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', self.img, symtab + i * 24)
            self.syms.append((self.img[strtab + nm:self.img.index(b'\0', strtab + nm)].decode('latin1'), value, shndx))
        self.exports = {n: v for n, v, s in self.syms if s and n}

    def relocs(self):
        out = []
        for tab, size in ((7, 8), (23, 2)):   # DT_RELA / DT_RELASZ, DT_JMPREL / DT_PLTRELSZ
            if tab not in self.tags or size not in self.tags: continue
            off, n = self.tags[tab], self.tags[size] // 24
            for i in range(n):
                r_off, info, add = struct.unpack_from('<QQq', self.img, off + i * 24)
                out.append((r_off, info & 0xffffffff, info >> 32, add))
        return out


def _cstr(m, a, limit=1 << 20):
    out = bytearray()
    while len(out) < limit:
        chunk = bytes(m.uc.mem_read(a + len(out), 256)); z = chunk.find(b'\0')
        if z >= 0: return bytes(out + chunk[:z])
        out += chunk
    return bytes(out)


class Machine:
    TRAPS = {}   # import name → handler(machine) returning x0 (filled below)

    def __init__(self, modules, heap_size=1 << 30):
        """modules: [(name, NSO path), ...] in load order (main first, as on Horizon)"""
        self.uc = uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        uc.reg_write(UC_ARM64_REG_CPACR_EL1, 0x300000)   # FP / SIMD on
        self.mods, base = [], 0x0800_0000
        for name, path in modules:
            m = Module(name, path, base); self.mods.append(m)
            uc.mem_map(base, up(len(m.img), 0x10000), UC_PROT_ALL)
            base = up(base + len(m.img) + 0x100000, 0x200000)
        self.traps, self.trap_names = {}, []
        uc.mem_map(TRAP_BASE, 0x10000, UC_PROT_ALL); uc.mem_map(STOP & ~0xffff, 0x10000, UC_PROT_ALL) if (STOP & ~0xffff) != TRAP_BASE else None
        uc.mem_write(TRAP_BASE, b'\xc0\x03\x5f\xd6' * (0x10000 // 4))   # ret
        exports = {}
        for m in self.mods:
            for n, v in m.exports.items(): exports.setdefault(n, m.base + v)
        for m in self.mods:
            for off, typ, si, add in m.relocs():
                if typ == 1027: val = m.base + add                                   # R_AARCH64_RELATIVE
                elif typ in (257, 1025, 1026):                                        # ABS64, GLOB_DAT, JUMP_SLOT
                    n, v, sh = m.syms[si]
                    if sh: val = m.base + v + (add if typ == 257 else 0)
                    elif n in self.TRAPS: val = self.trap(n)
                    elif n in exports: val = exports[n] + (add if typ == 257 else 0)
                    else: val = self.trap(n)                                           # unknown import: stops the call if it is ever reached
                elif typ == 0: continue
                else: raise EmuError(f'{m.name}: relocation type {typ} not handled')
                struct.pack_into('<Q', m.img, off, val & 0xffffffffffffffff)
            if 36 in m.tags and 35 in m.tags:   # DT_RELR / DT_RELRSZ: packed relative relocations (newer SDKs): an even word is an address, an odd word a bitmap of the 63 words after the last
                where = 0
                for k in range(m.tags[35] // 8):
                    e = struct.unpack_from('<Q', m.img, m.tags[36] + 8 * k)[0]
                    if not e & 1:
                        struct.pack_into('<Q', m.img, e, (struct.unpack_from('<Q', m.img, e)[0] + m.base) & 0xffffffffffffffff); where = e + 8
                    else:
                        for bit in range(1, 64):
                            if e >> bit & 1:
                                a = where + (bit - 1) * 8
                                struct.pack_into('<Q', m.img, a, (struct.unpack_from('<Q', m.img, a)[0] + m.base) & 0xffffffffffffffff)
                        where += 63 * 8
            uc.mem_write(m.base, bytes(m.img))
        uc.mem_map(STACK_TOP - STACK_SIZE, STACK_SIZE, UC_PROT_ALL)
        uc.mem_map(TLS_BASE, 0x10000, UC_PROT_ALL)
        uc.reg_write(UC_ARM64_REG_TPIDRRO_EL0, TLS_BASE); uc.reg_write(UC_ARM64_REG_TPIDR_EL0, TLS_BASE + 0x8000)
        self.heap_size = heap_size; uc.mem_map(HEAP_BASE, heap_size, UC_PROT_ALL)
        self.heap_top, self.blocks = HEAP_BASE, {}
        uc.hook_add(UC_HOOK_CODE, self._on_trap, begin=TRAP_BASE, end=TRAP_BASE + 0xffff)
        uc.hook_add(UC_HOOK_INTR, self._on_intr)
        self.fault = None

    # ---- memory ----
    def malloc(self, n, align=16):
        a = up(self.heap_top, max(align, 16))
        if a + n > HEAP_BASE + self.heap_size: raise EmuError(f'emulated heap full ({self.heap_size >> 20} MB)')
        self.heap_top = a + max(n, 1); self.blocks[a] = n
        return a
    def heap_mark(self): return self.heap_top
    def heap_reset(self, mark): self.heap_top = mark; self.blocks = {a: n for a, n in self.blocks.items() if a < mark}
    def write(self, a, b): self.uc.mem_write(a, bytes(b))
    def read(self, a, n): return bytes(self.uc.mem_read(a, n))

    def trap(self, name):
        if name not in self.traps:
            if len(self.trap_names) * 4 >= 0x10000 - 4: raise EmuError('too many trapped imports')
            self.traps[name] = TRAP_BASE + 4 * len(self.trap_names); self.trap_names.append(name)
        return self.traps[name]

    def module(self, name): return next(m for m in self.mods if m.name == name)

    # ---- calls ----
    def call(self, addr, *args, max_insns=0, timeout_us=0):
        """Call addr with integer / pointer arguments (AAPCS64: 8 in x0–x7, the rest on the stack, 8 bytes each); returns x0"""
        uc = self.uc
        sp = STACK_TOP - 0x1000
        extra = args[8:]
        sp -= up(8 * len(extra), 16)
        for i, v in enumerate(extra): uc.mem_write(sp + 8 * i, struct.pack('<Q', v & 0xffffffffffffffff))
        for i, v in enumerate(args[:8]): uc.reg_write(UC_ARM64_REG_X0 + i, v & 0xffffffffffffffff)
        uc.reg_write(UC_ARM64_REG_SP, sp); uc.reg_write(UC_ARM64_REG_LR, STOP); uc.reg_write(UC_ARM64_REG_X29, 0)
        self.fault = None
        try: uc.emu_start(addr, STOP, timeout=timeout_us, count=max_insns)
        except UcError as e:
            pc = uc.reg_read(UC_ARM64_REG_PC)
            raise EmuError(f'{e} at {self.where(pc)}' + (f' ({self.fault})' if self.fault else '')) from None
        if self.fault: raise EmuError(self.fault)
        return uc.reg_read(UC_ARM64_REG_X0)

    def where(self, pc):
        for m in self.mods:
            if m.base <= pc < m.base + len(m.img): return f'{m.name}+{pc - m.base:#x}'
        if TRAP_BASE <= pc < TRAP_BASE + 0x10000: return f'import {self.trap_names[(pc - TRAP_BASE) // 4]}'
        return f'{pc:#x}'

    def _on_intr(self, uc, intno, user):
        pc = uc.reg_read(UC_ARM64_REG_PC)
        self.fault = f'supervisor call / exception {intno} at {self.where(pc - 4)}: the emulator has no kernel'
        uc.emu_stop()

    def _on_trap(self, uc, addr, size, user):
        name = self.trap_names[(addr - TRAP_BASE) // 4] if (addr - TRAP_BASE) // 4 < len(self.trap_names) else None
        h = self.TRAPS.get(name)
        if not h:
            lr = uc.reg_read(UC_ARM64_REG_LR)
            self.fault = f'the code called import {name}, which the emulator does not provide (from {self.where(lr - 4)})'
            uc.emu_stop(); return
        r = h(self)
        if r is not None: uc.reg_write(UC_ARM64_REG_X0, r & 0xffffffffffffffff)   # then the slot's ret returns to the caller

    def x(self, i): return self.uc.reg_read(UC_ARM64_REG_X0 + i)


# ---- the C library and an allocator, in Python ----
def _memcpy(m):
    d, s, n = m.x(0), m.x(1), m.x(2)
    if n: m.uc.mem_write(d, bytes(m.uc.mem_read(s, n)))
    return d
def _memset(m):
    d, c, n = m.x(0), m.x(1) & 0xff, m.x(2)
    if n: m.uc.mem_write(d, bytes([c]) * n)
    return d
def _memcmp(m):
    a, b = m.read(m.x(0), m.x(2)), m.read(m.x(1), m.x(2))
    for x, y in zip(a, b):
        if x != y: return (x - y) & 0xffffffffffffffff
    return 0
def _strlen(m): return len(_cstr(m, m.x(0)))
def _strcmp(m):
    a, b = _cstr(m, m.x(0)), _cstr(m, m.x(1))
    return 0 if a == b else (1 if a > b else -1 & 0xffffffffffffffff)
def _strncmp(m):
    n = m.x(2); a, b = _cstr(m, m.x(0), n)[:n], _cstr(m, m.x(1), n)[:n]
    return 0 if a == b else (1 if a > b else -1 & 0xffffffffffffffff)
def _malloc(m): return m.malloc(m.x(0))
def _calloc(m):
    n = m.x(0) * m.x(1); a = m.malloc(n)
    if n: m.uc.mem_write(a, b'\0' * n)
    return a
def _aligned(m): return m.malloc(m.x(1), m.x(0))          # aligned_alloc / memalign(alignment, size)
def _posix_memalign(m):
    a = m.malloc(m.x(2), m.x(1)); m.uc.mem_write(m.x(0), struct.pack('<Q', a)); return 0
def _realloc(m):
    p, n = m.x(0), m.x(1); a = m.malloc(n)
    if p and p in m.blocks: m.uc.mem_write(a, bytes(m.uc.mem_read(p, min(n, m.blocks[p]))))
    return a
def _free(m): return None
def _abort(m): m.fault = 'the code called abort'; m.uc.emu_stop()

Machine.TRAPS.update({
    'memcpy': _memcpy, 'memmove': _memcpy, '__memcpy_chk': _memcpy, '__memmove_chk': _memcpy, 'memset': _memset, '__memset_chk': _memset,
    'memcmp': _memcmp, 'bcmp': _memcmp, 'strlen': _strlen, 'strcmp': _strcmp, 'strncmp': _strncmp,
    'malloc': _malloc, 'calloc': _calloc, 'realloc': _realloc, 'free': _free, 'aligned_alloc': _aligned, 'memalign': _aligned, 'posix_memalign': _posix_memalign,
    'abort': _abort,
})
