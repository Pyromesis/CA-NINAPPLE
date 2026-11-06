#!/usr/bin/env python3
# The translation chain's tool lock (dm/gfx/tools/dmsh_chain.lock) on a Windows PC: tool_lock.py --update-lock would
# record this machine's Metal compiler (metalfe-custom-windows), and the lock names the macOS one the shaders were tested
# with. This rewrites only what differs on Windows (the translator's DLLs and its embedded source digest, spirv-cross)
# and keeps the metal_* lines; the build accepts the Windows Metal compiler with --allow-other-metal.
# Run it after rebuilding dmsh_xlate, then dm/gfx/tools/dmsh_chain.py --header, and commit the lock, the header and the DLLs.
# Usage: python win/update_tools_lock.py
import hashlib, os, subprocess, sys
from pathlib import Path

WIN = Path(__file__).resolve().parent; REPO = WIN.parent
sys.path.insert(0, str(REPO / 'dm/gfx/tools')); sys.path.insert(0, str(WIN))
import dmsh_chain, toolchain

LOCK = Path(dmsh_chain.LOCK); BIN = Path(dmsh_chain.XLATE_DIR)
HEAD = '# Translation chain tool fingerprints (written by tool_lock.py --update-lock; regenerate after changing tools and commit it)'

def sha16(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]

def tools_now():
    t = {d: sha16(BIN / d) for d in ('dmsh_xlate.dll', 'Ryujinx.Graphics.Shader.dll', 'Ryujinx.Common.dll')}
    r = subprocess.run([os.environ.get('DOTNET', 'dotnet'), str(BIN / 'dmsh_xlate.dll'), '--source-sha'], capture_output=True, text=True, errors='replace')
    t['xlate_source'] = r.stdout.strip() if r.returncode == 0 else 'does not run (%s)' % ((r.stderr.strip().splitlines() or ['exit code %d' % r.returncode])[0])
    # the same one the build driver hands dmsh_build.py, not the in-repo Mach-O build (that is the macOS one)
    sc = toolchain.tool_on_path('spirv-cross') or (Path(os.environ['SPIRV_CROSS']) if os.environ.get('SPIRV_CROSS') else None)
    if not sc: sys.exit('[RED] spirv-cross not found: put it on PATH or set SPIRV_CROSS (win/toolchain.json also names its folder)')
    if not sc.exists(): sys.exit(f'[RED] spirv-cross not found at {sc}')
    t['spirv-cross'] = sha16(sc)
    return t, sc

def main():
    now, sc = tools_now()
    if now['xlate_source'] != dmsh_chain.xlate_source_sha():
        sys.exit(f'[RED] the translator was not built from the in-repo source (embedded {now["xlate_source"]} / in repo {dmsh_chain.xlate_source_sha()}): rebuild dmsh_xlate first (dotnet publish, see docs)')
    metal = [l for l in LOCK.read_text(encoding='utf-8').splitlines() if l.startswith('metal_')]
    if len(metal) != 2: sys.exit(f'[RED] {LOCK} has no metal_macosx / metal_iphoneos lines: restore it from git before updating it here')
    LOCK.write_text('\n'.join([HEAD] + [f'{k}\t{v}' for k, v in now.items()] + metal) + '\n', encoding='utf-8')
    for k, v in now.items(): print(f'{k}\t{v}')
    print('spirv-cross from', sc)
    print('wrote', LOCK)

if __name__ == '__main__':
    main()
