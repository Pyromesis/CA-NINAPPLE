# Building on Linux

These steps build an nxnative IPA on a Linux PC, with no Mac and no Windows. They were used on Pop!_OS (Ubuntu 24.04 base) to build Pokémon Legends: Arceus 1.0.2, which has no upstream profile and played in game on an iPhone 16 at about 30 fps.

The Linux build runs the Windows port's driver, `win/build_ipa_windows.py`. Everything is a native Linux program except Apple's Metal compiler, which Apple ships only for macOS and Windows. Here it runs under Wine.

## What you need

- An x86-64 Linux PC with Wine (tested with Wine 9.0 from Ubuntu's packages), 7-Zip (`p7zip-full`), git, a C++ compiler and zstd.
- Python 3.12 or later.
- About 14 GB of disk for the tools (LLVM alone unpacks to 12 GB). Each game needs about twice the size of its files plus 10 GB; Arceus's work folder came to 12 GB.
- A free Apple ID, for two downloads from [developer.apple.com/download](https://developer.apple.com/download/all/): Metal Developer Tools for Windows (6.2 tested) and Xcode 27.1 (`Xcode_27.1.xip`, of which the build uses only the iPhoneOS SDK). Apple's Xcode and Apple SDKs Agreement covers these files. Read it before you use them on non-Apple hardware.
- An iPhone or iPad on iOS / iPadOS 26 or later. Upstream needs an A17 Pro or newer iPhone, or an M1 or newer iPad, for the games' BC textures; the Windows port also decodes them on the CPU for older chips (tested on an A16 iPad). Arceus was tested on an iPhone 16.
- Your own game dump (NSP or XCI, with its update) and your own `prod.keys`.

The commands keep the tools in `$TOOLS`. Set it to a folder on a drive with room:

```sh
TOOLS=/path/to/nxtools
mkdir -p "$TOOLS"
```

## One-time setup

### 1. Python modules

A venv keeps them out of the system Python:

```sh
python3 -m venv ~/.local/venvs/nxnative
~/.local/venvs/nxnative/bin/pip install lz4 capstone fonttools backports.zstd unicorn pillow cmake
```

`backports.zstd` is only needed before Python 3.14. `unicorn` runs a game's own Oodle decoder (Arceus needs it), and `cmake` builds spirv-cross in step 4.

### 2. .NET SDK 10

```sh
curl -sSLo dotnet-install.sh https://dot.net/v1/dotnet-install.sh
bash dotnet-install.sh --channel 10.0
```

This installs to `~/.dotnet`, where the build looks for it.

### 3. LLVM 20 or later

Ubuntu 24.04 ships LLVM 18, which is too old. The LLVM project's Linux release works (23.1.4 tested):

```sh
mkdir -p "$TOOLS/llvm-23.1.4"
curl -L https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.4/LLVM-23.1.4-Linux-X64.tar.xz | tar -xJ -C "$TOOLS/llvm-23.1.4" --strip-components=1
```

It has `clang` and `ld64.lld` but no Darwin compiler runtime. [`ios/compat_rt.c`](ios/compat_rt.c) stands in for it, as on Windows.

### 4. spirv-cross

The repository's `dm/gfx/tools/spirv_cross_bin/spirv-cross` is a Mac build. Build the same pinned version for Linux:

```sh
git clone --depth 1 --branch vulkan-sdk-1.4.363.0 https://github.com/KhronosGroup/SPIRV-Cross.git "$TOOLS/spirv-cross-src"
CMAKE=~/.local/venvs/nxnative/bin/cmake
$CMAKE -S "$TOOLS/spirv-cross-src" -B "$TOOLS/spirv-cross-build" -DCMAKE_BUILD_TYPE=Release -DSPIRV_CROSS_ENABLE_TESTS=OFF -DSPIRV_CROSS_SKIP_INSTALL=ON
$CMAKE --build "$TOOLS/spirv-cross-build" --target spirv-cross -j"$(nproc)"
mkdir -p "$TOOLS/bin" && cp "$TOOLS/spirv-cross-build/spirv-cross" "$TOOLS/bin/"
```

### 5. Metal Developer Tools for Windows

You don't need to run the installer, because 7-Zip unpacks it:

```sh
7z x -o"$TOOLS/metal-tools" Metal_Developer_Tools6.2Windows.exe
```

The compiler is then `$TOOLS/metal-tools/bin/metal.exe`. Give it a Wine prefix of its own (step 7 names it), so its module cache stays apart from your other Wine programs. To try it:

```sh
WINEPREFIX=~/.local/share/wineprefixes/metal wine "$TOOLS/metal-tools/bin/metal.exe" --version
```

During a build, `metal.exe` prints lines like `Rename failed: ... invalid argument` under Wine. You can ignore them: the compiler falls back to another way of writing the file, and its output lands anyway.

### 6. The iPhoneOS SDK

From the repository folder:

```sh
~/.local/venvs/nxnative/bin/python win/sdk/extract_xip.py Xcode_27.1.xip "$TOOLS/sdk"
```

After a few minutes the SDK is in `$TOOLS/sdk/iPhoneOS.sdk`.

### 7. `win/toolchain.json`

Git ignores this file. Write your paths into it as absolute paths (only `wineprefix` expands `~`):

```json
{
  "llvm": "/path/to/nxtools/llvm-23.1.4",
  "metal_tools": "/path/to/nxtools/metal-tools",
  "wineprefix": "~/.local/share/wineprefixes/metal",
  "ios_sdk": "/path/to/nxtools/sdk/iPhoneOS.sdk",
  "spirv_cross_dir": "/path/to/nxtools/bin"
}
```

### 8. Check the toolchain

```sh
~/.local/venvs/nxnative/bin/python win/doctor.py
```

Every required line should say `ok`. The two Metal compiler lines run `metal.exe --version` through Wine. glslangValidator is optional, since only OpenGL games need it.

## The shader chain lock

`dmsh_build.py` stops when the shader tools differ from `dm/gfx/tools/dmsh_chain.lock`. The committed lock records the Windows tools. Under Wine, the Metal compiler prints the same version (Apple metal 32023.850), but a spirv-cross built on Linux has a fingerprint of its own. Check, and record your tools once:

```sh
export NXW_LINUX=1 PYTHONPATH="$PWD/win/pyshim" SPIRV_CROSS="$TOOLS/bin/spirv-cross" PATH="$HOME/.dotnet:$PATH"
PY=~/.local/venvs/nxnative/bin/python
$PY dm/gfx/tools/dmsh_chain.py --check-tools
$PY dm/gfx/tools/dmsh_chain.py --update-lock && $PY dm/gfx/tools/dmsh_chain.py --header
```

`--check-tools` prints `[RED]` lines and exits 1 when a tool differs. The environment variables load the port's shim, so `xcrun` reaches the Windows Metal compiler and the translator runs through `dotnet`. The chain version in `dm/gfx/nvn/dmsh_chain.h` follows the lock, and the app and its shader libraries are both built from it. Keep the two files' Linux versions local rather than committing them, since the repository's lock is the Windows one.

## Compile check

```sh
~/.local/venvs/nxnative/bin/python win/compile_check.py 010015100B514000 /tmp/nxw_compile_check
```

This compiles every source of the iOS app for one game profile (Mario's here) with LLVM and the iPhoneOS SDK, without any game files.

## Build an IPA

Put one game's files (base game, update, DLC) in a folder of their own, then run:

```sh
~/.local/venvs/nxnative/bin/python win/build_ipa_windows.py <game folder> -k <prod.keys>
```

The IPA lands in the game folder, and the work files go to `<title ID>_build` beside it. A later build reuses every step whose inputs did not change. Upstream's other options work as on Windows (`-h` lists them).

On a 12-thread laptop, the first Arceus build spent 1 hour 46 minutes in the shader stage, where about two dozen `metal.exe` processes under Wine compiled 12,782 shaders at 90 to 250 a minute. Packing the 4 GB IPA took 7 minutes. A later rebuild that found 69 more shaders took 31 minutes: 9 for the shader split with the emulated Oodle decoder, 15 for the shaders, 6 for packing.

Keep the machine awake during a build. A laptop that sleeps when its lid closes pauses the build, and the build carries on when it wakes.

## Install the IPA from Linux

Signing tools are not part of this repository. From Linux, [SideStore](https://sidestore.io) on the device or [Impactor](https://github.com/claration/impactor) on the PC signs and installs IPAs with an Apple ID (Impactor needs `usbmuxd`). With a free Apple ID the app must be signed again every 7 days.

Arceus was tested inside [LiveContainer](https://github.com/LiveContainer/LiveContainer), itself installed with SideStore: copy the IPA to the phone and open it with LiveContainer. There the game runs in LiveContainer's process and gets LiveContainer's memory limit. The memory figure on the launcher screen shows it: about 6 GB with Increased Memory Limit and about 3.4 GB without. The launcher's "Increased Memory Limit" line reads only the app's own signature, which LiveContainer replaces, so go by the memory figure. Arceus was started normally, not in LiveContainer's Multitask mode.

With a free Apple ID, [GetMoreRam](https://github.com/hugeBlack/GetMoreRam) adds Increased Memory Limit to an App ID: sign in with the Apple ID that signs the app, open App IDs, tap Refresh, tap the app and then Add Increased Memory Limit, and reinstall the app from SideStore. A second LiveContainer (LiveContainer2) set up this way showed about 6 GB on the launcher with Arceus.

## Linux problems the port already handles

- Debian and Ubuntu Pythons import their own `sitecustomize` (an apport hook) at startup, so `import sitecustomize` would not load the port's shim, and `build_ipa.sh` would run unmapped. The driver loads the shim by its path.
- Upstream extracts the RomFS as one `RomFS.img`. The app build reads it through `dm/tools/romfs.py` and packs it as `romfs.img`, as `build_ipa.sh` does. Split builds and RomFS mods need a RomFS folder, so they stop with a message when the extraction is an image.
- Upstream's heap check and region check boot the game in the Mac host. Without one, the heap check becomes the Windows port's estimate (a 2 GB pool for games with virtual address memory), and the region check, which only reports, is skipped. Both stamp the profile so later builds don't ask again.
- Oodle-compressed archives (Trinity packs, PlatinumGames PKZ) are decoded by the game's own decoder in an emulated ARM64 machine (`win/oodle_emu.py`), as on Windows. Arceus's GFPAK archives are Oodle-compressed too, and reading them needs a change to upstream's GFPAK reader, proposed to seedds/nxnative separately. With that change the emulator found `OodleLZ_Decompress` in Arceus's main and decoded all 678 GFPAKs.

## Not tested on Linux

- The builder window (`win/gui.pyw`); `Build-IPA-GUI.bat` is for Windows.
- Run-time shader captures on the device (Portal, Fire Emblem: Three Houses, Super Mario Galaxy).
- Encrypted Unreal paks. The shim's AES stand-in uses Windows' CNG, which Linux doesn't have, so these will not work yet.
