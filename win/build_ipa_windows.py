#!/usr/bin/env python3
# NSP → IPA on Windows: runs the upstream pipeline (scripts/build_ipa_from_nsp.py) unchanged, with its macOS-only steps replaced:
#   check_prereqs        → the Windows toolchain (win/doctor.py)
#   build_nx_extract     → the same dotnet build, which on Windows writes nx_extract.exe
#   can_clone            → False (no APFS clones; nx_extract writes plain copies)
#   toolchain()          → the Windows Metal compiler's and spirv-cross's versions (shader cache keys)
#   build_ipa.sh         → win/build_app.py (through win/pyshim/sitecustomize.py, which also maps xcrun / dmsh_xlate / which)
#   Mac host steps       → refused with a clear message: games whose shaders exist only at run time (GLSLC / Vulkan / GL capture, Unreal and Oodle decoding)
#                          boot the game's own arm64 code in the Mac host, which no Windows PC can run
# Usage: python win/build_ipa_windows.py <NSP folder> -k <prod.keys> [the upstream script's other options]   (--platform mac / mac-app and --prepare-xcode are Mac-only)
import importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path

WIN = Path(__file__).resolve().parent
REPO = WIN.parent
SHIM = WIN / 'pyshim'


def main():
    if sys.platform == 'darwin': sys.exit('win/build_ipa_windows.py is the Windows and Linux driver: on a Mac run scripts/build_ipa_from_nsp.py')
    if os.name != 'nt': os.environ['NXW_LINUX'] = '1'   # Linux: the shim's mappings with native tools, and the Metal Developer Tools for Windows under Wine (win/toolchain.py cmd)
    for bad in ('--prepare-xcode',):
        if bad in sys.argv: sys.exit(f'{bad} needs a Mac with Xcode')
    for i, a in enumerate(sys.argv):
        if (a == '--platform' and i + 1 < len(sys.argv) and sys.argv[i + 1] != 'ios') or (a.startswith('--platform=') and a != '--platform=ios'):
            sys.exit('only --platform ios builds on Windows (the Mac platforms run the game in the Mac host)')
    # --split-data [DIR]: a small IPA with only the app, and the game files + shader libraries in a data folder copied into the app's Documents
    # (--split-data=DIR names the folder; default <IPA name>-data beside the IPA). Taken out here: the upstream argument parser does not know it; win/build_app.py reads NXW_SPLIT_DATA
    if '-h' in sys.argv or '--help' in sys.argv:
        print('Windows options:\n  --split-data[=DIR]  small IPA (app only) + a data folder (game files, shaders) to copy into the app\'s Documents\n  --no-split-data     one IPA with everything inside (default)\n')
    rest = []
    for a in sys.argv[1:]:
        if a == '--split-data': os.environ['NXW_SPLIT_DATA'] = '1'
        elif a.startswith('--split-data='): os.environ['NXW_SPLIT_DATA'] = str(Path(a.split('=', 1)[1]).resolve())
        elif a == '--no-split-data': os.environ['NXW_SPLIT_DATA'] = '0'
        elif a == '--entitlements': os.environ['NXW_ENTITLEMENTS'] = '1'   # an ad-hoc signature asking for Increased Memory Limit (win/macho_sign.py)
        elif a == '--no-entitlements': os.environ['NXW_ENTITLEMENTS'] = '0'   # an unsigned executable, as before
        else: rest.append(a)
    sys.argv[1:] = rest
    # every Python the pipeline starts loads the shim; this one too
    os.environ['PYTHONPATH'] = os.pathsep.join([str(SHIM)] + [p for p in os.environ.get('PYTHONPATH', '').split(os.pathsep) if p])
    os.environ.setdefault('PYTHONUTF8', '1')   # the pipeline reads and writes UTF-8 text without naming the encoding
    os.environ.setdefault('J', str(max(8, 2 * (os.cpu_count() or 4))))   # dmsh_build.py's workers (upstream 8): on Windows each shader compile is mostly metal.exe starting up, so twice the cores keep the CPU busy
    # Windows builds get their own bundle IDs (org.nxnativewindows.<title ID>), so they install beside a Mac-built IPA of the same game; --bundle-id still names any ID
    if not any(a == '--bundle-id' or a.startswith('--bundle-id=') for a in sys.argv):
        sys.path.insert(0, str(WIN)); import toolchain as _tc
        os.environ['NXW_BUNDLE_PREFIX'] = _tc.setting('bundle_prefix', 'org.nxnativewindows')
    # The shim in this process too. By its path: Debian and Ubuntu Pythons load their own sitecustomize (an apport hook) at startup, and an `import sitecustomize`
    # would then return that one, leaving this process's subprocesses unmapped (bash build_ipa.sh ran as it is). The child Pythons find the shim first on PYTHONPATH
    if Path(getattr(sys.modules.get('sitecustomize'), '__file__', '') or '').resolve() != (SHIM / 'sitecustomize.py').resolve():
        _spec = importlib.util.spec_from_file_location('nxw_shim', SHIM / 'sitecustomize.py'); _spec.loader.exec_module(importlib.util.module_from_spec(_spec))
    sys.path.insert(0, str(WIN)); import toolchain as tc, doctor

    spec = importlib.util.spec_from_file_location('build_ipa_from_nsp', REPO / 'scripts/build_ipa_from_nsp.py')
    up = importlib.util.module_from_spec(spec); sys.modules['build_ipa_from_nsp'] = up; spec.loader.exec_module(up)
    BuildError = up.BuildError

    extra = [str(p) for p in (tc.llvm_bin(),) if p] + [str(tc.tool_on_path(t).parent) for t in ('spirv-cross', 'zstd', 'glslangValidator') if tc.tool_on_path(t)]
    up.TOOL_PATHS = extra + ([str(Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'dotnet')] if tc.WINDOWS else up.TOOL_PATHS)   # upstream's list has ~/.dotnet
    # the shader chain takes spirv-cross from SPIRV_CROSS, else the repository's Mach-O build (dm/gfx/tools/dmsh_chain.py): here the native one the toolchain names
    sc = tc.tool_on_path('spirv-cross')
    if sc: os.environ.setdefault('SPIRV_CROSS', str(sc))
    if not tc.WINDOWS: os.environ['PATH'] = os.pathsep.join(up.TOOL_PATHS + [os.environ.get('PATH', '')])   # this process's own lookups too (the shim's dotnet, the doctor's checks)

    def check_prereqs(env, xlate, mac=False):
        if mac: raise BuildError('the Mac platforms need a Mac')
        bad = [r for r in doctor.checks() if r['required'] and not r['ok']]
        if bad: raise BuildError('missing on this PC: ' + '; '.join(f'{r["name"]} ({r["how"]})' for r in bad) + ' (python win/doctor.py lists them)')
        if not xlate.parent.is_dir(): raise BuildError(f'the shader translator is missing from the repository: {xlate}')
    up.check_prereqs = check_prereqs

    def build_nx_extract(repo, work, logs, env):
        import tempfile, shutil
        nx = work / 'tools/nx_extract/nx_extract'
        with tempfile.TemporaryDirectory(prefix='nx_extract_') as t:
            up.run(['dotnet', 'build', repo / 'dm/tools/nx_extract', '-c', 'Release', '-o', t, '-v', 'quiet', '-nologo'], logs / 'nx_extract_build.log', env=env)
            if not (Path(t) / 'nx_extract.exe').exists(): raise BuildError(f'nx_extract built without an executable (see {logs / "nx_extract_build.log"})')
            up.rmtree(nx.parent); shutil.copytree(t, nx.parent)
        return nx   # Windows starts nx_extract.exe for this path
    if tc.WINDOWS: up.build_nx_extract = build_nx_extract   # on Linux dotnet writes nx_extract, as upstream expects

    # address-region cuts for an sdk build sdk_patches.py does not register (win/sdk_auto_cuts.py), for a game with virtual address memory: written beside the rewrite, read by the
    # shim when patch_nso.py imports sdk_patches, and part of the rewrite's cache key (patch_files)
    import sdk_auto_cuts, json
    orig_rewrite, orig_patch_files = up.rewrite, up.patch_files
    def rewrite(py, repo, exe_dir, out, env, logs, g, provisional=False):
        sdk = exe_dir / 'sdk'
        jf = out.with_name(out.name + '.auto_sdk_cuts.json')
        if jf.exists(): jf.unlink()
        if sdk.is_file() and int(g.get('sys_resource', '0') or '0', 0):
            sys.path.insert(0, str(REPO / 'dm/tools'))
            import importlib; registered = importlib.import_module('sdk_patches').CUTS
            bid = up.build_id(sdk)
            if bid not in registered:
                _, cuts = sdk_auto_cuts.for_nso(sdk, log=up.say)
                if cuts:
                    jf.parent.mkdir(parents=True, exist_ok=True)
                    jf.write_text(json.dumps({bid: [list(c) for c in cuts]}, indent=1), encoding='utf-8')
                    up.say(f'sdk {bid[:12]} is not in dm/tools/sdk_patches.py: {len(cuts)} address-region cut(s) found in its code (win/sdk_auto_cuts.py)')
        if jf.exists(): os.environ['NXW_AUTO_SDK_CUTS'] = env['NXW_AUTO_SDK_CUTS'] = str(jf)
        else: os.environ.pop('NXW_AUTO_SDK_CUTS', None); env.pop('NXW_AUTO_SDK_CUTS', None)
        # Mods (win/mods.py): <game folder>/mods, in the emulators' layout. Code patches -> rewriter cuts of the build they name, added to that build's registered cuts by the shim
        # (NXW_MOD_CUTS: extend = builds a patch file registers, new = builds none does); RomFS folders -> the app build's RomFS (NXW_MODS_ROMFS)
        import mods
        mf = out.with_name(out.name + '.mod_cuts.json')
        if mf.exists(): mf.unlink()
        mdir = Path(os.environ.get('NXW_MODS_DIR') or exe_dir.parents[3] / 'mods')   # the window stages the game files elsewhere and names the mods folder beside the originals
        pfiles, rdirs = mods.find(mdir)
        if pfiles:
            sys.path.insert(0, str(REPO / 'dm/tools'))
            import importlib.util as ilu, glob
            registered = {}
            for pth in [REPO / 'dm/tools/sdk_patches.py'] + [Path(x) for x in sorted(glob.glob(str(REPO / 'dm/games/*/patches.py')))]:
                sp = ilu.spec_from_file_location(f'nxw_reg_{abs(hash(str(pth)))}', pth); mm = ilu.module_from_spec(sp)
                try: sp.loader.exec_module(mm)
                except Exception: continue
                for k, v in getattr(mm, 'CUTS', {}).items(): registered.setdefault(k, list(v))
            cuts = mods.cuts_for(pfiles, exe_dir, g.get('modules').split(), registered, log=up.say)
            if cuts:
                mf.parent.mkdir(parents=True, exist_ok=True)
                mf.write_text(json.dumps({'extend': {k: v for k, v in cuts.items() if k in registered}, 'new': {k: v for k, v in cuts.items() if k not in registered}}, indent=1), encoding='utf-8')
        if mf.exists(): os.environ['NXW_MOD_CUTS'] = env['NXW_MOD_CUTS'] = str(mf)
        else: os.environ.pop('NXW_MOD_CUTS', None); env.pop('NXW_MOD_CUTS', None)
        if rdirs:
            os.environ['NXW_MODS_ROMFS'] = env['NXW_MODS_ROMFS'] = os.pathsep.join(map(str, rdirs))
            up.say(f'mods: {len(rdirs)} RomFS folder(s) to lay over the game files: ' + ', '.join(str(d.relative_to(mdir)) for d in rdirs))
        else: os.environ.pop('NXW_MODS_ROMFS', None); env.pop('NXW_MODS_ROMFS', None)
        return orig_rewrite(py, repo, exe_dir, out, env, logs, g, provisional)
    up.rewrite = rewrite
    def patch_files(repo, exe_dir, mods, game_id=None):
        f = orig_patch_files(repo, exe_dir, mods, game_id)
        extra = [Path(j) for j in (os.environ.get('NXW_AUTO_SDK_CUTS'), os.environ.get('NXW_MOD_CUTS')) if j and Path(j).exists()]
        return f + extra
    up.patch_files = patch_files

    # The profile status line: upstream calls a version red when a registered build's fixes do not reach it. An sdk build that sdk_patches.py does not register gets its
    # address-region cuts here anyway (win/sdk_auto_cuts.py, NXW_AUTO_SDK_CUTS), so when the sdk cuts are all that differ the line is not red
    orig_report = up.report_profile_status
    def report_profile_status(g, reg, pkg_ver, derived, provisional, *rest, **kw):   # rest: upstream's artifact and patched
        j = os.environ.get('NXW_AUTO_SDK_CUTS'); auto = set()
        try: auto = set(json.loads(Path(j).read_text(encoding='utf-8'))) if j else set()
        except (OSError, ValueError): pass
        lines, say = [], up.say
        up.say = lambda m, *a, **k: lines.append((m, a, k))
        try: orig_report(g, reg, pkg_ver, derived, provisional, *rest, **kw)
        finally: up.say = say
        if derived and auto:
            row = g.builds().get(pkg_ver, {})
            known = {(m, b) for r in reg.builds().values() for m, b in r.items() if m != 'display'}
            other = [m for m, b in row.items() if m != 'display' and (m, b) not in known]
            repo = Path(__file__).resolve().parent.parent
            texts = [p.read_text(errors='replace') for p in [reg.dir / 'patches.py'] if p.is_file()]
            texts += [p.read_text(errors='replace') for d in ('dm/host', 'dm/gfx') for p in (repo / d).rglob('*') if p.suffix in ('.c', '.m', '.h', '.inc')]
            reg_ids = {b for r in reg.builds().values() for m, b in r.items() if m != 'display' and m in other}
            lost = [b for b in reg_ids if any(b[:16] in t for t in texts)]   # fixes keyed to the game's own builds or host code: these the auto cuts do not replace
            if other and not lost and row.get('sdk') in auto:
                lines = [(m.replace('[RED] ', '', 1) + ' (Windows: the sdk address-region cuts were found in this build\'s own code, win/sdk_auto_cuts.py)' if m.startswith('[RED] this') else m, a, k)
                         for m, a, k in lines]
        for m, a, k in lines: say(m, *a, **k)
    up.report_profile_status = report_profile_status

    up.can_clone = lambda d: False
    up.apple_silicon = lambda: True   # only the heap check asks now (the Mac platforms are refused above, the Mac host steps below): it runs heap_estimate instead

    def heap_estimate(repo, d, patched, work, env, logs, g):
        """The heap check without the Mac host. Upstream boots the game a few seconds to see its heap request and how much of the alias region it maps (profile_guess.py heap_signals).
        Here: a game with virtual address memory (an NPDM system resource) whose nninitStartup hands pool − used to StandardAllocator as one address region (Unity: Patrick's Parabox,
        Advance Wars 1+2, Megabyte Punch) gets a 2 GB pool in place of the hardware pool, the size Advance Wars runs with (a 1 GB pool starved its malloc; the 3.2 GB pool filled the
        alias region beside Unity's own regions). The profile is stamped as upstream's check stamps it, so later builds keep the result"""
        up.PROG.stage('heap estimate (no Mac host)')
        sig = {}
        if int(g.get('sys_resource', '0'), 0) and int(g.get('app_pool', '0'), 0) > 0x80000000:
            sig['app_pool'] = ('0x80000000', 'virtual address memory and no heap check on Windows: a 2 GB pool, so StandardAllocator\'s region (pool − used) leaves the alias region room for the game\'s own')
        for k, (v, why) in sig.items(): up.say(f'heap estimate: {k} {v}: {why}')
        if sig: g = up.set_keys(g, sig, 'Heap estimate on Windows (no Mac host)')
        p = g.dir / 'game.tsv'
        p.write_text(p.read_text(encoding='utf-8') + f'\n# heap check: {time.strftime("%Y-%m-%d")}, estimated on Windows without booting the game' + (f'; set {", ".join(sig)}' if sig else '') + '\n', encoding='utf-8')
        up.PROG.end('set ' + ', '.join(sig) if sig else 'guessed keys kept')
        return type(g)(g.dir)
    up.heap_check = heap_estimate

    def region_skip(repo, d, patched, work, env, logs, g):
        """The address region check without the Mac host. Upstream boots the game to report where its address regions reach against the profile's alias region: a report,
        it changes no key. Skipped here, and the profile stamped as upstream's check stamps it, so later builds do not ask again"""
        up.PROG.stage('address regions (no Mac host)')
        p = g.dir / 'game.tsv'
        p.write_text(p.read_text(encoding='utf-8') + f'\n# address regions: {time.strftime("%Y-%m-%d")}, not checked (no Mac host on this PC)\n', encoding='utf-8')
        up.PROG.end('skipped: it only reports, and needs the game booted in the Mac host')
        return type(g)(g.dir)
    up.region_check = region_skip   # newer upstream (after this fork's last sync): heap_check's apple_silicon gate lets it run
    xc = [sys.executable, str(WIN / 'xcrun.py')]
    up.toolchain = lambda repo=None, env=None: (('cmd', xc + ['-sdk', 'iphoneos', 'metal', '--version']), ('cmd', xc + ['-sdk', 'macosx', 'metal', '--version']),
                                                ('cmd', [os.environ.get('SPIRV_CROSS', 'spirv-cross'), '--revision']))

    # Run-time shader captures (GLSLC: Fire Emblem: Three Houses, Portal; Vulkan: Super Mario Galaxy; GL of a non-LÖVE game) are done on the device instead of a Mac. Upstream boots
    # the game in the Mac host with DM_*_CAPTURE and keeps what it compiles; the iPhone runs the same code natively. A first build packs a capture IPA (no shader libraries, the capture
    # switch in its dm/env.txt) and stops; after one run of it, the folder the app wrote in Documents, copied next to the game files, finishes the build. The profile's tables say
    # which files a complete capture holds
    CAP = {'glslc': ('glslc_capture', 'DM_GLSLC_CAPTURE', 'nvn'), 'vk': ('vk_capture', 'DM_VK_CAPTURE', 'vulkan'), 'gl': ('gl_capture', 'DM_GL_CAPTURE', 'gl')}

    def device_capture(kind, d, patched, work, env, g, want, done_fn):
        name, var, gfx = CAP[kind]
        up.PROG.stage(f'{name.replace("_", " ")} (from the device)')
        nsp = work.parent
        roots = [nsp] + ([nsp.parent] if nsp.name.endswith('_nxw') else [])
        cands = [r / n for r in roots for n in (name, f'{g.id}_capture/{name}', f'{g.id}_capture')]
        for c in cands:
            if not c.is_dir(): continue
            got = done_fn(c)
            if not got: continue
            if want and not got >= want:
                up.say(f'[RED] {c} holds {len(got & want)} of the {len(want)} shaders the profile names: run the capture IPA longer (until the title screen, then a minute) and copy the folder again')
                continue
            dst = d / name; up.rmtree(dst); shutil.copytree(c, dst)
            up.PROG.end(f'{len(got)} shaders from {c}')
            return dst
        # no capture yet: pack the capture IPA
        envf = work / 'tmp' / 'capture_env.txt'; envf.parent.mkdir(parents=True, exist_ok=True)
        envf.write_text(f'# shader capture (win/build_ipa_windows.py): the host saves every shader the game compiles at run time into Documents/{name}\n{var}={name}\n', encoding='utf-8')
        stem = (g.get('ipa') or f'{g.id}.ipa').rsplit('.', 1)[0]
        out = nsp / f'{stem}-capture.ipa'
        nacp = d / 'control.nacp'
        try: gname = subprocess.run([sys.executable, str(REPO / 'dm/tools/nacp.py'), str(nacp)], capture_output=True, text=True).stdout.strip()
        except OSError: gname = ''
        cenv = dict(env, GAME=g.id, W=str(work / 'ipa_capture'), PATCHED=str(patched), ROMFS=str(up.rfs.source(d)), AOC='', GFXAPI=gfx, DM_ENV_FILE=str(envf), NXW_CAPTURE_IPA='1',
                    DM_DISPLAY_NAME=f'{gname or stem} (capture)', DM_SHOW_FPS='NO')
        up.PROG.set(step='packing the capture IPA')
        up.run([sys.executable, str(WIN / 'build_app.py'), str(out)], logs_dir(work) / 'capture_ipa.log', env=cenv)
        up.PROG.end(ok=False)
        want_n = f'{len(want)} ' if want else ''
        sp = os.environ.get('NXW_SPLIT_DATA', '')
        data_step = (f', open it once, copy the folder {out.with_name(out.stem + "-data")} into its Documents (Apple Devices app › Files, or the Files app; '
                     f'the app shows the steps), reopen it') if sp and sp != '0' else ''
        raise BuildError(f'this game compiles {want_n}shaders only at run time; they are captured on your device, as upstream captures them on a Mac. 1) Install {out} '
                         f'(in LiveContainer){data_step} and play it until its title screen, then wait a minute (no picture is fine: it has no shaders yet). 2) In the Files app, copy '
                         f'"On My iPhone/iPad › {gname or stem} (capture) › {name}" to {nsp}. 3) Build again: the build finds the folder and makes the real IPA')

    def logs_dir(work): return work / 'logs'

    def capture_glslc(repo, dirs, pkg_ver, patched, work, env, logs, g):
        d = dirs[pkg_ver]
        want = up.glslc_wanted(g)
        if want and up.glslc_done(d / 'glslc_capture') >= want: up.say(f'reusing the captured run-time shaders: {d / "glslc_capture"}'); return
        device_capture('glslc', d, patched, work, env, g, want, up.glslc_done)
    up.capture_glslc = capture_glslc

    # The Mac host's decoder tool mode (Oodle / LZ5: shader_split.py, uepak.py, the Unreal step) runs in an emulated ARM64 machine: the "host" is a marker the shim starts as win/oodle_emu.py
    up.build_mac_host = lambda repo, out, env, logs, g: WIN / 'nxw_oodle_host'
    up.UE_DECODE_SECS = up.UE_DECODE_SECS * 20   # emulated, slower than the Mac's native run

    derive = up.derive_profile
    def derive_profile(g, pdir, ver, d, mods, *rest, **kw):   # rest: upstream's app and shader_only
        """upstream's derived profile, with a RomFS marker this version has: the profile's marker may be a file only its tested version ships (Balatro 1.1.3's NotoSansSC-Bold.ttf,
        absent from v0), and both the IPA build and the app's start (main.m romfs_locate) look for it. Then main.lua (LÖVE) or the largest RomFS file stands in"""
        disp = derive(g, pdir, ver, d, mods, *rest, **kw)
        tsv = pdir / 'game.tsv'; T = '\t'
        lines = tsv.read_text(encoding='utf-8').splitlines()
        old = next((l.split(T, 1)[1] for l in lines if l.startswith('romfs_marker' + T)), None)
        romfs = up.rfs.source(d)   # RomFS.img (upstream's extraction) or the RomFS folder, read alike
        if old and not (romfs / old).exists():
            files = [p for p in romfs.rglob('*') if p.is_file()]
            new = 'main.lua' if (romfs / 'main.lua').exists() else os.path.relpath(max(files, key=lambda p: p.stat().st_size), romfs).replace('\\', '/') if files else None
            if new:
                tsv.write_text('\n'.join(f'romfs_marker{T}{new}' if l.startswith('romfs_marker' + T) else l for l in lines) + '\n', encoding='utf-8')
                up.say(f'romfs_marker: {old} is not in {ver}\'s RomFS; the derived profile uses {new}')
        return disp
    up.derive_profile = derive_profile

    import love_shaders
    def capture_shaders(repo, d, patched, work, env, logs, g, api):
        """GL capture of a LÖVE game without the Mac host: win/love_shaders.py assembles the GLSL offline from the Lua LÖVE embeds in main (the same text the game hands to glShaderSource)"""
        if api != 'gl': return device_capture(api, d, patched, work, env, g, up.capture_wanted(g, api), lambda c: up.capture_done(c, api))
        out, part = d / 'gl_capture', d / 'gl_capture.partial'
        up.PROG.stage('GL shader reconstruction (LÖVE)')
        up.rmtree(part)
        try: table = g.table(up.CAPTURES['gl']['table'])
        except Exception: table = None
        r = love_shaders.generate(d / 'ExeFS/main', up.rfs.source(d), part, table, log=up.say)
        if r is None: return device_capture('gl', d, patched, work, env, g, up.capture_wanted(g, 'gl'), lambda c: up.capture_done(c, 'gl'))
        up.rmtree(out); part.rename(out)
        up.PROG.end(f'{len(r[0])} shaders')
        return out
    up.capture_shaders = capture_shaders

    sys.argv[0] = str(REPO / 'scripts/build_ipa_from_nsp.py')
    return up.cli(sys.argv[1:])   # the upstream entry point: argument parsing, error reporting and the exit code


if __name__ == '__main__':
    sys.exit(main())
