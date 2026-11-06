#!/usr/bin/env python3
# Windows replacement for the GL shader capture of LÖVE games (Balatro): upstream boots the game in the Mac host with DM_GL_CAPTURE and saves every GLSL source the game
# hands to glShaderSource (<key>.vert / <key>.frag, key = sha256(GLSL)[:16], dm/gfx/gl/hle_gl.m). LÖVE builds those sources with plain string concatenation in Lua
# (love.graphics._shaderCodeToGLSL in wrap_GraphicsShader.lua, which love-nx embeds in main as text), so this file reads that Lua out of the game's own main, takes its GLSL
# blocks, and assembles the same sources offline:
#   LÖVE's default shaders (standard vertex + pixel, video, array image), for every target the game could pick
#   one shader per resources/shaders/*.fs file (Balatro's game.lua: love.graphics.newShader("resources/shaders/" .. file) for each .fs), vertex and pixel from the same code
# Every candidate is written; with a capture table (the profile's gl_capture.tsv) it reports which listed keys it made, so a match proves the reconstruction byte for byte.
# Usage: love_shaders.py <ExeFS main (NSO)> <RomFS> <out folder> [gl_capture.tsv]
import hashlib, re, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'dm/tools'))
import romfs as rfs   # the RomFS as a folder or as one RomFS image (nx_extract --romfs-image), read alike


def nso_image(path):
    import lz4.block
    d = Path(path).read_bytes()
    flags = struct.unpack_from('<I', d, 0xc)[0]
    segs = [struct.unpack_from('<III', d, 0x10 + i * 0x10) for i in range(3)]
    csz = struct.unpack_from('<III', d, 0x60)
    img = bytearray(segs[2][1] + segs[2][2])
    for i, (fo, mo, sz) in enumerate(segs):
        raw = d[fo:fo + csz[i]]
        if flags >> i & 1: raw = lz4.block.decompress(raw, uncompressed_size=sz)
        img[mo:mo + sz] = raw
    return bytes(img)


def love_shader_lua(img):
    """the text of LÖVE's wrap_GraphicsShader.lua embedded in main (the C string holding love.graphics._shaderCodeToGLSL)"""
    i = img.find(b'function love.graphics._shaderCodeToGLSL')
    if i < 0: return None
    s, e = img.rfind(b'\0', 0, i) + 1, img.find(b'\0', i)
    return img[s:e].decode('utf-8')


LONG = re.compile(r'(\w+)\s*=\s*\[(=*)\[\n?(.*?)\]\2\]', re.S)   # Lua long string: a newline right after the opening bracket is not part of it


def blocks(lua):
    """{'SYNTAX': ..., 'VERTEX.HEADER': ..., 'defaultcode.pixel': ..., 'VERSION': {...}}: the GLSL text blocks, keyed by their table"""
    lua = lua.replace('\r\n', '\n')
    out = {}
    for m in re.finditer(r'^GLSL\.(\w+)\s*=\s*\[(=*)\[\n?(.*?)\]\2\]', lua, re.S | re.M): out[m.group(1)] = m.group(3)
    for m in re.finditer(r'^(?:GLSL\.(\w+)|local (defaultcode))\s*=\s*\{', lua, re.M):
        name, pos = m.group(1) or m.group(2), m.end()
        if name == 'VERSION':
            body = lua[pos:lua.index('\n}', pos)]
            out['VERSION'] = {t: {False: n, True: es} for t, n, es in re.findall(r'(\w+)\s*=\s*\{\s*\[false\]\s*=\s*"([^"]*)"\s*,\s*\[true\]\s*=\s*"([^"]*)"', body)}
            continue
        while True:   # the table's entries one by one: its long strings may hold lines starting with "}"
            ws = re.compile(r'(?:\s|,|--[^\n]*)*').match(lua, pos); pos = ws.end()
            if lua.startswith('}', pos): break
            e = LONG.match(lua, pos)
            if not e: raise ValueError(f'unexpected Lua in table {name} at {lua[pos:pos + 40]!r}')
            out[f'{name}.{e.group(1)}'] = e.group(3); pos = e.end()
    return out


class Love:
    def __init__(self, lua):
        self.b = blocks(lua)
        for need in ('VERSION', 'SYNTAX', 'UNIFORMS', 'FUNCTIONS', 'VERTEX.HEADER', 'VERTEX.MAIN', 'PIXEL.HEADER', 'PIXEL.MAIN'):
            if need not in self.b: raise ValueError(f'LÖVE shader Lua without {need}: another LÖVE version?')

    def stage(self, stage, code, lang, gles, glsl1on3, gammacorrect, custom=False, multicanvas=False):   # createShaderStageCode
        b = self.b
        lines = [b['VERSION'][lang][gles], f'#define {stage} {stage}', '#define LOVE_GLSL1_ON_GLSL3 1' if glsl1on3 else '',
                 '#define LOVE_GAMMA_CORRECT 1' if gammacorrect else '', '#define LOVE_MULTI_CANVAS 1' if multicanvas else '',
                 b['SYNTAX'], b[f'{stage}.HEADER'], b['UNIFORMS'], b['FUNCTIONS'], b.get(f'{stage}.FUNCTIONS'),
                 b.get(f'{stage}.MAIN_CUSTOM') if custom else b[f'{stage}.MAIN'],
                 '#line 0' if ((lang == 'glsl1' or glsl1on3) and not gles) else '#line 1', code]
        return '\n'.join('' if l is None else l for l in lines)   # table.concat of a table whose nil entries end it early would differ; LÖVE 11.4 has every entry

    @staticmethod
    def target(code):
        m = re.match(r'\s*#pragma language (\w+)', code)
        return m.group(1) if m else 'glsl1'

    def to_glsl(self, gles, code, glsl3=True, gammacorrect=False):   # _shaderCodeToGLSL(gles, code) for one file holding both stages
        vert = code if re.search(r'vec4\s+position\s*\(', code) else None
        pix, custom, multi = None, False, False
        if re.search(r'vec4\s+effect\s*\(', code): pix = code
        elif re.search(r'void\s+effect\s*\(', code): pix, custom, multi = code, True, 'love_Canvases' in code
        lang, on3 = self.target(code), False
        if lang == 'glsl1' and glsl3: lang, on3 = 'glsl3', True
        return (self.stage('VERTEX', vert, lang, gles, on3, gammacorrect) if vert else None,
                self.stage('PIXEL', pix, lang, gles, on3, gammacorrect, custom, multi) if pix else None)

    def defaults(self, target, gles, gammacorrect):
        d = {k.split('.', 1)[1]: v for k, v in self.b.items() if k.startswith('defaultcode.')}
        return [('vert', self.stage('VERTEX', d['vertex'], target, gles, False, gammacorrect)),
                ('frag', self.stage('PIXEL', d['pixel'], target, gles, False, gammacorrect)),
                ('frag', self.stage('PIXEL', d['videopixel'], target, gles, False, gammacorrect, True)),
                ('frag', self.stage('PIXEL', d['arraypixel'], target, gles, False, gammacorrect, True))]


def key(src): return hashlib.sha256(src.encode('utf-8', 'surrogateescape')).hexdigest()[:16]


def generate(main, romfs, out, table=None, log=print):
    lua = love_shader_lua(nso_image(main))
    if not lua: return None   # not a LÖVE game
    love = Love(lua)
    want = None
    if table and Path(table).exists():
        want = {l.strip() for l in Path(table).read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')}
    # the desktop GL core profile love-nx runs on: GLSL 3 (#version 330 core), not ES. Gamma correction: what the table's default shaders show, else the game's conf.lua (t.gammacorrect)
    conf = rfs.Path(romfs) / 'conf.lua'
    gc = bool(conf.exists() and re.search(r'\bgammacorrect\s*=\s*true', conf.read_text(encoding='utf-8', errors='replace')))
    if want:
        for g in (False, True):
            if all(f'{key(s)}.{e}' in want for e, s in love.defaults('glsl3', False, g)): gc = g
    cands = [(ext, s, 'LÖVE default') for ext, s in love.defaults('glsl3', False, gc)]
    for fs in sorted((rfs.Path(romfs) / 'resources/shaders').glob('*.fs')):
        code = fs.read_bytes().decode('utf-8', 'surrogateescape')   # bytes as they are: LÖVE hands the file's CRLF line ends to GL, and read_text would turn them into LF
        v, p = love.to_glsl(False, code, True, gc)
        if v: cands.append(('vert', v, fs.name))
        if p: cands.append(('frag', p, fs.name))
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    made = {}
    for ext, src, what in cands:
        name = f'{key(src)}.{ext}'
        made[name] = what
        (out / name).write_bytes(src.encode('utf-8', 'surrogateescape'))
    log(f'love_shaders: {len(made)} sources (gamma correction {"on" if gc else "off"})')
    if want is not None:
        hit = want & set(made)
        log(f'love_shaders: {len(hit)} of the {len(want)} sources the capture table lists are among them' +
            (' (every one, byte for byte)' if hit == want else f'; {len(made) - len(hit)} differ, as a game version other than the table\'s changes its shader files'
             if len(made) == len(want) else '; the counts differ too: check the reconstruction'))
    return made, want


if __name__ == '__main__':
    if len(sys.argv) < 4: sys.exit('usage: love_shaders.py <ExeFS main> <RomFS> <out> [gl_capture.tsv]')
    r = generate(*sys.argv[1:5])
    if r is None: sys.exit('not a LÖVE game (no love.graphics._shaderCodeToGLSL in main)')
    made, want = r
    sys.exit(0 if want is None or len(made) == len(want) else 1)
