# CA-NINAPPLE — NXNative para Windows

Build **nxnative** IPAs on a **Windows 10/11 PC, with no Mac**. Use your own legally dumped game files (NSP / XCI) and your own `prod.keys`. Pick them in a window, press **Build IPA**, and sideload the IPA to your iPhone or iPad.

This repository is a fork of [zenvyzenshiro/NXNativeWindows](https://github.com/zenvyzenshiro/NXNativeWindows), itself a fork of [seedds/nxnative](https://github.com/seedds/nxnative). nxnative is not an emulator: the game's own arm64 code runs directly on the Apple chip, and the Switch graphics are rebuilt on Metal. Upstream builds IPAs only on a Mac with Xcode. The Windows fork adds a Windows build path in [`win/`](win/) and changes as little of upstream as it can. Nothing from any game is in this repository, and the project has no ties to Nintendo, Apple or any game publisher. Authorship, scope and what this copy adds: [NOTICE.md](NOTICE.md).

> Panduan langkah demi langkah dalam Bahasa Indonesia: [win/TUTORIAL.md](win/TUTORIAL.md).
> On Linux the same build runs with native tools and Apple's Metal compiler under Wine: [win/LINUX.md](win/LINUX.md).
> Upstream's own README (games gallery, Mac packing, playing) is kept as [README.nxnative.md](README.nxnative.md).

## Empieza aquí (español)

CA-NINAPPLE es esta distribución: el mismo NXNative for Windows, con las guías en español y
los arreglos de esta copia. Compilas en tu PC el IPA de **tus propios** juegos y lo instalas
en el iPhone o iPad. Aquí no hay juegos, llaves ni SDK de Apple.

| Guía | Cuándo |
|---|---|
| [Empezar en Windows](docs/ca-ninapple/EMPEZAR.md) | de cero al IPA: requisitos, instalación y comandos |
| [Instalar en el iPhone](docs/ca-ninapple/IPHONE.md) | Sideloadly, LiveContainer, memoria y ajustes |
| [Problemas](docs/ca-ninapple/PROBLEMAS.md) | pantalla negra con música, cierres, avisos `[RED]` |
| [Juegos](docs/ca-ninapple/JUEGOS.md) | qué está probado y cómo añadir uno |

En un paso, desde PowerShell en la raíz del repositorio:

```powershell
.\build.ps1 -Game "C:\Juegos\BALLxPIT"
```

El resto de este documento es el manual técnico del fork de Windows, en inglés.

<p align="center">
  <img src="docs/images/windows/gui-start.png" width="32%" alt="The builder window, before picking files">
  <img src="docs/images/windows/gui-building.png" width="32%" alt="A build in progress: the button is the progress bar">
  <img src="docs/images/windows/gui-done.png" width="32%" alt="A finished build with its IPA">
</p>

## Contents

- [Status](#status)
- [Games on NXNative for Windows](#games-on-nxnative-for-windows)
- [Upstream NXNative games](#upstream-nxnative-games)
- [What you need](#what-you-need)
- [One-time setup](#one-time-setup)
- [Build an IPA with the window](#build-an-ipa-with-the-window)
- [Build an IPA from a terminal](#build-an-ipa-from-a-terminal)
- [Split builds (small IPA + data folder)](#split-builds-small-ipa--data-folder)
- [Install the IPA on your iPhone or iPad](#install-the-ipa-on-your-iphone-or-ipad)
- [The launcher on the device](#the-launcher-on-the-device)
- [How the Windows build works](#how-the-windows-build-works)
- [Which games build on Windows](#which-games-build-on-windows)
- [Building on Linux](#building-on-linux)
- [Troubleshooting](#troubleshooting)
- [Differences from upstream](#differences-from-upstream)
- [Repository layout](#repository-layout)
- [Updating from upstream](#updating-from-upstream)
- [Credits and license](#credits-and-license)
- [Legal notice](#legal-notice)

## Status

NXNative for Windows builds the same kind of IPA as upstream NXNative, from a Windows PC. The games below are the ones **built with this fork and run on a real device** by its author (an iPad with an Apple A16 GPU, iPadOS 27, signed with SideStore). Upstream's own list of tested games follows in [Upstream NXNative games](#upstream-nxnative-games).

## Games on NXNative for Windows

| Game | Version | Built on Windows | On the iPad (A16, 6 GB) | Notes |
|---|---|---|---|---|
| **The Legend of Zelda: Tears of the Kingdom** | 1.4.3 | yes: split build, 28,669 shaders, 39 MB app + 17 GB data | **plays**, saves load | With Increased Memory Limit on: 3.7 GB, no closes. Render scale 60 % + MetalFX + Handheld: GPU about 10 ms a frame, mostly 60 fps; drops in fights (CPU). BC textures decoded for the A16. |
| **Balatro** | 1.0 (v0) | yes: LÖVE shaders rebuilt offline from the game's Lua | **plays** | |
| **Mario vs. Donkey Kong** | 1.0.0 (v0) | yes | runs | slow on the A16; not tuned yet |
| **OCTOPATH TRAVELER 0** | 1.0.1 (v0) | yes: 10,596 Oodle-compressed Unreal shaders decoded by the game's own Oodle in an emulated ARM64 machine; the allocator cut and 60 fps addresses ported to v0 | not yet confirmed | 3.2 GB IPA |
| **Megabyte Punch** | 1.0 | yes (no upstream profile: a provisional one) | under test | SDK 8.3.1 address-region fix found automatically |
| **Portal** | 1.0.3 | yes, with one run-time shader capture on the device | not yet confirmed | 8 of its 10 run-time shaders are already made on the PC by the game's own GLSLC in an emulated ARM64 machine; the rest needs the capture IPA |

What this fork adds on top of upstream, for every game:

| | |
|---|---|
| **No Mac** | Metal Developer Tools for Windows, LLVM (clang, ld64.lld) and the iPhoneOS SDK from `Xcode.xip`; upstream's Mac-host steps replaced (LÖVE shaders offline, Oodle / Unreal / LZ5 and GLSLC in an emulated ARM64 machine, run-time captures on the device). |
| **A16 and older GPUs** | BC1–BC7 textures transcoded at upload (`dm/gfx/tex/bc_soft.c`): BC1 / BC2 / BC3 / BC7 into ASTC 4x4 (a quarter of RGBA8's memory; BC1 keeps its palette exactly), unsigned BC6H into RG11B10F, BC4 / BC5 into R8 / RG8. Upstream's IPAs close on these GPUs with `MTLTextureDescriptor has invalid pixelFormat`. `DM_BC_ASTC=0` goes back to uncompressed formats. |
| **Small IPAs** | Split builds: the app alone (tens of MB) plus a data folder or ZIP the app imports itself, with a progress bar, in the background with a Live Activity on iOS 26+. |
| **Memory** | The app asks for Increased Memory Limit in its own signature, so SideStore keeps it when the App ID allows it; a texture memory saver frees the textures' second copy (automatic when memory runs low); a HUD shows fps, GPU time and the memory left. A memory guard in every game caps the frame rate at 30 under 600 MB left and flushes caches under 300 MB (`DM_MEM_GUARD=0` turns it off; the HUD shows `GUARD`). On 6 GB devices, Metal 4 pipelines and the pipeline prebuild are off by default, and the device's own pipeline list is not prewarmed before the first frame, so there is no long "Preparing" screen. |
| **Launcher** | Upstream's single-screen launcher in UIKit, with memory-light defaults on 6 GB devices and Tile memory optimizations as an experiment. |
| **Mods** | Emulator-layout mods (`exefs` IPS / pchtxt, `romfs`) from a `mods` folder, applied as rewriter cuts after a build-ID check. |
| **Window** | A builder window (black and pink) besides the command line. |

The PC this was built and tested on:

| Tool | Version |
|---|---|
| Windows | 11 Pro (x64) |
| Python | 3.15 |
| LLVM (clang, ld64.lld) | 23.1.4 |
| .NET SDK | 10.0.403 |
| Vulkan SDK (spirv-cross, glslangValidator) | 1.4.363.0 |
| zstd | 1.5.7 |
| Metal Developer Tools for Windows | 6.2 (`Apple metal version 32023.850`) |
| iPhoneOS SDK | 27.1, from `Xcode_27.1.xip` |

## Upstream NXNative games

These are **upstream's** tested games (on a Mac or an iPhone with upstream NXNative), not a list of games verified with this fork: most build the same way here, and [Which games build on Windows](#which-games-build-on-windows) lists those that need an extra step (no game needs a Mac). Upstream's 65 tested games, each with its IPA size. A note under a game is upstream's, for example "60 fps with 1.2.0" where the game runs at 60 fps with that update. The [per-game notes](dm/games/README.md#games) give each game's tested version, platforms and known issues.

<table>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/mario-kart-8-deluxe.jpg" width="256" alt="Mario Kart 8 Deluxe"><br>Mario Kart 8 Deluxe<br><sub>~11.9 GB · no Mii heads</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/mario-vs-donkey-kong.jpg" width="256" alt="Mario vs. Donkey Kong"><br>Mario vs. Donkey Kong<br><sub>~1.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/paper-mario-the-thousand-year-door.jpg" width="256" alt="Paper Mario: The Thousand-Year Door"><br>Paper Mario: The Thousand-Year Door<br><sub>~5 GB · 60 fps with 1.0.1</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-3d-world.jpg" width="256" alt="Super Mario 3D World + Bowser's Fury"><br>Super Mario 3D World + Bowser's Fury<br><sub>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-bros-wonder.jpg" width="256" alt="Super Mario Bros. Wonder"><br>Super Mario Bros. Wonder<br><sub>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-galaxy.jpg" width="256" alt="Super Mario Galaxy"><br>Super Mario Galaxy<br><sub>~3 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-galaxy-2.jpg" width="256" alt="Super Mario Galaxy 2"><br>Super Mario Galaxy 2<br><sub>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-odyssey.jpg" width="256" alt="Super Mario Odyssey"><br>Super Mario Odyssey<br><sub>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-breath-of-the-wild.jpg" width="256" alt="The Legend of Zelda: Breath of the Wild"><br>The Legend of Zelda: Breath of the Wild<br><sub>~16 GB · 60 fps with 1.9.0</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-links-awakening.jpg" width="256" alt="The Legend of Zelda: Link's Awakening"><br>The Legend of Zelda: Link's Awakening<br><sub>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-tears-of-the-kingdom.jpg" width="256" alt="The Legend of Zelda: Tears of the Kingdom"><br>The Legend of Zelda: Tears of the Kingdom<br><sub>~17 GB · 60 fps with 1.4.3</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/13-sentinels.jpg" width="256" alt="13 Sentinels: Aegis Rim"><br>13 Sentinels: Aegis Rim<br><sub>~5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/absolum.jpg" width="256" alt="Absolum"><br>Absolum<br><sub>~2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/ace-attorney-investigations.jpg" width="256" alt="Ace Attorney Investigations Collection"><br>Ace Attorney Investigations Collection<br><sub>~7 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/advance-wars-1-2-re-boot-camp.jpg" width="256" alt="Advance Wars 1+2: Re-Boot Camp"><br>Advance Wars 1+2: Re-Boot Camp<br><sub>~7.1 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/ai-the-somnium-files.jpg" width="256" alt="AI: THE SOMNIUM FILES"><br>AI: THE SOMNIUM FILES<br><sub>~8.3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/ai-the-somnium-files-nirvana-initiative.jpg" width="256" alt="AI: THE SOMNIUM FILES - nirvanA Initiative"><br>AI: THE SOMNIUM FILES - nirvanA Initiative<br><sub>~11.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/animal-crossing-new-horizons.jpg" width="256" alt="Animal Crossing: New Horizons"><br>Animal Crossing: New Horizons<br><sub>~10.5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/animal-well.png" width="256" alt="ANIMAL WELL"><br>ANIMAL WELL<br><sub>~54 MB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/astral-chain.png" width="256" alt="ASTRAL CHAIN"><br><a href="dm/games/01007300020FA000/README.md">ASTRAL CHAIN</a><br><sub>~9.7 GB · 60 fps target with 1.0.1</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/balatro.jpg" width="256" alt="Balatro"><br>Balatro<br><sub>~82 MB · played by touch</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/ball-x-pit.jpg" width="256" alt="BALL x PIT"><br>BALL x PIT<br><sub>~1.1 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/bayonetta.jpg" width="256" alt="Bayonetta"><br>Bayonetta<br><sub>~8.8 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/bayonetta-2.jpg" width="256" alt="Bayonetta 2"><br>Bayonetta 2<br><sub>~12.5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/bayonetta-3.jpg" width="256" alt="Bayonetta 3"><br>Bayonetta 3<br><sub>~14.2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/big-brain-academy-brain-vs-brain.jpg" width="256" alt="Big Brain Academy: Brain vs. Brain"><br>Big Brain Academy: Brain vs. Brain<br><sub>~0.8 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/brain-memory-training-academy.jpg" width="256" alt="Brain Memory Training Academy"><br>Brain Memory Training Academy<br><sub>~0.1 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/captain-toad-treasure-tracker.jpg" width="256" alt="Captain Toad: Treasure Tracker"><br>Captain Toad: Treasure Tracker<br><sub>~2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/catherine-full-body.jpg" width="256" alt="Catherine: Full Body"><br>Catherine: Full Body<br><sub>~14 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/celeste.jpg" width="256" alt="Celeste"><br>Celeste<br><sub>~0.9 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/cuphead.jpg" width="256" alt="Cuphead"><br>Cuphead<br><sub>~5 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/dark-souls-remastered-creation.jpg" width="256" alt="DARK SOULS: REMASTERED"><br>DARK SOULS: REMASTERED<br><sub>~4 GB · 60 fps with 1.0.3</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/digimon-story-cyber-sleuth.jpg" width="256" alt="Digimon Story Cyber Sleuth: Complete Edition"><br>Digimon Story Cyber Sleuth: Complete Edition<br><sub>~5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/dragon-quest-vii-reimagined.jpg" width="256" alt="DRAGON QUEST VII Reimagined"><br>DRAGON QUEST VII Reimagined<br><sub>~5.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/dragon-quest-xi-s.jpg" width="256" alt="DRAGON QUEST XI S: Echoes of an Elusive Age – Definitive Edition"><br>DRAGON QUEST XI S: Echoes of an Elusive Age – Definitive Edition<br><sub>~15 GB · 60 fps with 1.0.4</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/final-fantasy-resonance.jpg" width="256" alt="FINAL FANTASY RESONANCE"><br>FINAL FANTASY RESONANCE<br><sub>~10 GB · 60 fps with 1.0.1</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/final-fantasy-tactics.jpg" width="256" alt="FINAL FANTASY TACTICS - The Ivalice Chronicles"><br>FINAL FANTASY TACTICS - The Ivalice Chronicles<br><sub>~11 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/fire-emblem-engage.jpg" width="256" alt="Fire Emblem Engage"><br>Fire Emblem Engage<br><sub>~15 GB · 60 fps with 2.0.0</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/fire-emblem-three-houses.jpg" width="256" alt="Fire Emblem: Three Houses"><br>Fire Emblem: Three Houses<br><sub>~13 GB · 60 fps with 1.2.0</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/ghost-trick-phantom-detective.jpg" width="256" alt="Ghost Trick: Phantom Detective"><br>Ghost Trick: Phantom Detective<br><sub>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/the-great-ace-attorney-chronicles.jpg" width="256" alt="The Great Ace Attorney Chronicles"><br>The Great Ace Attorney Chronicles<br><sub>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/hades.jpg" width="256" alt="Hades"><br>Hades<br><sub>~4 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/hades-ii.jpg" width="256" alt="Hades II"><br>Hades II<br><sub>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/hollow-knight-silksong.jpg" width="256" alt="Hollow Knight: Silksong"><br>Hollow Knight: Silksong<br><sub>~6.4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/hyrule-warriors-age-of-calamity.jpg" width="256" alt="Hyrule Warriors: Age of Calamity"><br>Hyrule Warriors: Age of Calamity<br><sub>~15 GB · 60 fps with 1.3.0</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/luigis-mansion-3.jpg" width="256" alt="Luigi's Mansion 3"><br>Luigi's Mansion 3<br><sub>~7.5 GB · 60 fps with 1.4.0</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/metroid-dread.jpg" width="256" alt="Metroid Dread"><br>Metroid Dread<br><sub>~5 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/monster-hunter-rise.jpg" width="256" alt="Monster Hunter Rise"><br>Monster Hunter Rise<br><sub>~22 GB · 60 fps with 16.0.2</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/monster-train-2.jpg" width="256" alt="Monster Train 2"><br>Monster Train 2<br><sub>~1.6 GB · 60 fps with 1.1.1</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/octopath-traveler-0.jpg" width="256" alt="Octopath Traveler 0"><br>Octopath Traveler 0<br><sub>~4 GB · 60 fps with 1.0.5</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/octopath-traveler-ii.jpg" width="256" alt="Octopath Traveler II"><br>Octopath Traveler II<br><sub>~5.9 GB · 60 fps with 1.1.1</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/patricks-parabox.jpg" width="256" alt="Patrick's Parabox"><br>Patrick's Parabox<br><sub>~0.2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/persona-5-royal.jpg" width="256" alt="Persona 5 Royal"><br>Persona 5 Royal<br><sub>~14.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pikmin-4.jpg" width="256" alt="Pikmin 4"><br>Pikmin 4<br><sub>~10.8 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-legends-z-a.jpg" width="256" alt="Pokémon Legends: Z-A"><br>Pokémon Legends: Z-A<br><sub>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-sword.jpg" width="256" alt="Pokémon Sword"><br>Pokémon Sword<br><sub>~12.4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/portal.jpg" width="256" alt="Portal"><br>Portal<br><sub>~2.6 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/raging-loop.jpg" width="256" alt="Raging Loop"><br>Raging Loop<br><sub>~0.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/rhythm-heaven-groove.jpg" width="256" alt="Rhythm Heaven Groove"><br>Rhythm Heaven Groove<br><sub>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/romance-of-the-three-kingdoms-8-remake.jpg" width="256" alt="ROMANCE OF THE THREE KINGDOMS 8 REMAKE"><br>ROMANCE OF THE THREE KINGDOMS 8 REMAKE<br><sub>~16.8 GB · controller only</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/stardew-valley.jpg" width="256" alt="Stardew Valley"><br>Stardew Valley<br><sub>~0.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/steins-gate-reboot.jpg" width="256" alt="STEINS;GATE RE:BOOT"><br>STEINS;GATE RE:BOOT<br><sub>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-smash-bros-ultimate.jpg" width="256" alt="Super Smash Bros. Ultimate"><br>Super Smash Bros. Ultimate<br><sub>~17.5 GB · offline</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/taiko-risshiden-v-dx.jpg" width="256" alt="Taiko Risshiden V DX"><br>Taiko Risshiden V DX<br><sub>~3.3 GB · Japanese · played by touch</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/unicorn-overlord.jpg" width="256" alt="Unicorn Overlord"><br>Unicorn Overlord<br><sub>~4 GB</sub></td>
</tr>
</table>

## What you need

- **A Windows 10 or 11 PC (x64)** with free disk space of about twice your NSPs plus 10 GB. The SDK and tools take about 5 GB more.
- **An iPhone or iPad on iOS / iPadOS 26 or later.** An **A17 Pro or newer** iPhone, or an **M1 or newer** iPad, reads the games' BC-compressed textures on the GPU. On an **A16 or older** chip this fork decodes them on the CPU: it is slower to load, and textures take more memory. Tested on an iPad with an A16.
- **Your own game dump** (NSP, XCI, NSZ or XCZ: the base game, plus its update and DLC if you have them) and **your own `prod.keys`**.
- **A free Apple ID**, for two downloads from Apple (below) and for signing with Sideloadly.

## One-time setup

### 1. Tools from winget and pip

Open **PowerShell** and run:

```
winget install --id LLVM.LLVM -e
winget install --id Microsoft.DotNet.SDK.10 -e
winget install --id KhronosGroup.VulkanSDK -e
winget install --id Meta.Zstandard -e
python -m pip install lz4 capstone fonttools pillow "backports.zstd; python_version < '3.14'"
```

You need Python 3.10 or later from [python.org](https://www.python.org/downloads/). Check "Add python.exe to PATH" when you install it.

### 2. Two downloads from Apple

Sign in at [developer.apple.com/download](https://developer.apple.com/download/all/) with your Apple ID:

1. **Metal Developer Tools for Windows** (version 5.x or 6.x). Install it anywhere, for example `E:\ProjectIOS\Metal Developer Tools`. It compiles the shader libraries.
2. **Xcode 26 or 27** (`Xcode_27.1.xip`, about 2 GB). Only its iPhoneOS SDK is used. Extract it once (one to two minutes):

   ```
   cd E:\ProjectIOS\nxnative-win
   python win\sdk\extract_xip.py E:\ProjectIOS\Xcode_27.1.xip
   ```

   The SDK lands in `win\sdk\out\iPhoneOS.sdk`. Copying `iPhoneOS.sdk` from a Mac works too.

Apple's Xcode and Apple SDKs Agreement covers these files. Read it before you use them on non-Apple hardware.

### 3. Get this repository

```
git clone https://github.com/zenvyzenshiro/NXNativeWindows.git E:\ProjectIOS\nxnative-win
```

Keep the checkout's line endings as they are. `.gitattributes` turns Git's CRLF conversion off, because the shader chain hashes source bytes.

### 4. Tell the build where the tools are

Copy `win\toolchain.example.json` to `win\toolchain.json` and fix the paths. Tools in their default install folders are found without it. For example:

```json
{
  "llvm": "C:\\Program Files\\LLVM",
  "metal_tools": "E:\\ProjectIOS\\Metal Developer Tools",
  "ios_sdk": "E:\\ProjectIOS\\nxnative-win\\win\\sdk\\out\\iPhoneOS.sdk",
  "spirv_cross_dir": "C:\\VulkanSDK\\1.4.363.0\\Bin",
  "glslangValidator_dir": "C:\\VulkanSDK\\1.4.363.0\\Bin"
}
```

Every key can also be set as an environment variable `NXW_<KEY>`, for example `NXW_IOS_SDK`.

### 5. Check everything

```
python win\doctor.py
```

Every line should read `[ok ]`, ending with `everything a build needs is there`. A missing tool prints where to get it.

## Build an IPA with the window

Double-click **`Build-IPA-GUI.bat`** in the repository folder.

1. **Game files**: click the dashed box to pick your NSP / XCI files (base, update and DLC of one game), or use *Choose folder*. Each file shows as BASE, UPD or DLC with its size. *✕* removes one.
2. **prod.keys**: click *Browse*. The window finds `prod.keys` by itself when it sits next to the game files.
3. **Package**: *Single IPA* (everything in one file) or *App + data folder* (see [Split builds](#split-builds-small-ipa--data-folder)). Below it, **Increased Memory Limit** *On* (default: the app asks for the entitlement in its own signature) or *Off* (same as `--no-entitlements`).
4. Click **Build IPA**. The button turns into the progress bar (stage, step, percentage). A green card then shows the IPA, and *Show in folder* opens it.

Every build uses the defaults. *Details*, shown from the start, lists them:

- App name: the game's own name
- Bundle ID: `org.nxnativewindows.<title ID>`
- Language: the game's default
- IPA: saved next to your game files (*Change* picks another path)
- Signing: none (Sideloadly signs the IPA when you install it)

When the folder you pick also holds another game's files, the window hard-links the chosen files into a folder of their own (`<title ID>_nxw`, next to them). The pipeline packs every game file in its folder, so this keeps the games apart, and hard links take no extra disk space.

## Build an IPA from a terminal

```
cd E:\ProjectIOS\nxnative-win
python win\build_ipa_windows.py "E:\ProjectIOS\Games\MarioWonder" -k "E:\ProjectIOS\Games\prod.keys"
```

Put one game per folder. The IPA appears in that folder (for example `SMBWMobile.ipa`). The work folder `<title ID>_build\` stays next to it, so later builds of the same game reuse its shader cache and take seconds to minutes. Each stage writes its full log to `<title ID>_build\logs\`. A first build compiles every shader with the Windows Metal compiler: Megabyte Punch's 3,498 shaders take about 3.5 minutes on a 12-thread PC.

The options are upstream's (`-h` lists them all):

| Option | Effect |
|---|---|
| `-o D:\out\Game.ipa` | where the IPA goes |
| `--app-name "Name"` | the name on the home screen |
| `--bundle-id com.you.game` | another bundle ID (default `org.nxnativewindows.<title ID>`) |
| `-l ja` | the game language packed into the app |
| `--show-fps` / `--no-show-fps` | the frame-rate counter's default |
| `--keep-extracted` / `--no-keep-extracted` | keep or delete the extracted game files after the build |
| `--env-file my_env.txt` | diagnostic environment variables baked into the app |
| `--split-data` / `--split-data=D:\data\Game-data` | a small app-only IPA plus a data folder ([Split builds](#split-builds-small-ipa--data-folder)) |

Only `--platform ios` builds on Windows. `--prepare-xcode` and the Mac platforms need a Mac.

## Split builds (small IPA + data folder)

A normal IPA carries the game files, so signing and installing a 3 GB game takes minutes, every 7 days with a free Apple ID. A split build keeps them apart:

- `<Game>.ipa`: only the app (Balatro: 10 MB). Sideloadly signs and installs it in seconds.
- `<Game>-data\`: `romfs\`, `msl\` (the shader libraries) and `aoc\` (DLC), hard-linked from the build, so it takes no extra disk space. Its `README.txt` repeats these steps.

Install the IPA, open the app once (it says the game files are missing), then copy the whole `<Game>-data` folder into the app's Documents:

- **Windows**: the *Apple Devices* app (or iTunes) → your device → *Files* → the app → drag the folder in.
- **On the device**: the *Files* app → *On My iPhone/iPad* → the app, from a USB drive, a network share or iCloud Drive.

Close the app fully and open it again. The app looks for `romfs` in Documents and in every folder directly inside it, so the folder can keep its name. Re-signing the IPA later leaves Documents alone. Copy the data folder again only after a new build of the same game (`nxw_data.tsv` in it names the build). Shaders from one build do not load in an app from another chain version: the log says so.

## Install the IPA on your iPhone or iPad

1. Install **[Sideloadly](https://sideloadly.io/)** on Windows. When it asks, also install iTunes and iCloud from Apple's website, not the Microsoft Store versions.
2. Connect the device, drag the `.ipa` onto Sideloadly, enter your Apple ID and press **Start**. Leave Sideloadly's *Bundle ID* and *App Name* fields empty, so the values from the build are kept.
3. In *Advanced options*, enable **Increased Memory Limit** when Sideloadly offers it. Without it iOS gives the app about 3.4 GB and closes the bigger games; with it a recent device gives about 6 GB.
4. On the device, turn on **Settings → Privacy & Security → Developer Mode** and restart. Then trust your Apple ID under **Settings → General → VPN & Device Management**.
5. Open the app: the launcher appears, then press **Play**.

With a free Apple ID the app must be signed again every 7 days.

## The launcher on the device

The settings screen before the game starts follows upstream's single-screen SwiftUI launcher: the game card (icon, name, version, **Play**) on the left third, and on the right every setting under *Game*, *Controls* and *Performance*, each with its note, then *Reset to tested defaults* and the memory available. On Windows it is drawn by [`win/ios/Launcher.m`](win/ios/Launcher.m), a UIKit port, so no Swift toolchain is needed. Only choices that differ from the game's tested defaults are kept.

| Setting | What it does |
|---|---|
| **Frame rate** | 30 or 60 fps, in games whose profile can change it (60 fps patches: Tears of the Kingdom, Breath of the Wild, Octopath Traveler 0 1.0.5, …). |
| **Render scale** | 50–100 % of the game's 3D render size, in games whose rewriter has a dynamic-resolution hook (Tears of the Kingdom, Breath of the Wild). To lower the GPU load in any game, pick *Handheld* (most games render at 720p instead of 1080p), with *Upscaling: MetalFX* to sharpen the result. |
| **Console mode** | *Docked* (the profile's default; touch games such as Balatro default to *Handheld*, because their touches reach the game only in handheld mode). |
| **Upscaling** | *Standard* or *MetalFX*: Apple's spatial upscaler for the presented picture, in every game. Uses more GPU time and can increase heat. |
| **Game language** | The Switch system language, among the languages the game's control data declares (Balatro chooses its language in its own menu). |
| **Frame-rate counter** | on-screen FPS |
| **Touch feedback**, **Game rumble**, **Rumble strength** | haptics (*Controls*) |
| **Frame buffering**, **Metal 4 pipelines**, **Pipeline prebuild**, **Encode thread**, **Hold frames when late**, **Performance HUD** | NVN games' pacing and pipeline options (*Performance*), as upstream documents them |

The list itself is upstream's ([`dm/games/settings.tsv`](dm/games/settings.tsv)), so a setting appears only in the games it applies to. An `env.txt` in the app's Documents folder (Files app) still overrides any setting, as upstream documents.

## How the Windows build works

`win/build_ipa_windows.py` runs upstream's own pipeline (`scripts/build_ipa_from_nsp.py`) unchanged. Only the steps that call macOS tools are replaced, at the subprocess boundary:

| Step | Upstream on a Mac | NXNative for Windows |
|---|---|---|
| Extract NSP / XCI (LibHac) | `nx_extract` (.NET) | the same, built with the .NET SDK for Windows |
| Rewrite the game modules | `patch_nso.py` | the same |
| Translate shaders (Ryujinx) | `dmsh_xlate` apphost | the same locked DLLs through `dotnet dmsh_xlate.dll`, so the chain's fingerprints still match `dmsh_chain.lock` |
| Compile shader libraries | `xcrun metal` / `metallib` (Xcode) | Metal Developer Tools for Windows, through [`win/xcrun.py`](win/xcrun.py) (`-mios-version-min` becomes `-target air64-apple-ios…`) |
| Build the app | `xcodegen` + `xcodebuild` | LLVM `clang -target arm64-apple-ios26.0 -isysroot iPhoneOS.sdk`, linked by `ld64.lld` ([`win/build_app.py`](win/build_app.py)) |
| Launcher | `Launcher.swift` (SwiftUI) | [`win/ios/Launcher.m`](win/ios/Launcher.m) (UIKit, same contract) |
| `@available` runtime | Apple's compiler-rt | [`win/ios/compat_rt.c`](win/ios/compat_rt.c) |
| App icon | `actool` asset catalog | PNG icons in `CFBundleIcons` (Pillow) |
| `sips`, `plutil`, `make -n` | macOS tools | Pillow, `plistlib`, the Makefile's source rules reproduced (the build stops if they change) |
| Executable's x bit in the IPA | Unix modes | `pack_ipa.py --exec` (Windows has no Unix modes) |
| iPhoneOS SDK | inside Xcode | [`win/sdk/extract_xip.py`](win/sdk/extract_xip.py) reads `Xcode.xip` (xar → pbzx → cpio), including Xcode 27's deduplicated archive, whose hard links hold `NULLcanary` placeholders |
| Run-time GL shaders of LÖVE games | boot the game in the Mac host (`DM_GL_CAPTURE`) | [`win/love_shaders.py`](win/love_shaders.py) assembles the same GLSL offline from the Lua that love-nx embeds in `main`. LÖVE's defaults match upstream's capture table byte for byte, and all 31 keys an iPad run asked for match. |
| Heap check of a new game | boot it in the Mac host | an estimate: a 2 GB application pool for games with virtual address memory, stamped into the profile |
| Address-region cuts for an unregistered `sdk` build | added by hand per build ID | [`win/sdk_auto_cuts.py`](win/sdk_auto_cuts.py) finds them from the code (the `AddressRegionManager` constructor's node-area loads and the 1 GB alignment), only when the match is unique |

[`win/pyshim/sitecustomize.py`](win/pyshim/sitecustomize.py) loads in every Python the pipeline starts. It maps `xcrun`, `dmsh_xlate`, `which`, `python3` and `bash build_ipa.sh` to their Windows counterparts, and makes `ctypes.CDLL(None)` safe. The technical notes are in [win/README.md](win/README.md).

## Which games build on Windows

Upstream lists about 65 playable games in its [games table](dm/games/README.md#games), with each game's tested version. On Windows:

- **Most games build as on a Mac.** Examples: Super Mario Bros. Wonder, Super Mario Odyssey, Mario Kart 8 Deluxe, Zelda: Breath of the Wild and Tears of the Kingdom.
- **LÖVE games** (Balatro) build: their run-time shaders are rebuilt offline.
- **Games whose shaders exist only at run time** (Fire Emblem: Three Houses and Portal through GLSLC, Super Mario Galaxy 1 & 2 through Vulkan) are captured **on your device**, as upstream captures them on a Mac:
  1. The first build packs `<Game>-capture.ipa` (no shader libraries; its `dm/env.txt` turns the host's capture on) and stops with instructions.
  2. Install it and play until the title screen, then wait a minute. There may be no picture, because the game has no shaders yet. The host saves every shader the game compiles into the app's Documents.
  3. In the Files app, copy the folder (`glslc_capture` or `vk_capture`) next to the game files on the PC, and build again. The build checks it against the profile's table and makes the real IPA.
- **Oodle, Unreal and LZ5 games** (Octopath Traveler 0 / II, Bayonetta 3, ASTRAL CHAIN, Pokémon Legends: Z-A, DRAGON QUEST XI S, FINAL FANTASY RESONANCE) decode their shader archives with the game's own decoder, run in an emulated ARM64 machine ([`win/oodle_emu.py`](win/oodle_emu.py), [`win/arm64_emu.py`](win/arm64_emu.py)). Octopath Traveler 0's 10,596 Oodle-compressed shaders decode this way.
- **Games without an upstream profile** (Megabyte Punch) get a provisional profile guessed from a survey. The IPA is a best effort and may not boot until the game is brought up ([docs/agents](docs/agents/README.md)).
- **Use the tested version.** Another version builds with its own shaders, but the fixes made for the tested build (60 fps patches and others) do not apply, and the build says so.

## Building on Linux

The same driver, `win/build_ipa_windows.py`, also runs on Linux. There it calls native LLVM (clang and ld64.lld, 20 or later), the .NET 10 SDK, spirv-cross and zstd, and starts Apple's `metal.exe` and `metallib.exe` through Wine ([`win/toolchain.py`](win/toolchain.py) `cmd()`). It was tested on Pop!_OS (Ubuntu 24.04 base) with Wine 9.0, LLVM 23.1.4 and .NET SDK 10.0.403, building Pokémon Legends: Arceus 1.0.2 from a provisional profile, which played in game on an iPhone 16. [win/LINUX.md](win/LINUX.md) has the setup, the shader chain lock on Linux, building, installing from Linux, and the Linux problems the port handles.

## Troubleshooting

| Message or symptom | What to do |
|---|---|
| `doctor.py` shows `MISSING` | Install what the `get it:` line names, or set its path in `win\toolchain.json`. |
| `this game compiles … shaders only at run time; they are captured on your device` | Follow the three steps the message gives: install the capture IPA, play to the title screen, copy the capture folder next to the game files, build again. |
| `[RED] this IPA uses vX, which game profile … was not brought up on` | Put the update named in upstream's games table in the same folder and build again. |
| `[RED] provisional game profile …` | The game has no upstream profile: the IPA may not boot. Send the device log (below). |
| The app closes right after *Play* | Open the **Files** app → *On My iPhone/iPad* → the game → `log.txt` (and `log.prev.txt`), and look at its last lines. [docs/agents/symptoms.md](docs/agents/symptoms.md) indexes known messages. |
| A 3D game closes while loading on an older device | BC textures are decoded on the CPU there and take more memory: sign with *Increased Memory Limit*. `log.txt` says `BC textures: decoded on the CPU` when the fallback is on. |
| The name or bundle ID on the device differs from the build | Leave Sideloadly's *App Name* / *Bundle ID* fields empty. |
| A stage failed | Its full log is in `<title ID>_build\logs\` next to the game files. |

## Differences from upstream

- **Windows build path** in [`win/`](win/), and the window `Build-IPA-GUI.bat`. The same path runs on Linux ([win/LINUX.md](win/LINUX.md)).
- **Default bundle ID `org.nxnativewindows.<title ID>`** in every build path, so these apps install beside upstream-built ones.
- **Derived profiles** get a RomFS marker that their version has (Balatro v0 lacks 1.1.3's marker file).
- **`pack_ipa.py --exec`** sets the executable's mode when packing on Windows.
- **`.gitattributes`** keeps every file byte-identical to upstream on Windows, and the shim writes every pipeline text file with LF line ends, as on a Mac. With CRLF, the host refused the shader libraries' stamp.
- **BC textures on GPUs without BC** (A16 and older) are decoded on the CPU ([`dm/gfx/tex/bc_soft.c`](dm/gfx/tex/bc_soft.c); `DM_BC_SOFT=1` forces it, `=0` turns it off).
- **Address-region cuts for unregistered `sdk` builds** are found from the code ([`win/sdk_auto_cuts.py`](win/sdk_auto_cuts.py)).

## Repository layout

| Path | What it is |
|---|---|
| `Build-IPA-GUI.bat` | starts the window |
| `win/gui.pyw` | the window (Tkinter, black and pink) |
| `win/build_ipa_windows.py` | the Windows driver around upstream's NSP script |
| `win/build_app.py` | the app build that replaces `build_ipa.sh` / Xcode |
| `win/xcrun.py`, `win/toolchain.py` | the `xcrun` stand-in and the tool locator |
| `win/pyshim/sitecustomize.py` | the subprocess shim loaded by every pipeline Python |
| `win/ios/Launcher.m`, `win/ios/compat_rt.c` | the UIKit launcher and the `@available` runtime |
| `win/love_shaders.py` | LÖVE run-time shaders, offline |
| `win/sdk_auto_cuts.py` | address-region cuts for unregistered `sdk` builds |
| `win/sdk/extract_xip.py` | iPhoneOS SDK from `Xcode.xip` |
| `win/doctor.py`, `win/compile_check.py` | toolchain check; compile every app source without game files |
| `win/tests/test_win.py` | unit tests of the Windows parts |
| `win/TUTORIAL.md` | the step-by-step guide in Indonesian |
| `win/LINUX.md` | building on Linux, step by step |
| `win/README.md` | technical notes on the port |
| everything else | upstream nxnative ([README.nxnative.md](README.nxnative.md), [docs/development.md](docs/development.md)) |

Local files git ignores: `win/toolchain.json`, `win/gui_settings.json`, `win/sdk/out/` (the extracted SDK) and `win/build/`.

## Updating from upstream

Last synced with [seedds/nxnative](https://github.com/seedds/nxnative) on 2026-10-27 (135 upstream commits: Kirby and the Forgotten Land's profile, the RomFS image extraction, the region check, the newer launcher contract, and more). The sync before it, on 2026-10-26 (46 upstream commits), brought MetalFX upscaling and the single-screen launcher, offline pipeline archives, the prepare step, hybrid pipelines, Pokémon Shield and Brilliant Diamond, Echoes of Wisdom 1.1.0 and thermal frame-rate caps. The offline pipeline archive (`DM_PSO_GPUS`, default for games whose profile sets `pso_mtl4`) builds on Windows too: Metal Developer Tools for Windows ship `metal-tt`.

```
git remote add upstream https://github.com/seedds/nxnative.git
git fetch upstream
git merge upstream/main
python win\tests\test_win.py
python win\compile_check.py
```

`win/build_app.py` checks `dm/host/Makefile`'s source rules and stops with a clear message when upstream changes them. The functions the driver wraps can also change their arguments upstream; after a merge, check them against `scripts/build_ipa_from_nsp.py` before the first build. When a merge brings a new translator build, keep upstream's DLL lines in `dm/gfx/tools/dmsh_chain.lock` and this port's spirv-cross and Metal lines, then run `dmsh_chain.py --header`.

## Credits and license

- **[seedds/nxnative](https://github.com/seedds/nxnative)** and everything it builds on: [d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile), Ryujinx, Atmosphère, yuzu, LibHac, SPIRV-Cross, glslang, deko3d and the libraries in `dm/third_party` (see [README.nxnative.md](README.nxnative.md#acknowledgements)).
- **Apple's** Metal Developer Tools for Windows and iPhoneOS SDK are downloaded by each user under Apple's terms and are not part of this repository.
- **[LLVM](https://llvm.org/)** (clang, ld64.lld) builds the app on Windows and Linux, and **[Wine](https://www.winehq.org/)** runs Apple's Metal compiler on Linux.
- Linux support by [amansingh909](https://github.com/amansingh909).

MIT License, as upstream ([LICENSE](LICENSE)).

## Legal notice

This is an independent, unofficial developer tool for interoperability and preservation research. It is not affiliated with, endorsed by, or sponsored by Nintendo, Apple, or any game publisher. All trademarks and game titles belong to their owners and are named only to describe compatibility; cover images are shown for identification only.

This repository contains no games, no game files, no keys, no firmware, and no means of bypassing copy protection. You must supply files you dumped yourself from hardware and software you legally own. Do not use this project to obtain or share copyrighted material, and do not open issues asking for game files or keys.
