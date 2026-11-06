#!/usr/bin/env python3
# Checks the Windows toolchain the nxnative Windows port needs and says how to get what is missing. Exit code 0 = everything a build needs is there.
# Usage: win/doctor.py [--json]
import importlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc


def run(cmd):
    try: r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e: return 1, str(e)
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip()


def checks():
    out = []
    def add(name, ok, detail, how='', required=True): out.append({'name': name, 'ok': bool(ok), 'detail': detail, 'how': how, 'required': required})

    if tc.WINDOWS: add('Windows', True, sys.platform)
    else: add('Linux with Wine (runs the Windows Metal compiler)', tc.wine(), tc.wine() or 'wine not found', 'install wine (apt install wine64), or set "wine" in win/toolchain.json')
    add('Python 3.10+', sys.version_info >= (3, 10), sys.version.split()[0], 'https://www.python.org/downloads/')
    for m, pip in (('lz4.block', 'lz4'), ('capstone', 'capstone'), ('fontTools', 'fonttools'), ('PIL', 'pillow')):
        try: importlib.import_module(m); ok = True
        except ImportError: ok = False
        add(f'python module {m}', ok, '', f'python -m pip install {pip}', required=m != 'PIL')
    zs = any(_spec_ok(m) for m in ('compression.zstd', 'backports.zstd'))
    add('python zstd (compression.zstd / backports.zstd)', zs, '', 'python -m pip install backports.zstd (Python before 3.14)')

    dn = tc.dotnet()
    rc, txt = run([dn, '--list-sdks']) if dn else (1, 'dotnet not found')
    add('.NET SDK 10', dn and any(l.startswith('10.') for l in txt.splitlines()), txt.splitlines()[-1] if txt else '', 'https://dotnet.microsoft.com/download/dotnet/10.0 (SDK, x64)')
    add('shader translator DLLs', tc.xlate_dll().exists(), str(tc.xlate_dll()), 'part of the repository (dm/gfx/tools/dmsh_xlate_bin)')

    clang = tc.llvm_tool('clang')
    rc, txt = run([clang, '--version']) if clang else (1, '')
    add('LLVM clang (20+)', clang and rc == 0, (txt.splitlines() or [''])[0], 'https://github.com/llvm/llvm-project/releases (LLVM-*-win64.exe), or set "llvm" in win/toolchain.json')
    lld = tc.llvm_tool('ld64.lld')
    add('ld64.lld (LLVM Mach-O linker)', lld, str(lld or ''), 'ships with LLVM for Windows (bin/ld64.lld.exe)')

    sdk = tc.ios_sdk()
    ver, build = tc.sdk_settings(sdk) if sdk else ('', '')
    add('iPhoneOS SDK 26+', sdk and ver.split('.')[0].isdigit() and int(ver.split('.')[0]) >= 26, f'{sdk} {ver} {build}' if sdk else 'not found',
        'python win/sdk/extract_xip.py <Xcode_26.xip> (Xcode from developer.apple.com/download, free Apple ID), or copy iPhoneOS.sdk from a Mac; then set "ios_sdk"')

    for sdkname in ('iphoneos', 'macosx'):
        m = tc.metal_tool(sdkname, 'metal'); ml = tc.metal_tool(sdkname, 'metallib')
        rc, txt = run(tc.cmd(m) + ['--version']) if m else (1, '')   # through Wine off Windows
        add(f'Metal compiler ({sdkname})', m and ml and rc == 0, (txt.splitlines() or [str(m or 'not found')])[0],
            'Metal Developer Tools for Windows: developer.apple.com/download/all/?q=metal%20developer%20tools%20for%20windows (Apple ID), or set "metal_tools"')

    for tool, how, req in (('spirv-cross', 'Vulkan SDK for Windows (vulkan.lunarg.com) or github.com/KhronosGroup/SPIRV-Cross releases; or set "spirv_cross_dir"', True),
                           ('zstd', 'github.com/facebook/zstd/releases (zstd-*-win64.zip); or set "zstd_dir"', True),
                           ('glslangValidator', 'Vulkan SDK for Windows; only OpenGL games need it', False)):
        p = tc.tool_on_path(tool)
        add(tool, p, str(p or 'not found'), how, required=req)
    f = tc.std_font()
    add('standard font (STD_FONT)', f, str(f or ''), 'any TTF with broad Unicode coverage; set STD_FONT or "std_font"')
    return out


def _spec_ok(m):
    try: return importlib.util.find_spec(m) is not None
    except (ImportError, ValueError): return False


def main():
    res = checks()
    if '--json' in sys.argv: print(json.dumps(res, indent=1)); return 0 if all(r['ok'] for r in res if r['required']) else 1
    for r in res:
        mark = 'ok ' if r['ok'] else ('MISSING' if r['required'] else 'missing (optional)')
        print(f'[{mark}] {r["name"]}: {r["detail"]}')
        if not r['ok'] and r['how']: print(f'         get it: {r["how"]}')
    bad = [r for r in res if r['required'] and not r['ok']]
    print(f'\n{len(bad)} required item(s) missing' if bad else '\neverything a build needs is there')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
