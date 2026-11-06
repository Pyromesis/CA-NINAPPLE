#!/usr/bin/env python3
# xcrun for Windows: the subset of `xcrun` the nxnative pipeline calls, mapped onto Windows tools (win/toolchain.py).
#   xcrun -sdk iphoneos|macosx metal [args]     Metal Developer Tools for Windows: metal.exe of the matching toolchain. Xcode's -mios-version-min=X becomes -target air64-apple-iosX
#                                               (the Windows compiler wants an explicit target); a macOS compile without a target gets air64-apple-macos<METAL_MACOS_TARGET>
#   xcrun -sdk ... metallib [args]              metallib.exe of the matching toolchain
#   xcrun -sdk iphoneos clang [args]            LLVM clang -target arm64-apple-ios<IOS_DEPLOYMENT> -isysroot <iPhoneOS SDK> (compile_check.py); -o /dev/null becomes NUL
#   xcrun [-sdk ...] --show-sdk-version | --show-sdk-build-version | --show-sdk-path
# Anything else exits 127 with a message naming the call, so a missing mapping is visible in the build log instead of a silent wrong result.
import os, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toolchain as tc


def metal_args(sdk, args):
    out, has_target = [], False
    for a in args:
        if a.startswith('-mios-version-min='):
            out += ['-target', f'air64-apple-ios{a.split("=", 1)[1]}']; has_target = True; continue
        if a.startswith('-mmacosx-version-min=') or a.startswith('-mmacos-version-min='):
            out += ['-target', f'air64-apple-macos{a.split("=", 1)[1]}']; has_target = True; continue
        if a in ('-target', '--target') or a.startswith('-target=') or a.startswith('--target='): has_target = True
        out.append(a)
    if not has_target and not any(a in ('--version', '-v', '--help') for a in args):
        tgt = f'air64-apple-ios{tc.setting("metal_ios_target", "18.0")}' if sdk.startswith('iphone') else f'air64-apple-macos{tc.setting("metal_macos_target", tc.METAL_MACOS_TARGET)}'
        out = ['-target', tgt] + out
    return out


def clang_args(args):
    sdk = tc.ios_sdk()
    if not sdk: die('no iPhoneOS SDK (set NXW_IOS_SDK or ios_sdk in win/toolchain.json; win/sdk/extract_xip.py extracts it from Xcode.xip)')
    fixed = ['NUL' if a == '/dev/null' and tc.WINDOWS else a for a in args]
    return ['-target', f'arm64-apple-ios{tc.setting("ios_deployment", tc.IOS_DEPLOYMENT)}', '-isysroot', str(sdk)] + fixed


def die(msg, code=127):
    print(f'xcrun (Windows port): {msg}', file=sys.stderr); sys.exit(code)


def sdk_info(sdk, what):
    if sdk.startswith('iphone'):
        p = tc.ios_sdk()
        if not p: die('no iPhoneOS SDK for ' + what)
        ver, build = tc.sdk_settings(p)
        return {'--show-sdk-path': str(p), '--show-sdk-version': ver, '--show-sdk-build-version': build}[what]
    # macosx: no SDK on Windows; the Metal tools' own folder name identifies the toolchain for the caches that key on it
    root = tc.metal_tools_root()
    return {'--show-sdk-path': str(root or ''), '--show-sdk-version': 'windows-metal-tools', '--show-sdk-build-version': root.name if root else 'missing'}[what]


def main(argv):
    sdk = 'macosx'
    a = list(argv)
    while a and a[0].startswith('-'):
        if a[0] in ('-sdk', '--sdk') and len(a) > 1: sdk = a[1]; a = a[2:]
        elif a[0] in ('--show-sdk-version', '--show-sdk-build-version', '--show-sdk-path'): print(sdk_info(sdk, a[0])); return 0
        elif a[0] in ('-r', '--run', '-f', '--find'):
            if a[0] in ('-f', '--find') and len(a) > 1:
                t = find(sdk, a[1]); print(t or ''); return 0 if t else 1
            a = a[1:]
        else: die('unsupported option ' + a[0])
    if not a: die('no tool named')
    tool, rest = a[0], a[1:]
    exe = find(sdk, tool)
    if not exe: die(f'no Windows tool for `xcrun -sdk {sdk} {tool}` (see win/README.md, Prerequisites)')
    if tool == 'metal': rest = metal_args(sdk, rest)
    elif tool == 'clang': rest = clang_args(rest)
    return subprocess.run(tc.cmd(exe) + rest).returncode   # the Metal tools through Wine off Windows


def find(sdk, tool):
    if tool in ('metal', 'metallib', 'metal-objdump', 'metal-ar') or tool.startswith('metal-'): return tc.metal_tool(sdk, tool)   # metal-tt: the offline pipeline archive (pso_offline.py)
    if tool in ('clang', 'clang++'): return tc.llvm_tool(tool)
    if tool in ('ld', 'ld64'): return tc.llvm_tool('ld64.lld')
    if tool in ('ar', 'libtool'): return tc.llvm_tool('llvm-ar')
    if tool in ('strip', 'nm', 'otool', 'lipo', 'objdump'):
        return tc.llvm_tool({'strip': 'llvm-strip', 'nm': 'llvm-nm', 'otool': 'llvm-otool', 'lipo': 'llvm-lipo', 'objdump': 'llvm-objdump'}[tool])
    return None


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
