# The game's own GLSLC (NVIDIA's offline GLSL compiler, linked into a subsdk) run on the PC in the ARM64 emulator (win/arm64_emu.py), so the shaders a game compiles at run time
# are made at build time instead of being captured on a device (upstream boots the game in the Mac host with DM_GLSLC_CAPTURE, dm/host/hle_glslc.c). The outputs are the same bytes:
# the same compiler build, the same sources, the same options. A file is named as the host names a capture: <FNV-1a 64 of the output>.glslc
#
# The compile object, as the games fill it (Portal's video_nx.nro +0x3f74 and materialsystem.nro +0xb0068, after glslcInitialize):
#   +0x00  GLSLCresults * (the last results: {GLSLCcompilationStatus *, GLSLCoutput *}); the status has "success" at +0xc
#   +0x20  options bitfield (u64)
#   +0xa8  input: const char **sources, NVNshaderStage *stages (u32: 0 vertex, 1 fragment, 2 geometry, 3 tess control, 4 tess evaluation, 5 compute), u8 count
# Usage: glslc_emu.py <module dir (ExeFS)> <out dir> <spec.json>   spec: [{"sources": [text, ...], "stages": [0, 1], "options": null | int}, ...]
import json, os, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arm64_emu as E

OBJ_SIZE = 0x400


def _g_alloc(m): return m.malloc(max(m.x(0), 1), max(m.x(1), 16))
def _g_realloc(m):
    p, n = m.x(0), m.x(1); a = m.malloc(max(n, 1))
    if p and p in m.blocks: m.write(a, m.read(p, min(n, m.blocks[p])))
    return a
E.Machine.TRAPS.update({'glslc_alloc': _g_alloc, 'glslc_free': lambda m: None, 'glslc_realloc': _g_realloc})
OUT_MAGIC = 0x19866891


def glslc_module(exefs):
    """The subsdk that exports glslcCompile"""
    for n in sorted(os.listdir(exefs)):
        if not n.startswith('subsdk'): continue
        if b'glslcCompile' in Path(exefs, n).read_bytes() or True:
            m = E.Module(n, str(Path(exefs, n)), 0)
            if 'glslcCompile' in m.exports: return n
    return None


class Glslc:
    def __init__(self, exefs):
        name = glslc_module(exefs)
        if not name: raise E.EmuError(f'no module in {exefs} exports glslcCompile')
        mods = [(name, str(Path(exefs, name)))] + ([('sdk', str(Path(exefs, 'sdk')))] if Path(exefs, 'sdk').exists() else [])
        self.m = E.Machine(mods, heap_size=2 << 30)
        g = self.m.module(name)
        self.fn = {k: g.base + g.exports[k] for k in ('glslcInitialize', 'glslcCompile', 'glslcFinalize', 'glslcGetDefaultOptions', 'glslcSetAllocator') if k in g.exports}
        # glslcInitialize refuses to start before glslcSetAllocator (status 3): the games hand it their heap; here the emulator's (alloc(size, alignment, user), free(p, user),
        # realloc(p, size, user), each a trapped function)
        # One thread and no kernel: the SDK's mutexes, condition variables and events (which end in SVCs) become returns, and NVIDIA's own heap (NvOs, behind nn::os
        # mutexes) the emulator's allocator. Patched in place at the SDK's exported addresses, since the SDK calls them directly, not through imports
        self.stub_sdk()
        if 'glslcSetAllocator' in self.fn:
            m = self.m
            m.call(self.fn['glslcSetAllocator'], m.trap('glslc_alloc'), m.trap('glslc_free'), m.trap('glslc_realloc'), 0)

    def stub_sdk(self):
        m = self.m
        try: sdk = m.module('sdk')
        except StopIteration: return
        RET0 = struct.pack('<II', 0xd2800000, 0xd65f03c0)   # mov x0,#0 ; ret
        RET1 = struct.pack('<II', 0xd2800020, 0xd65f03c0)   # mov x0,#1 ; ret
        n = 0
        for name, off in sdk.exports.items():
            if not name.startswith('_ZN2nn2os'): continue
            if any(k in name for k in ('Mutex', 'ConditionVariable', 'CriticalSection', 'Semaphore', 'Event', 'Barrier', 'ReaderWriterLock', 'SdkMutex', 'SdkRecursiveMutex')):
                m.write(sdk.base + off, RET1 if 'TryLock' in name or 'TryAcquire' in name or 'TryWait' in name else RET0); n += 1
        for name, trap in (('NvOsAlloc', 'malloc'), ('NvOsFree', 'free'), ('NvOsRealloc', 'realloc')):
            if name in sdk.exports: self._jump(sdk.base + sdk.exports[name], m.trap(trap))
        self.stubbed = n

    def _jump(self, at, to):
        """Overwrite the function at `at` with a jump to `to` (ldr x16, #8 ; br x16 ; .quad to)"""
        self.m.write(at, struct.pack('<IIQ', 0x58000050, 0xd61f0200, to))

    def compile(self, sources, stages, options=None):
        m = self.m
        try:
            obj = m.malloc(OBJ_SIZE); m.write(obj, b'\0' * OBJ_SIZE)
            if not m.call(self.fn['glslcInitialize'], obj) & 0xff: raise E.EmuError('glslcInitialize failed')
            srcs = [m.malloc(len(s) + 1) for s in sources]
            for a, s in zip(srcs, sources): m.write(a, s.encode('latin1') + b'\0')
            sp = m.malloc(8 * len(srcs)); m.write(sp, b''.join(struct.pack('<Q', a) for a in srcs))
            st = m.malloc(4 * len(stages)); m.write(st, b''.join(struct.pack('<I', s) for s in stages))
            m.write(obj + 0xa8, struct.pack('<QQB', sp, st, len(srcs)))
            if options is not None: m.write(obj + 0x20, struct.pack('<Q', options))
            ok = m.call(self.fn['glslcCompile'], obj) & 0xff
            res = struct.unpack('<Q', m.read(obj, 8))[0]
            status, out = struct.unpack('<QQ', m.read(res, 16)) if res else (0, 0)
            if not ok or not out:
                info = ''
                if status:
                    log = struct.unpack('<Q', m.read(status, 8))[0]
                    if log: info = E._cstr(m, log).decode('latin1', 'replace')[:2000]
                raise E.EmuError(f'glslcCompile failed: {info}')
            n = struct.unpack('<I', m.read(out + 0x44, 4))[0]
            data = m.read(out, n)
            if struct.unpack('<I', data[:4])[0] != OUT_MAGIC: raise E.EmuError('unknown GLSLC output header')
            return data
        finally:
            m.call(self.fn['glslcFinalize'], obj)   # the heap is not reset: GLSLC keeps global state (NvOs objects made by the first glslcInitialize) on it

    def options_word(self):
        """The options bitfield glslcInitialize leaves (the defaults a game starts from)"""
        m = self.m; mark = m.heap_mark()
        try:
            obj = m.malloc(OBJ_SIZE); m.write(obj, b'\0' * OBJ_SIZE); m.call(self.fn['glslcInitialize'], obj)
            return struct.unpack('<Q', m.read(obj + 0x20, 8))[0]
        finally: m.heap_reset(mark)


def fnv(b):
    h = 0xcbf29ce484222325
    for x in b: h = ((h ^ x) * 0x100000001b3) & 0xffffffffffffffff
    return h


if __name__ == '__main__':
    exefs, out, spec = sys.argv[1:4]
    g = Glslc(exefs); os.makedirs(out, exist_ok=True)
    for p in json.loads(Path(spec).read_text(encoding='utf-8')):
        data = g.compile(p['sources'], p['stages'], p.get('options'))
        name = f'{fnv(data):016x}.glslc'; Path(out, name).write_bytes(data); print(name, len(data))
