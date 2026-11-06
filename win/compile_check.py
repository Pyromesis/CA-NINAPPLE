#!/usr/bin/env python3
# Compile every source of the iOS app (host, graphics, libvpx, the iOS front end and win/ios/Launcher.m) for one game profile, without its game files: the Windows
# counterpart of dm/ios/tools/compile_check.py. Checks that LLVM and the iPhoneOS SDK build the app; Gen/embed.S (the game's rewritten modules) is left out.
# Usage: win/compile_check.py [game id (default 010015100B514000)] [work folder]
import sys, tempfile
from pathlib import Path
WIN = Path(__file__).resolve().parent
sys.path.insert(0, str(WIN))
import toolchain as tc, build_app as ba

game = sys.argv[1] if len(sys.argv) > 1 else '010015100B514000'
work = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.gettempdir()) / 'nxw_compile_check'
sdk = tc.ios_sdk() or ba.die('no iPhoneOS SDK'); clang = tc.llvm_tool('clang') or ba.die('no clang')
(work / 'profile').mkdir(parents=True, exist_ok=True)
ba.py(ba.DM / 'games/game.py', 'header', game, work / 'profile/game_profile.h')
files, incs = ba.host_sources(work / 'profile')
files += [p.resolve() for p in sorted((ba.IOS / 'Sources').glob('*.m'))] + [(WIN / 'ios/Launcher.m').resolve(), (WIN / 'ios/DataHelp.m').resolve(), (WIN / 'ios/nxw_unzip.c').resolve()]
objs = ba.compile_all(clang, sdk, files, incs, work / 'obj', [])
print(f'compile_check: {len(objs)} files compiled for {game} ({sdk.name} {" ".join(tc.sdk_settings(sdk))})')
