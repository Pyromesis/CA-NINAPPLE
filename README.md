# CA-NINAPPLE — NXNative para Windows

Compila IPAs de **nxnative** en un **PC con Windows 10/11, sin Mac**. Usa tus propios archivos de juego (NSP / XCI) y tus propias `prod.keys`. Elígelos en una ventana, pulsa **Build IPA** y lleva el IPA a tu iPhone o iPad.

Este repositorio es un fork de [zenvyzenshiro/NXNativeWindows](https://github.com/zenvyzenshiro/NXNativeWindows), que a su vez es un fork de [seedds/nxnative](https://github.com/seedds/nxnative). nxnative no es un emulador: el código arm64 del juego corre directamente en el chip de Apple y los gráficos de Switch se rehacen sobre Metal. Upstream solo compila IPAs en un Mac con Xcode; el fork de Windows añade una ruta de compilación en Windows ([`win/`](win/)) y cambia lo mínimo de upstream. Aquí no hay ningún juego, ni llaves, ni SDK de Apple. Autoría, alcance y qué añade esta copia: [NOTICE.md](NOTICE.md).

> Guía paso a paso en indonesio: [win/TUTORIAL.md](win/TUTORIAL.md).
> En Linux la misma compilación funciona con herramientas nativas y el compilador de Metal de Apple bajo Wine: [win/LINUX.md](win/LINUX.md).
> El README de upstream (galería de juegos, empaquetado en Mac, cómo jugar) está en [README.nxnative.md](README.nxnative.md).

## Empieza aquí

CA-NINAPPLE es esta distribución: el mismo NXNative for Windows, con las guías en español y
los arreglos de esta copia. Compilas en tu PC el IPA de **tus propios** juegos y lo instalas
en el iPhone o iPad. Aquí no hay juegos, llaves ni SDK de Apple.

No es un emulador: el código arm64 del juego corre tal cual en el chip de Apple y los
gráficos de Switch se rehacen sobre Metal. En un PC con Windows, sin Mac.

### Qué hace

| | |
|---|---|
| **Sin Mac** | Metal Developer Tools para Windows, LLVM y el SDK de iPhoneOS de Xcode; upstream solo compila en Mac |
| **IPA pequeño** | Compilación partida: la app sola (decenas de MB) y los datos del juego en *Documents* |
| **Texturas BC** | BC1–BC7 transcodificadas a ASTC para los GPU que no las leen (A16 y anteriores) |
| **Memoria** | La app pide *Increased Memory Limit* en su propia firma: ~6 GB en vez de ~3,4 GB |
| **Launcher** | Pantalla de ajustes propia en UIKit, sin Swift |
| **TV** | Salida a 16:9 por AirPlay o HDMI; el iPhone queda de mando |

### Requisitos

| Cosa | Detalle |
|---|---|
| PC | Windows 10 u 11 de 64 bits, con ~2× el tamaño del juego + 10 GB libres |
| iPhone / iPad | iOS / iPadOS 26 o posterior; **A17 Pro o superior** (iPhone 15 Pro en adelante) o iPad con **M1 o superior**: las texturas vienen en BC y solo esos chips las leen en la GPU |
| Juego | tu propio volcado (NSP, XCI, NSZ o XCZ) y tu `prod.keys` (los juegos de **Switch 2** no los necesitan) |
| Apple ID | gratis: para bajar dos cosas de Apple y para firmar |

### 1. Herramientas

```powershell
winget install --id LLVM.LLVM -e
winget install --id Microsoft.DotNet.SDK.10 -e
winget install --id KhronosGroup.VulkanSDK -e
winget install --id Meta.Zstandard -e
python -m pip install lz4 capstone fonttools pillow "backports.zstd; python_version < '3.14'"
```

De Apple, con tu Apple ID, en <https://developer.apple.com/download/all/>: **Metal Developer
Tools for Windows** y **Xcode 26 o 27** (solo se usa su `iPhoneOS.sdk`, que se extrae con
`python win\sdk\extract_xip.py`). Los enlaces oficiales están en la primera guía.

### 2. Compilar

Doble clic en **`Build-IPA-GUI.bat`** (ventana negra y rosa: se eligen los NSP, el
`prod.keys` y se pulsa *Build IPA*), o desde PowerShell:

```powershell
.\build.ps1 -Game "C:\Juegos\BALLxPIT"
```

El IPA aparece junto al juego; al lado queda `<title ID>_build\`, que es la caché de shaders:
**no la borres**, o la siguiente compilación repite el trabajo.

### 3. Instalar en el iPhone

Firmar con un *signer* (LiveContainer, SideStore, AltStore o `plumesign`), instalar el IPA y
copiar los datos del juego a *Documents*. El paso a paso, con los errores de cada paso, está
en [Instalar desde el PC](docs/ca-ninapple/INSTALAR-DESDE-PC.md).

Con un Apple ID gratis **cada app instalada caduca a los 7 días** y hay un máximo de **3 apps**
con perfil gratuito en cada dispositivo: desinstalar una borra también sus partidas.

La primera compilación de un juego grande se pasa horas (el compilador de Metal de Apple es
de CPU y no tiene atajo por GPU). Los tiempos medidos y lo que sí acelera están en
[Cuánto tarda una compilación](#cuánto-tarda-una-compilación) y en la guía
[Compilar más rápido](docs/ca-ninapple/COMPILAR-RAPIDO.md).

### Guías

| Guía | Cuándo |
|---|---|
| [Empezar en Windows](docs/ca-ninapple/EMPEZAR.md) | de cero al IPA: requisitos, instalación y comandos |
| [Instalar en el iPhone](docs/ca-ninapple/IPHONE.md) | LiveContainer, memoria y ajustes |
| [Instalar desde el PC](docs/ca-ninapple/INSTALAR-DESDE-PC.md) | paso a paso completo: firmar, instalar y comprobar, con errores y soluciones |
| [Compilar más rápido](docs/ca-ninapple/COMPILAR-RAPIDO.md) | dónde se va el tiempo y cómo se acelera |
| [Mandos](docs/ca-ninapple/MANDOS.md) | Xbox y PlayStation por Bluetooth, mapeo de botones y problemas |
| [TV y AirPlay](docs/ca-ninapple/TV-AIRPLAY.md) | el juego a 16:9 en la tele; el iPhone queda de mando |
| [NX2Apple y Switch 2](docs/ca-ninapple/NX2APPLE-SWITCH2.md) | el motor nuevo, qué instalar y qué se puede esperar de rendimiento |
| [Problemas](docs/ca-ninapple/PROBLEMAS.md) | pantalla negra con música, cierres, avisos `[RED]`, builds partidos con XCI |
| [Juegos](docs/ca-ninapple/JUEGOS.md) | qué está probado y cómo añadir uno |

El resto del documento es el manual técnico del fork de Windows. Los documentos que vienen
de upstream ([`docs/development.md`](docs/development.md), [`docs/agents`](docs/agents/README.md),
[`dm/`](dm/)) siguen en inglés.

<p align="center">
  <img src="docs/images/windows/gui-start.png" width="32%" alt="La ventana del builder, antes de elegir los archivos">
  <img src="docs/images/windows/gui-building.png" width="32%" alt="Una compilación en curso: el botón es la barra de progreso">
  <img src="docs/images/windows/gui-done.png" width="32%" alt="Una compilación terminada, con su IPA">
</p>

## Índice

- [Estado](#estado)
- [Juegos compilados en Windows](#juegos-compilados-en-windows)
- [Juegos de upstream](#juegos-de-upstream)
- [Qué necesitas](#qué-necesitas)
- [Preparación inicial](#preparación-inicial)
- [Compilar un IPA con la ventana](#compilar-un-ipa-con-la-ventana)
- [Compilar un IPA desde la terminal](#compilar-un-ipa-desde-la-terminal)
- [Compilación partida: IPA pequeño y carpeta de datos](#compilación-partida-ipa-pequeño-y-carpeta-de-datos)
- [Instalar el IPA en el iPhone o el iPad](#instalar-el-ipa-en-el-iphone-o-el-ipad)
- [El launcher en el dispositivo](#el-launcher-en-el-dispositivo)
- [Cuánto tarda una compilación](#cuánto-tarda-una-compilación)
- [Acelerar la compilación de shaders](#acelerar-la-compilación-de-shaders)
- [Cómo funciona la compilación en Windows](#cómo-funciona-la-compilación-en-windows)
- [Qué juegos compilan en Windows](#qué-juegos-compilan-en-windows)
- [Juegos de Switch 2](#juegos-de-switch-2)
- [Compilar en Linux](#compilar-en-linux)
- [Problemas](#problemas)
- [Diferencias con upstream](#diferencias-con-upstream)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Actualizar desde upstream](#actualizar-desde-upstream)
- [Créditos y licencia](#créditos-y-licencia)
- [Aviso legal](#aviso-legal)

## Estado

NXNative for Windows compila el mismo tipo de IPA que el NXNative de upstream, desde un PC
con Windows. Los juegos de la tabla siguiente son los que **su autor compiló con este fork y
probó en un dispositivo real** (un iPad con GPU A16, iPadOS 27, firmado con SideStore). La
lista de juegos probados por upstream viene después, en [Juegos de upstream](#juegos-de-upstream).

Las compilaciones propias de esta copia, en un iPhone y con la ruta de Windows: Cuphead,
Mario Kart 8 Deluxe, The Legend of Zelda: Tears of the Kingdom, Pokémon: Let's Go, Pikachu! y
Hollow Knight: Silksong, este último con el motor de Switch 2
([docs/ca-ninapple/NX2APPLE-SWITCH2.md](docs/ca-ninapple/NX2APPLE-SWITCH2.md)). Pokémon
Pokopia (Switch 2) se compiló hasta el 22 % de su etapa de Metal y luego se abandonó; sus
mediciones están en [docs/ca-ninapple/COMPILAR-RAPIDO.md](docs/ca-ninapple/COMPILAR-RAPIDO.md).

## Juegos compilados en Windows

| Juego | Versión | Compilado en Windows | En el iPad (A16, 6 GB) | Notas |
|---|---|---|---|---|
| **Hollow Knight: Silksong** | 1.0.30000 | sí: el motor de Switch 2 (NVN2 / Ampere); los 6,29 GB de datos del juego van a *Documents* como `romfs.img` | sin probar | En un iPhone: el launcher muestra el juego y *Play*, el log nombra el archivo del juego y las librerías de shaders, y la app pide Increased Memory Limit |
| **Pokémon Pokopia** (Switch 2) | 2.0.1 | sí, hasta el 22 % de la etapa de Metal; luego abandonado | — | 131.382 shaders: ~1 h de traducción y ~10 h de compilación con Metal en un PC de 12 hilos. Los fuentes y la caché se borraron, así que vuelve a empezar de cero |
| **The Legend of Zelda: Tears of the Kingdom** | 1.4.3 | sí: compilación partida, 28.669 shaders, app de 39 MB + 17 GB de datos | **juega**, las partidas cargan | Con Increased Memory Limit activado: 3,7 GB, sin cierres. Escala de render 60 % + MetalFX + Handheld: GPU ~10 ms por fotograma, sobre todo 60 fps; baja en las luchas (CPU). Texturas BC decodificadas para el A16. |
| **Balatro** | 1.0 (v0) | sí: shaders de LÖVE reconstruidos fuera de línea desde el Lua del juego | **juega** | |
| **Mario vs. Donkey Kong** | 1.0.0 (v0) | sí | corre | lento en el A16; sin ajustar todavía |
| **OCTOPATH TRAVELER 0** | 1.0.1 (v0) | sí: 10.596 shaders de Unreal comprimidos con Oodle, decodificados por el Oodle del propio juego en una máquina ARM64 emulada; el corte del asignador y las direcciones de 60 fps llevados a v0 | sin confirmar todavía | IPA de 3,2 GB |
| **Megabyte Punch** | 1.0 | sí (sin perfil de upstream: uno provisional) | en pruebas | El arreglo de regiones de direcciones del SDK 8.3.1 se encontró solo |
| **Portal** | 1.0.3 | sí, con una captura de shaders en el dispositivo | sin confirmar todavía | 8 de sus 10 shaders de ejecución ya los hace el PC con el GLSLC del propio juego en una máquina ARM64 emulada; el resto necesita el IPA de captura |

Lo que este fork añade a upstream, para todos los juegos:

| | |
|---|---|
| **Sin Mac** | Metal Developer Tools para Windows, LLVM (clang, ld64.lld) y el SDK de iPhoneOS de `Xcode.xip`; los pasos que upstream hace en un Mac se sustituyen (shaders de LÖVE fuera de línea, Oodle / Unreal / LZ5 y GLSLC en una máquina ARM64 emulada, capturas en el dispositivo). |
| **GPU A16 y anteriores** | Texturas BC1–BC7 transcodificadas al subir (`dm/gfx/tex/bc_soft.c`): BC1 / BC2 / BC3 / BC7 a ASTC 4x4 (la cuarta parte de la memoria de RGBA8; BC1 conserva su paleta exacta), BC6H sin signo a RG11B10F, BC4 / BC5 a R8 / RG8. Los IPA de upstream se cierran en estos GPU con `MTLTextureDescriptor has invalid pixelFormat`. `DM_BC_ASTC=0` vuelve a los formatos sin comprimir. |
| **IPA pequeños** | Compilación partida: solo la app (decenas de MB) más una carpeta de datos o un ZIP que la propia app importa, con barra de progreso, en segundo plano y con una Live Activity en iOS 26+. |
| **Memoria** | La app pide Increased Memory Limit en su propia firma, así que SideStore lo conserva cuando el App ID lo permite; un ahorrador de memoria de texturas libera la segunda copia de las texturas (automático cuando queda poca memoria); un HUD muestra los fps, el tiempo de GPU y la memoria libre. Un guardián de memoria en cada juego limita los fotogramas a 30 por debajo de 600 MB libres y vacía cachés por debajo de 300 MB (`DM_MEM_GUARD=0` lo desactiva; el HUD muestra `GUARD`). En dispositivos de 6 GB, las pipelines de Metal 4 y la precompilación de pipelines están desactivadas por defecto, y la lista de pipelines del propio dispositivo no se precalienta antes del primer fotograma, así que no hay una pantalla larga de "Preparing". |
| **Launcher** | El launcher de una sola pantalla de upstream, en UIKit, con valores por defecto ligeros en memoria para dispositivos de 6 GB y optimizaciones de memoria de tiles como experimento. |
| **Mods** | Mods con la disposición de un emulador (`exefs` IPS / pchtxt, `romfs`) desde una carpeta `mods`, aplicados como cortes del rewriter tras comprobar el build ID. |
| **Salida a TV** | Cada juego llena una pantalla AirPlay o HDMI a 16:9 con un accesorio de escena de iOS 27 (`UISceneAccessory`, `dm/ios/Sources/front_ios.m`), activado por defecto; el iPhone queda con el mando y el contador de fps (`DM_TV_OUT=0` lo desactiva). Guía en español: [docs/ca-ninapple/TV-AIRPLAY.md](docs/ca-ninapple/TV-AIRPLAY.md). |
| **Ventana** | Una ventana de compilación (negra y rosa) además de la línea de órdenes. |

El PC en el que se compiló y se probó:

| Herramienta | Versión |
|---|---|
| Windows | 11 Pro (x64) |
| Python | 3.15 |
| LLVM (clang, ld64.lld) | 23.1.4 |
| .NET SDK | 10.0.403 |
| Vulkan SDK (spirv-cross, glslangValidator) | 1.4.363.0 |
| zstd | 1.5.7 |
| Metal Developer Tools for Windows | 6.2 (`Apple metal version 32023.850`) |
| SDK de iPhoneOS | 27.1, del `Xcode_27.1.xip` |

## Juegos de upstream

Estos son los juegos probados por **upstream** (en un Mac o en un iPhone con el NXNative de
upstream), no una lista de juegos verificados con este fork: la mayoría compila igual aquí, y
[Qué juegos compilan en Windows](#qué-juegos-compilan-en-windows) recoge los que necesitan
un paso extra (ningún juego necesita un Mac). Los 91 juegos de la galería de upstream, cada
uno con el tamaño de su IPA. Las notas de un juego son de upstream, por ejemplo "60 fps con
1.2.0" cuando el juego corre a 60 fps con esa actualización. Las
[notas por juego](dm/games/README.md#games) dan la versión probada de cada juego, sus
plataformas y sus problemas conocidos.

<!-- gallery: written by dm/tools/docs_gallery.py from docs/images/gallery.tsv; change the table, then run it -->
<table>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/mario-kart-8-deluxe.jpg" width="256" alt="Mario Kart 8 Deluxe"><br><sub><b>Mario Kart 8 Deluxe</b><br>~11.9 GB · sin cabezas Mii</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/mario-vs-donkey-kong.jpg" width="256" alt="Mario vs. Donkey Kong"><br><sub><b>Mario vs. Donkey Kong</b><br>~1.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/paper-mario-the-thousand-year-door.jpg" width="256" alt="Paper Mario: The Thousand-Year Door"><br><sub><b>Paper Mario: The Thousand-Year Door</b><br>~5 GB · 60 fps con 1.0.1</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-3d-world.jpg" width="256" alt="Super Mario 3D World + Bowser's Fury"><br><sub><b>Super Mario 3D World + Bowser's Fury</b><br>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-bros-wonder.jpg" width="256" alt="Super Mario Bros. Wonder"><br><sub><b>Super Mario Bros. Wonder</b><br>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-galaxy.jpg" width="256" alt="Super Mario Galaxy"><br><sub><b>Super Mario Galaxy</b><br>~3 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-galaxy-2.jpg" width="256" alt="Super Mario Galaxy 2"><br><sub><b>Super Mario Galaxy 2</b><br>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-odyssey.jpg" width="256" alt="Super Mario Odyssey"><br><sub><b>Super Mario Odyssey</b><br>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-breath-of-the-wild.jpg" width="256" alt="The Legend of Zelda: Breath of the Wild"><br><sub><b>The Legend of Zelda: Breath of the Wild</b><br>~16 GB · 60 fps con 1.9.0</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-links-awakening.jpg" width="256" alt="The Legend of Zelda: Link's Awakening"><br><sub><b>The Legend of Zelda: Link's Awakening</b><br>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-tears-of-the-kingdom.jpg" width="256" alt="The Legend of Zelda: Tears of the Kingdom"><br><sub><b>The Legend of Zelda: Tears of the Kingdom</b><br>~17 GB · 60 fps con 1.4.3</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/13-sentinels.jpg" width="256" alt="13 Sentinels: Aegis Rim"><br><sub><b>13 Sentinels: Aegis Rim</b><br>~5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/absolum.jpg" width="256" alt="Absolum"><br><sub><b>Absolum</b><br>~2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/ace-attorney-investigations.jpg" width="256" alt="Ace Attorney Investigations Collection"><br><sub><b>Ace Attorney Investigations Collection</b><br>~7 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/advance-wars-1-2-re-boot-camp.jpg" width="256" alt="Advance Wars 1+2: Re-Boot Camp"><br><sub><b>Advance Wars 1+2: Re-Boot Camp</b><br>~7.1 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/ai-the-somnium-files.jpg" width="256" alt="AI: THE SOMNIUM FILES"><br><sub><b>AI: THE SOMNIUM FILES</b><br>~8.3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/ai-the-somnium-files-nirvana-initiative.jpg" width="256" alt="AI: THE SOMNIUM FILES - nirvanA Initiative"><br><sub><b>AI: THE SOMNIUM FILES - nirvanA Initiative</b><br>~11.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/animal-crossing-new-horizons.jpg" width="256" alt="Animal Crossing: New Horizons"><br><sub><b>Animal Crossing: New Horizons</b><br>~10.5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/animal-well.png" width="256" alt="ANIMAL WELL"><br><sub><b>ANIMAL WELL</b><br>~54 MB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/astral-chain.png" width="256" alt="ASTRAL CHAIN"><br><sub><b><a href="dm/games/01007300020FA000/README.md">ASTRAL CHAIN</a></b><br>~9.7 GB · 60 fps como objetivo con 1.0.1</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/balatro.jpg" width="256" alt="Balatro"><br><sub><b>Balatro</b><br>~82 MB · jugado con el dedo</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/ball-x-pit.jpg" width="256" alt="BALL x PIT"><br><sub><b>BALL x PIT</b><br>~1.1 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/bayonetta.jpg" width="256" alt="Bayonetta"><br><sub><b>Bayonetta</b><br>~8.8 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/bayonetta-2.jpg" width="256" alt="Bayonetta 2"><br><sub><b>Bayonetta 2</b><br>~12.5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/bayonetta-3.jpg" width="256" alt="Bayonetta 3"><br><sub><b>Bayonetta 3</b><br>~14.2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/big-brain-academy-brain-vs-brain.jpg" width="256" alt="Big Brain Academy: Brain vs. Brain"><br><sub><b>Big Brain Academy: Brain vs. Brain</b><br>~0.8 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/brain-memory-training-academy.jpg" width="256" alt="Brain Memory Training Academy"><br><sub><b>Brain Memory Training Academy</b><br>~0.1 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/captain-toad-treasure-tracker.jpg" width="256" alt="Captain Toad: Treasure Tracker"><br><sub><b>Captain Toad: Treasure Tracker</b><br>~2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/catherine-full-body.jpg" width="256" alt="Catherine: Full Body"><br><sub><b>Catherine: Full Body</b><br>~14 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/celeste.jpg" width="256" alt="Celeste"><br><sub><b>Celeste</b><br>~0.9 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/cuphead.jpg" width="256" alt="Cuphead"><br><sub><b>Cuphead</b><br>~5 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/dark-souls-remastered-creation.jpg" width="256" alt="DARK SOULS: REMASTERED"><br><sub><b>DARK SOULS: REMASTERED</b><br>~4 GB · 60 fps con 1.0.3</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/digimon-story-cyber-sleuth.jpg" width="256" alt="Digimon Story Cyber Sleuth: Complete Edition"><br><sub><b>Digimon Story Cyber Sleuth: Complete Edition</b><br>~5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/donkey-kong-country-tropical-freeze.jpg" width="256" alt="Donkey Kong Country: Tropical Freeze"><br><sub><b>Donkey Kong Country: Tropical Freeze</b><br>~7.3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/dragon-quest-vii-reimagined.jpg" width="256" alt="DRAGON QUEST VII Reimagined"><br><sub><b>DRAGON QUEST VII Reimagined</b><br>~5.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/dragon-quest-xi-s.jpg" width="256" alt="DRAGON QUEST XI S: Echoes of an Elusive Age – Definitive Edition"><br><sub><b>DRAGON QUEST XI S: Echoes of an Elusive Age – Definitive Edition</b><br>~15 GB · 60 fps con 1.0.4</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/final-fantasy-resonance.jpg" width="256" alt="FINAL FANTASY RESONANCE"><br><sub><b>FINAL FANTASY RESONANCE</b><br>~10 GB · 60 fps con 1.0.1</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/final-fantasy-tactics.jpg" width="256" alt="FINAL FANTASY TACTICS - The Ivalice Chronicles"><br><sub><b>FINAL FANTASY TACTICS - The Ivalice Chronicles</b><br>~11 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/fire-emblem-engage.jpg" width="256" alt="Fire Emblem Engage"><br><sub><b>Fire Emblem Engage</b><br>~15 GB · 60 fps con 2.0.0</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/fire-emblem-three-houses.jpg" width="256" alt="Fire Emblem: Three Houses"><br><sub><b>Fire Emblem: Three Houses</b><br>~13 GB · 60 fps con 1.2.0</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/ghost-trick-phantom-detective.jpg" width="256" alt="Ghost Trick: Phantom Detective"><br><sub><b>Ghost Trick: Phantom Detective</b><br>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/the-great-ace-attorney-chronicles.jpg" width="256" alt="The Great Ace Attorney Chronicles"><br><sub><b>The Great Ace Attorney Chronicles</b><br>~4 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/hades.jpg" width="256" alt="Hades"><br><sub><b>Hades</b><br>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/hades-ii.jpg" width="256" alt="Hades II"><br><sub><b>Hades II</b><br>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/hollow-knight-silksong.jpg" width="256" alt="Hollow Knight: Silksong"><br><sub><b>Hollow Knight: Silksong</b><br>~6.4 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/hyrule-warriors-age-of-calamity.jpg" width="256" alt="Hyrule Warriors: Age of Calamity"><br><sub><b>Hyrule Warriors: Age of Calamity</b><br>~15 GB · 60 fps con 1.3.0</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/kirby-and-the-forgotten-land.jpg" width="256" alt="Kirby and the Forgotten Land"><br><sub><b>Kirby and the Forgotten Land</b><br>~6.4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/luigis-mansion-3.jpg" width="256" alt="Luigi's Mansion 3"><br><sub><b>Luigi's Mansion 3</b><br>~7.5 GB · 60 fps con 1.4.0</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/metroid-dread.jpg" width="256" alt="Metroid Dread"><br><sub><b>Metroid Dread</b><br>~5 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/monster-hunter-rise.jpg" width="256" alt="Monster Hunter Rise"><br><sub><b>Monster Hunter Rise</b><br>~22 GB · 60 fps con 16.0.2</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/monster-train-2.jpg" width="256" alt="Monster Train 2"><br><sub><b>Monster Train 2</b><br>~1.6 GB · 60 fps con 1.1.1</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/octopath-traveler.jpg" width="256" alt="OCTOPATH TRAVELER"><br><sub><b>OCTOPATH TRAVELER</b><br>~3.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/octopath-traveler-0.jpg" width="256" alt="Octopath Traveler 0"><br><sub><b>Octopath Traveler 0</b><br>~4 GB · 60 fps con 1.0.5</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/octopath-traveler-ii.jpg" width="256" alt="Octopath Traveler II"><br><sub><b>Octopath Traveler II</b><br>~5.9 GB · 60 fps con 1.1.1</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/patricks-parabox.jpg" width="256" alt="Patrick's Parabox"><br><sub><b>Patrick's Parabox</b><br>~0.2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/persona-5-royal.jpg" width="256" alt="Persona 5 Royal"><br><sub><b>Persona 5 Royal</b><br>~14.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pikmin-4.jpg" width="256" alt="Pikmin 4"><br><sub><b>Pikmin 4</b><br>~10.8 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-brilliant-diamond.jpg" width="256" alt="Pokémon Brilliant Diamond"><br><sub><b>Pokémon Brilliant Diamond</b><br>~4.6 GB · 60 fps con 1.3.0</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-legends-z-a.jpg" width="256" alt="Pokémon Legends: Z-A"><br><sub><b>Pokémon Legends: Z-A</b><br>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-scarlet.png" width="256" alt="Pokémon Scarlet"><br><sub><b>Pokémon Scarlet</b><br>~7.0 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-sword.jpg" width="256" alt="Pokémon Sword"><br><sub><b>Pokémon Sword</b><br>~12.4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-shield.jpg" width="256" alt="Pokémon Shield"><br><sub><b>Pokémon Shield</b><br>~12.4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/portal.jpg" width="256" alt="Portal"><br><sub><b>Portal</b><br>~2.6 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/raging-loop.jpg" width="256" alt="Raging Loop"><br><sub><b>Raging Loop</b><br>~0.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/rhythm-heaven-groove.jpg" width="256" alt="Rhythm Heaven Groove"><br><sub><b>Rhythm Heaven Groove</b><br>~3 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/romance-of-the-three-kingdoms-8-remake.jpg" width="256" alt="ROMANCE OF THE THREE KINGDOMS 8 REMAKE"><br><sub><b>ROMANCE OF THE THREE KINGDOMS 8 REMAKE</b><br>~16.8 GB · solo con mando</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/sea-of-stars.jpg" width="256" alt="Sea of Stars"><br><sub><b>Sea of Stars</b><br>~5.1 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/shin-megami-tensei-v-vengeance.jpg" width="256" alt="SHIN MEGAMI TENSEI V: Vengeance"><br><sub><b>SHIN MEGAMI TENSEI V: Vengeance</b><br>~14.6 GB · 60 fps con 1.0.3</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/stardew-valley.jpg" width="256" alt="Stardew Valley"><br><sub><b>Stardew Valley</b><br>~0.6 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/steins-gate-reboot.jpg" width="256" alt="STEINS;GATE RE:BOOT"><br><sub><b>STEINS;GATE RE:BOOT</b><br>~6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/super-smash-bros-ultimate.jpg" width="256" alt="Super Smash Bros. Ultimate"><br><sub><b>Super Smash Bros. Ultimate</b><br>~17.5 GB · sin conexión</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/taiko-risshiden-v-dx.jpg" width="256" alt="Taiko Risshiden V DX"><br><sub><b>Taiko Risshiden V DX</b><br>~3.3 GB · japonés · jugado con el dedo</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/unicorn-overlord.jpg" width="256" alt="Unicorn Overlord"><br><sub><b>Unicorn Overlord</b><br>~4 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/yoshis-crafted-world.jpg" width="256" alt="Yoshi's Crafted World"><br><sub><b><a href="dm/games/01006000040C2000/README.md">Yoshi's Crafted World</a></b><br>~6.1 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/nier-automata.png" width="256" alt="NieR:Automata The End of YoRHa Edition"><br><sub><b>NieR:Automata The End of YoRHa Edition</b><br>~10.9 GB · 60 fps con 1.0.3</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/zelda-echoes-of-wisdom.jpg" width="256" alt="The Legend of Zelda: Echoes of Wisdom"><br><sub><b>The Legend of Zelda: Echoes of Wisdom</b><br>~7.8 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/donkey-kong-country-returns-hd.png" width="256" alt="Donkey Kong Country Returns HD"><br><sub><b>Donkey Kong Country Returns HD</b><br>~11.6 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/mario-rabbids-sparks-of-hope.jpg" width="256" alt="Mario + Rabbids Sparks of Hope"><br><sub><b>Mario + Rabbids Sparks of Hope</b><br>~9.8 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/xenoblade-chronicles-2.jpg" width="256" alt="Xenoblade Chronicles 2"><br><sub><b>Xenoblade Chronicles 2</b><br>~17.1 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/xenoblade-chronicles-3.jpg" width="256" alt="Xenoblade Chronicles 3"><br><sub><b>Xenoblade Chronicles 3</b><br>~19.2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/final-fantasy-crystal-chronicles.jpg" width="256" alt="FINAL FANTASY CRYSTAL CHRONICLES Remastered Edition"><br><sub><b>FINAL FANTASY CRYSTAL CHRONICLES Remastered Edition</b></sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/return-of-the-obra-dinn.png" width="256" alt="Return of the Obra Dinn"><br><sub><b><a href="dm/games/010032E00E6E2000/README.md">Return of the Obra Dinn</a></b><br>~0.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/blasphemous-2.png" width="256" alt="Blasphemous 2"><br><sub><b><a href="dm/games/010040801A4C8000/README.md">Blasphemous 2</a></b><br>~1.5 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/silver-pines.jpg" width="256" alt="Silver Pines"><br><sub><b><a href="dm/games/0100D5B026844000/README.md">Silver Pines</a></b></sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/blasphemous.jpg" width="256" alt="Blasphemous"><br><sub><b><a href="dm/games/0100698009C6E000/README.md">Blasphemous</a></b><br>~0.9 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/final-fantasy-x-x2-hd-remaster.jpg" width="256" alt="FINAL FANTASY X/X-2 HD Remaster"><br><sub><b><a href="dm/games/0100BC300CB48000/README.md">FINAL FANTASY X/X-2 HD Remaster</a></b><br>~26.5 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/mario-rabbids-kingdom-battle.jpg" width="256" alt="Mario + Rabbids Kingdom Battle"><br><sub><b><a href="dm/games/010067300059A000/README.md">Mario + Rabbids Kingdom Battle</a></b><br>~5 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/persona-4-golden.jpg" width="256" alt="Persona 4 Golden"><br><sub><b><a href="dm/games/010062B01525C000/README.md">Persona 4 Golden</a></b></sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/xenoblade-chronicles-definitive-edition.jpg" width="256" alt="Xenoblade Chronicles: Definitive Edition"><br><sub><b><a href="dm/games/0100FF500E34A000/README.md">Xenoblade Chronicles: Definitive Edition</a></b><br>~13.2 GB</sub></td>
<td align="center" valign="top" width="33%"><img src="docs/images/pokemon-legends-arceus.jpg" width="256" alt="Pokémon Legends: Arceus"><br><sub><b><a href="dm/games/01001F5010DFA000/README.md">Pokémon Legends: Arceus</a></b><br>~4.2 GB</sub></td>
</tr>
<tr>
<td align="center" valign="top" width="33%"><img src="docs/images/super-mario-party-jamboree.jpg" width="256" alt="Super Mario Party Jamboree"><br><sub><b><a href="dm/games/0100965017338000/README.md">Super Mario Party Jamboree</a></b></sub></td>
<td></td>
<td></td>
</tr>
</table>
<!-- end of gallery -->

## Qué necesitas

- **Un PC con Windows 10 u 11 (x64)** y espacio libre de disco de unas dos veces tus NSP más
  10 GB. El SDK y las herramientas ocupan unos 5 GB más.
- **Un iPhone o iPad con iOS / iPadOS 26 o posterior.** Un **iPhone A17 Pro o superior**, o
  un **iPad con M1 o superior**, leen las texturas comprimidas en BC de los juegos en la GPU.
  En un chip **A16 o anterior** este fork las decodifica en la CPU: tarda más en cargar y las
  texturas ocupan más memoria. Probado en un iPad con A16.
- **Tu propio volcado del juego** (NSP, XCI, NSZ o XCZ: el juego base, más su actualización
  y sus DLC si los tienes) y **tus propias `prod.keys`**.
- **Un Apple ID gratis**, para las dos descargas de Apple (abajo) y para firmar la app.

## Preparación inicial

### 1. Herramientas de winget y pip

Abre **PowerShell** y ejecuta:

```
winget install --id LLVM.LLVM -e
winget install --id Microsoft.DotNet.SDK.10 -e
winget install --id KhronosGroup.VulkanSDK -e
winget install --id Meta.Zstandard -e
python -m pip install lz4 capstone fonttools pillow "backports.zstd; python_version < '3.14'"
```

Necesitas Python 3.10 o posterior de [python.org](https://www.python.org/downloads/). Marca
"Add python.exe to PATH" al instalarlo.

### 2. Dos descargas de Apple

Entra en [developer.apple.com/download](https://developer.apple.com/download/all/) con tu
Apple ID:

1. **Metal Developer Tools for Windows** (versión 5.x o 6.x). Instálalo donde quieras, por
   ejemplo `E:\ProjectIOS\Metal Developer Tools`. Compila las librerías de shaders.
2. **Xcode 26 o 27** (`Xcode_27.1.xip`, unos 2 GB). Solo se usa su SDK de iPhoneOS. Extráelo
   una vez (uno o dos minutos):

   ```
   cd E:\ProjectIOS\nxnative-win
   python win\sdk\extract_xip.py E:\ProjectIOS\Xcode_27.1.xip
   ```

   El SDK queda en `win\sdk\out\iPhoneOS.sdk`. También vale copiar `iPhoneOS.sdk` de un Mac.

El acuerdo de licencia de Xcode y de los SDK de Apple cubre estos archivos: léelo antes de
usarlos en hardware que no es de Apple.

### 3. Traer este repositorio

```
git clone https://github.com/zenvyzenshiro/NXNativeWindows.git E:\ProjectIOS\nxnative-win
```

Deja los finales de línea del clon tal como están. `.gitattributes` desactiva la conversión
CRLF de Git, porque la cadena de shaders calcula hashes de los bytes del código.

### 4. Decirle al build dónde están las herramientas

Copia `win\toolchain.example.json` a `win\toolchain.json` y corrige las rutas. Las
herramientas en sus carpetas de instalación por defecto se encuentran sin este archivo. Por
ejemplo:

```json
{
  "llvm": "C:\\Program Files\\LLVM",
  "metal_tools": "E:\\ProjectIOS\\Metal Developer Tools",
  "ios_sdk": "E:\\ProjectIOS\\nxnative-win\\win\\sdk\\out\\iPhoneOS.sdk",
  "spirv_cross_dir": "C:\\VulkanSDK\\1.4.363.0\\Bin",
  "glslangValidator_dir": "C:\\VulkanSDK\\1.4.363.0\\Bin"
}
```

Cada clave se puede poner también como variable de entorno `NXW_<CLAVE>`, por ejemplo
`NXW_IOS_SDK`.

### 5. Comprobarlo todo

```
python win\doctor.py
```

Cada línea debería decir `[ok ]`, acabando en `everything a build needs is there`. Una
herramienta que falte indica de dónde conseguirla.

## Compilar un IPA con la ventana

Haz doble clic en **`Build-IPA-GUI.bat`** dentro de la carpeta del repositorio.

1. **Archivos del juego**: pulsa el recuadro discontinuo para elegir tus NSP / XCI (base,
   actualización y DLC de un mismo juego), o usa *Choose folder*. Cada archivo aparece como
   BASE, UPD o DLC con su tamaño. *✕* quita uno.
2. **prod.keys**: pulsa *Browse*. La ventana encuentra `prod.keys` por su cuenta cuando está
   junto a los archivos del juego.
3. **Paquete**: *Single IPA* (todo en un archivo) o *App + data folder* (ver
   [Compilación partida](#compilación-partida-ipa-pequeño-y-carpeta-de-datos)). Debajo,
   **Increased Memory Limit** *On* (por defecto: la app pide el permiso en su propia firma) o
   *Off* (igual que `--no-entitlements`).
4. Pulsa **Build IPA**. El botón se convierte en la barra de progreso (etapa, paso,
   porcentaje). Después aparece una tarjeta verde con el IPA, y *Show in folder* lo abre.

Cada compilación usa los valores por defecto. *Details*, visible desde el principio, los
recoge:

- Nombre de la app: el nombre del propio juego
- Bundle ID: `org.nxnativewindows.<title ID>`
- Idioma: el del propio juego
- IPA: se guarda junto a tus archivos del juego (*Change* elige otra ruta)
- Firma: ninguna (la herramienta de firma firma el IPA al instalarlo)

Cuando la carpeta que eliges contiene también archivos de otro juego, la ventana crea
enlaces duros de los archivos elegidos en una carpeta propia (`<title ID>_nxw`, al lado). El
pipeline empaqueta todos los archivos de juego de su carpeta, así que esto mantiene los
juegos separados, y los enlaces duros no ocupan disco extra.

## Compilar un IPA desde la terminal

```
cd E:\ProjectIOS\nxnative-win
python win\build_ipa_windows.py "E:\ProjectIOS\Games\MarioWonder" -k "E:\ProjectIOS\Games\prod.keys"
```

Un juego por carpeta. El IPA aparece en esa carpeta (por ejemplo `SMBWMobile.ipa`). La carpeta
de trabajo `<title ID>_build\` se queda al lado, así que las compilaciones siguientes del
mismo juego reutilizan su caché de shaders y tardan de segundos a minutos. Cada etapa escribe
su log completo en `<title ID>_build\logs\`. La primera compilación compila todos los shaders
con el compilador de Metal de Windows: los 3.498 shaders de Megabyte Punch tardan unos 3,5
minutos en un PC de 12 hilos.

Las opciones son las de upstream (`-h` las lista todas):

| Opción | Efecto |
|---|---|
| `-o D:\out\Juego.ipa` | dónde va el IPA |
| `--app-name "Nombre"` | el nombre en la pantalla de inicio |
| `--bundle-id com.tu.juego` | otro bundle ID (por defecto `org.nxnativewindows.<title ID>`) |
| `-l ja` | el idioma del juego que se empaqueta en la app |
| `--show-fps` / `--no-show-fps` | el valor por defecto del contador de fotogramas |
| `--keep-extracted` / `--no-keep-extracted` | conservar o borrar los archivos extraídos del juego tras la compilación |
| `--env-file my_env.txt` | variables de entorno de diagnóstico metidas en la app |
| `--split-data` / `--split-data=D:\data\Juego-data` | un IPA solo con la app más una carpeta de datos ([compilación partida](#compilación-partida-ipa-pequeño-y-carpeta-de-datos)) |

En Windows solo compila `--platform ios`. `--prepare-xcode` y las plataformas de Mac
necesitan un Mac.

## Compilación partida: IPA pequeño y carpeta de datos

Un IPA normal lleva dentro los archivos del juego, así que firmar e instalar un juego de 3
GB tarda minutos, cada 7 días con un Apple ID gratis. Una compilación partida los separa:

- `<Juego>.ipa`: solo la app (Balatro: 10 MB). LiveContainer la instala en segundos.
- `<Juego>-data\`: `romfs\`, `msl\` (las librerías de shaders) y `aoc\` (los DLC), con enlaces
  duros desde la compilación, así que no ocupan disco extra. Su `README.txt` repite estos
  pasos.

Instala el IPA, abre la app una vez (dice que faltan los archivos del juego) y copia toda la
carpeta `<Juego>-data` dentro de *Documents* de la app:

- **En Windows**: la app *Apple Devices* (o iTunes) → tu dispositivo → *Files* → la app →
  arrastra la carpeta dentro.
- **En el dispositivo**: la app *Files* → *On My iPhone/iPad* → la app, desde una memoria USB,
  un recurso de red o iCloud Drive.

Cierra la app del todo y ábrela otra vez. La app busca `romfs` en *Documents* y en cada
carpeta que hay dentro, así que la carpeta puede conservar su nombre. Volver a firmar el IPA
después no toca *Documents*. Copia la carpeta de datos otra vez solo tras una compilación
nueva del mismo juego (`nxw_data.tsv` de dentro indica la compilación). Los shaders de una
compilación no cargan en una app de otra versión de la cadena: el log lo dice.

## Instalar el IPA en el iPhone o el iPad

La herramienta de firma es la que instala la app. Este proyecto documenta **LiveContainer**,
que ejecuta cada IPA dentro de su propia app:

1. Instala **LiveContainer** ([LiveContainer/LiveContainer](https://github.com/LiveContainer/LiveContainer))
   con un firmador que te deje añadir la capacidad **Increased Memory Limit**
   (`com.apple.developer.kernel.increased-memory-limit`); SideStore, AltStore y PlumeImpactor
   pueden firmarlo. Pide ese permiso para LiveContainer mismo: sin él iOS da a la app unos
   3,4 GB y cierra los juegos grandes; con él, un dispositivo reciente da unos 6 GB.
2. En LiveContainer, importa un **certificado de firma** (Settings → Certificate, de
   SideStore/AltStore o un `.p12` con su contraseña): en iOS 26 LiveContainer firma cada app
   invitada sin JIT y no puede ejecutar una sin certificado.
3. Instala el `.ipa` con el botón **+** y elígelo desde la app *Files*. El juego aparece como
   una app más dentro de LiveContainer.
4. En el dispositivo, activa **Ajustes → Privacidad y seguridad → Modo desarrollador** y
   reinicia. Después confía en el certificado de firma en **Ajustes → General → VPN y gestión
   de dispositivos**.
5. Abre el juego desde LiveContainer: aparece el launcher, y luego pulsa **Play**.

Con un Apple ID gratis hay que volver a firmar la app cada 7 días.

## El launcher en el dispositivo

La pantalla de ajustes que sale antes de empezar el juego sigue el launcher de una sola
pantalla de upstream (SwiftUI): la tarjeta del juego (icono, nombre, versión, **Play**) en el
tercio izquierdo, y a la derecha todos los ajustes de *Juego*, *Gráficos*, *Controles* y
*Rendimiento*, cada uno con su nota, luego *Reset to tested defaults* y la memoria
disponible. En Windows lo dibuja [`win/ios/Launcher.m`](win/ios/Launcher.m), un port a UIKit,
así que no hace falta ninguna cadena de herramientas de Swift. Solo se guardan las
elecciones que difieren de los valores por defecto probados del juego.

| Ajuste | Qué hace |
|---|---|
| **Frame rate** | 30 o 60 fps, en los juegos cuyo perfil puede cambiarlo (parches de 60 fps: Tears of the Kingdom, Breath of the Wild, Octopath Traveler 0 1.0.5, …). |
| **Render scale** | 50–100 % del tamaño de render 3D del juego, en los juegos cuyo rewriter tiene un enganche de resolución dinámica (Tears of the Kingdom, Breath of the Wild). Para bajar la carga de la GPU en cualquier juego, elige *Handheld* (la mayoría renderizan a 720p en vez de 1080p), con *Upscaling: MetalFX* para afinar el resultado. |
| **Console mode** | *Docked* (el valor por defecto del perfil; los juegos táctiles como Balatro vienen en *Handheld*, porque sus toques solo llegan al juego en modo portátil). |
| **Upscaling** | *Standard* o *MetalFX*: el escalador espacial de Apple para la imagen que se presenta, en todos los juegos. Usa más tiempo de GPU y puede aumentar el calor. |
| **Game language** | El idioma del sistema de Switch, entre los que declara la información de control del juego (Balatro elige su idioma en su propio menú). |
| **Contador de fotogramas** | los fps en pantalla |
| **Touch feedback**, **Game rumble**, **Rumble strength** | vibración (*Controles*) |
| **Frame buffering**, **Metal 4 pipelines**, **Pipeline prebuild**, **Encode thread**, **Hold frames when late**, **Performance HUD** | opciones de ritmo y de pipelines de los juegos NVN (*Rendimiento*), tal como las documenta upstream |

La lista es la de upstream ([`dm/games/settings.tsv`](dm/games/settings.tsv)), así que un
ajuste solo aparece en los juegos a los que aplica. Un `env.txt` en *Documents* de la app
(app *Files*) sigue mandando sobre cualquier ajuste, como documenta upstream.

## Cuánto tarda una compilación

La primera compilación de un juego compila todos sus shaders con el compilador de Metal de
Apple; las siguientes reutilizan la caché de la carpeta de compilación. Dos etapas son largas:

| Etapa | Qué hace | Coste |
|---|---|---|
| Traducción | Los binarios de shaders del juego → SPIR-V (el traductor de Ryujinx) → MSL (spirv-cross) | ~38 shaders/s |
| Compilación con Metal | MSL → `.metallib` para iPhoneOS (`metal.exe` + `metallib.exe`) | 0,42 s de CPU por shader |

Medido en un Ryzen 5 5600G de 6 núcleos / 12 hilos con Metal Developer Tools 32023.850:

| Juego | Shaders | Primera compilación | Las siguientes |
|---|---|---|---|
| BALL x PIT | 22.319 (6.584 textos de MSL distintos) | ~25 min | minutos |
| The Legend of Zelda: Tears of the Kingdom | 28.669 | ~35 min (estimado) | minutos |
| Pokémon Pokopia (Switch 2) | 131.382 | ~1 h de traducción + ~10 h de compilación con Metal | — |

El `metal.exe` de Apple es un compilador de host (un driver de clang con el back end de
Metal): corre en la CPU y nunca usa la tarjeta gráfica del PC, así que esta etapa no se
puede pasar a la GPU. Un shader de Switch 2 cuesta unas cinco veces más que uno de Switch 1
(los programas Ampere SM86 son mucho más grandes), y por eso un juego de 131.382 shaders se
tarda horas.

Upstream mide ese mismo juego de Pokopia en **~2,5 h en un M4 Pro**, con una reparación que
a este motor todavía le falta: el builder termina los shaders en hilos que comparten un solo
GIL, de modo que un núcleo hace el trabajo en Python (reescribir el MSL, calcular la
reflexión, escribir las salidas) mientras los demás compiladores de Metal esperan. El arreglo
es terminar cada shader en un **proceso** trabajador: ×1,9 medido por upstream (42.848
shaders: 3.506 s → 1.826 s). Está descrito en
[Compilar más rápido](docs/ca-ninapple/COMPILAR-RAPIDO.md).

## Acelerar la compilación de shaders

| Palanca | Efecto |
|---|---|
| Más núcleos | Lineal: el doble de núcleos, la mitad de tiempo. `NXW_SHADER_JOBS` fija el número de trabajadores (por defecto, uno por hilo lógico) |
| Terminar cada shader en un proceso, no en un hilo | Arranque de los trabajadores en el propio PC: **×1,9** medido por upstream. En Windows hay que portarlo (upstream usa `fork`) |
| Conservar `<title ID>_build\` | Es la caché. Borra el IPA, no la carpeta |
| Una plataforma por carpeta | Una carpeta que ya tiene las librerías de un build de Mac de la misma cadena compila también las de macOS, y eso duplica el trabajo de Metal |
| Otra máquina | Una máquina en la nube con 32 vCPU por la vía de Linux ([win/LINUX.md](win/LINUX.md)), o un Mac con chip Apple silicon |
| Un Mac | Upstream mide ese juego de Pokopia en **~2,5 h en un M4 Pro**: ×3-5 frente a este PC |

Medido con 72 shaders: 6 trabajadores dan 9,2 shaders/s, 12 dan 14,8, 18 dan 14,6 y 24 dan
14,6. Más trabajadores que núcleos no ayudan.

Medido y **sin** resultado: `-O0` (más lento, 6,6 frente a 10,5 shaders/s), quitar
`-fpreserve-invariance` (sin cambio), compartir la caché de Metal entre juegos (solo coincide
el 0,2 % de los textos de MSL entre dos juegos) y la GPU (el compilador no la usa).

Las medidas completas, y los otros proyectos que hacen correr juegos de Switch en Apple
silicon, están en la guía [Compilar más rápido](docs/ca-ninapple/COMPILAR-RAPIDO.md).

## Cómo funciona la compilación en Windows

`win/build_ipa_windows.py` ejecuta el pipeline de upstream (`scripts/build_ipa_from_nsp.py`)
sin cambiarlo. Solo se sustituyen los pasos que llaman a herramientas de macOS, en el
límite del subproceso:

| Paso | Upstream en un Mac | NXNative para Windows |
|---|---|---|
| Extraer NSP / XCI (LibHac) | `nx_extract` (.NET) | el mismo, compilado con el .NET SDK para Windows |
| Reescribir los módulos del juego | `patch_nso.py` | el mismo |
| Traducir shaders (Ryujinx) | el `dmsh_xlate` nativo | el mismo traductor nativo compilado para Windows (NativeAOT), para que las huellas de la cadena sigan cuadrando con `dmsh_chain.lock` |
| Compilar las librerías de shaders | `xcrun metal` / `metallib` (Xcode) | Metal Developer Tools para Windows, a través de [`win/xcrun.py`](win/xcrun.py) (`-mios-version-min` pasa a ser `-target air64-apple-ios…`) |
| Compilar la app | `xcodegen` + `xcodebuild` | LLVM `clang -target arm64-apple-ios26.0 -isysroot iPhoneOS.sdk`, enlazado por `ld64.lld` ([`win/build_app.py`](win/build_app.py)) |
| Launcher | `Launcher.swift` (SwiftUI) | [`win/ios/Launcher.m`](win/ios/Launcher.m) (UIKit, el mismo contrato) |
| Runtime de `@available` | el compiler-rt de Apple | [`win/ios/compat_rt.c`](win/ios/compat_rt.c) |
| Icono de la app | el catálogo de recursos de `actool` | iconos PNG en `CFBundleIcons` (Pillow) |
| `sips`, `plutil`, `make -n` | herramientas de macOS | Pillow, `plistlib`, las reglas de fuentes del Makefile reproducidas (la compilación se detiene si cambian) |
| Bit de ejecución del ejecutable en el IPA | modos de Unix | `pack_ipa.py --exec` (Windows no tiene modos de Unix) |
| SDK de iPhoneOS | dentro de Xcode | [`win/sdk/extract_xip.py`](win/sdk/extract_xip.py) lee `Xcode.xip` (xar → pbzx → cpio), incluido el archivo deduplicado de Xcode 27, cuyos enlaces duros llevan marcadores `NULLcanary` |
| Shaders GL de ejecución de los juegos LÖVE | arrancar el juego en el host de Mac (`DM_GL_CAPTURE`) | [`win/love_shaders.py`](win/love_shaders.py) monta el mismo GLSL fuera de línea desde el Lua que love-nx incrusta en `main`. Los valores por defecto de LÖVE coinciden byte a byte con la tabla de captura de upstream, y las 31 claves que pidió una ejecución en un iPad coinciden. |
| Comprobación del heap de un juego nuevo | arrancarlo en el host de Mac | una estimación: un pool de aplicación de 2 GB para los juegos con memoria de direcciones virtuales, estampado en el perfil |
| Cortes de regiones de direcciones para un build `sdk` sin registrar | añadidos a mano por build ID | [`win/sdk_auto_cuts.py`](win/sdk_auto_cuts.py) los encuentra en el código (las cargas de node-area del constructor de `AddressRegionManager` y la alineación de 1 GB), solo cuando la coincidencia es única |

[`win/pyshim/sitecustomize.py`](win/pyshim/sitecustomize.py) se carga en cada Python que
arranca el pipeline. Mapea `xcrun`, `dmsh_xlate` (al `.exe` nativo), `nx_extract`, `which`, `python3` y `bash build_ipa.sh` a
sus equivalentes de Windows, y hace seguro `ctypes.CDLL(None)`. Las notas técnicas están en
[win/README.md](win/README.md).

## Qué juegos compilan en Windows

Upstream lista unos 65 juegos jugables en su [tabla de juegos](dm/games/README.md#games), con
la versión probada de cada uno. En Windows:

- **La mayoría compila como en un Mac.** Ejemplos: Super Mario Bros. Wonder, Super Mario
  Odyssey, Mario Kart 8 Deluxe, Zelda: Breath of the Wild y Tears of the Kingdom.
- **Los juegos de LÖVE** (Balatro) compilan: sus shaders de ejecución se reconstruyen fuera de
  línea.
- **Los juegos cuyos shaders solo existen en ejecución** (Fire Emblem: Three Houses y Portal con
  GLSLC, Super Mario Galaxy 1 y 2 con Vulkan) se capturan **en tu dispositivo**, igual que
  upstream los captura en un Mac:
  1. La primera compilación empaqueta `<Juego>-capture.ipa` (sin librerías de shaders; su
     `dm/env.txt` activa la captura del host) y se detiene con las instrucciones.
  2. Instálala y juega hasta la pantalla de título, y espera un minuto. Puede no haber imagen,
     porque el juego todavía no tiene shaders. El host guarda en *Documents* de la app todos
     los shaders que el juego compila.
  3. En la app *Files*, copia la carpeta (`glslc_capture` o `vk_capture`) junto a los archivos
     del juego en el PC, y compila otra vez. La compilación la contrasta con la tabla del
     perfil y hace el IPA de verdad.
- **Los juegos de Oodle, Unreal y LZ5** (Octopath Traveler 0 / II, Bayonetta 3, ASTRAL CHAIN,
  Pokémon Legends: Z-A, DRAGON QUEST XI S, FINAL FANTASY RESONANCE) decodifican sus archivos
  de shaders con el decodificador del propio juego, ejecutado en una máquina ARM64 emulada
  ([`win/oodle_emu.py`](win/oodle_emu.py), [`win/arm64_emu.py`](win/arm64_emu.py)). Los 10.596
  shaders de Octopath Traveler 0 comprimidos con Oodle se decodifican así.
- **Los juegos sin perfil de upstream** (Megabyte Punch) reciben un perfil provisional deducido
  de un sondeo. El IPA es un intento y puede no arrancar hasta que se trabaja el juego
  ([docs/agents](docs/agents/README.md)).
- **Usa la versión probada.** Otra versión compila con sus propios shaders, pero los arreglos
  hechos para la compilación probada (los parches de 60 fps y otros) no se aplican, y la
  compilación lo dice.

## Juegos de Switch 2

Los juegos de Switch 2 los soporta el propio motor: NVN2 y Ounce (Ampere) traducidos a Metal,
el front end de shaders de Ampere y los contenedores `.nup`, que no necesitan `prod.keys`. Un
juego de Switch 2 se compila desde una carpeta (`base/`, `updates/`, `dlc/`) o desde un
archivo `.nup`:

```
python win\build_ipa_windows.py "C:\Juegos\MiJuego.nup" --allow-other-metal
```

`--allow-other-metal` hace falta en Windows: el compilador de Metal de ahí es
`metalfe-custom-windows` (32023.850) y el motor solo acepta por defecto el de Xcode 27.2
(32023.922).

Sus shaders son los caros: los 131.382 de Pokopia tardaron ~1 h en traducirse y ~10 h en
compilarse en un PC de 12 hilos. La guía [NX2Apple y Switch 2](docs/ca-ninapple/NX2APPLE-SWITCH2.md)
tiene el flujo completo: el pin del motor, la reconstrucción del traductor que el lock file
necesita en Windows, y lo que pide el perfil de cada juego.

## Compilar en Linux

El mismo driver, `win/build_ipa_windows.py`, también funciona en Linux. Allí llama al LLVM
nativo (clang y ld64.lld, versión 20 o posterior), al .NET SDK 10, a spirv-cross y a zstd, y
arranca el `metal.exe` y el `metallib.exe` de Apple a través de Wine ([`win/toolchain.py`](win/toolchain.py)
`cmd()`). Se probó en Pop!_OS (base Ubuntu 24.04) con Wine 9.0, LLVM 23.1.4 y .NET SDK
10.0.403, compilan Pokémon Legends: Arceus 1.0.2 desde un perfil provisional, que jugó en
game en un iPhone 16. [win/LINUX.md](win/LINUX.md) tiene la instalación, el lock de la cadena
de shaders en Linux, la compilación, la instalación desde Linux y los problemas de Linux que
resuelve el port.

## Problemas

| Mensaje o síntoma | Qué hacer |
|---|---|
| `doctor.py` muestra `MISSING` | Instala lo que dice su línea `get it:` o pon su ruta en `win\toolchain.json`. |
| `this game compiles … shaders only at run time; they are captured on your device` | Sigue los tres pasos que da el mensaje: instala el IPA de captura, juega hasta la pantalla de título, copia la carpeta de captura junto a los archivos del juego y compila otra vez. |
| `[RED] this IPA uses vX, which game profile … was not brought up on` | Pon en la misma carpeta la actualización que nombra la tabla de juegos de upstream y compila otra vez. |
| `[RED] provisional game profile …` | El juego no tiene perfil de upstream: puede que el IPA no arranque. Manda el log del dispositivo (abajo). |
| La app se cierra justo después de *Play* | Abre la app **Files** → *On My iPhone/iPad* → el juego → `log.txt` (y `log.prev.txt`), y mira sus últimas líneas. [docs/agents/symptoms.md](docs/agents/symptoms.md) indexa los mensajes conocidos. |
| Un juego 3D se cierra mientras carga en un dispositivo antiguo | Allí las texturas BC se decodifican en la CPU y ocupan más memoria: firma con *Increased Memory Limit*. `log.txt` dice `BC textures: decoded on the CPU` cuando está activo ese camino. |
| El nombre o el bundle ID en el dispositivo no es el del build | Mantén el *App Name* / *Bundle ID* del build en la herramienta de firma. |
| Una etapa falló | Su log completo está en `<title ID>_build\logs\`, junto a los archivos del juego. |

## Diferencias con upstream

- **Ruta de compilación para Windows** en [`win/`](win/), y la ventana `Build-IPA-GUI.bat`. La
  misma ruta funciona en Linux ([win/LINUX.md](win/LINUX.md)).
- **Bundle ID por defecto `org.nxnativewindows.<title ID>`** en todas las rutas de compilación,
  para que estas apps se instalen junto a las compiladas por upstream.
- **Los perfiles derivados** reciben un marcador de RomFS del de su versión (Balatro v0 no
  tiene el archivo de marcador de la 1.1.3).
- **`pack_ipa.py --exec`** fija el modo del ejecutable al empaquetar en Windows.
- **`.gitattributes`** mantiene cada archivo byte a byte idéntico a upstream en Windows, y el
  shim escribe cada archivo de texto del pipeline con finales de línea LF, como en un Mac. Con
  CRLF, el host rechazaba el sello de las librerías de shaders.
- **Texturas BC en GPU sin BC** (A16 y anteriores) se decodifican en la CPU
  ([`dm/gfx/tex/bc_soft.c`](dm/gfx/tex/bc_soft.c); `DM_BC_SOFT=1` lo fuerza, `=0` lo desactiva).
- **Cortes de regiones de direcciones para builds `sdk` sin registrar** se encuentran en el
  código ([`win/sdk_auto_cuts.py`](win/sdk_auto_cuts.py)).

## Estructura del repositorio

| Ruta | Qué es |
|---|---|
| `Build-IPA-GUI.bat` | arranca la ventana |
| `win/gui.pyw` | la ventana (Tkinter, negra y rosa) |
| `win/build_ipa_windows.py` | el driver de Windows alrededor del script de NSP de upstream |
| `win/build_app.py` | la compilación de la app que sustituye a `build_ipa.sh` / Xcode |
| `win/xcrun.py`, `win/toolchain.py` | el sustituto de `xcrun` y el localizador de herramientas |
| `win/pyshim/sitecustomize.py` | el shim de subprocesos que carga cada Python del pipeline |
| `win/ios/Launcher.m`, `win/ios/compat_rt.c` | el launcher en UIKit y el runtime de `@available` |
| `win/love_shaders.py` | los shaders de ejecución de LÖVE, fuera de línea |
| `win/sdk_auto_cuts.py` | cortes de regiones de direcciones para builds `sdk` sin registrar |
| `win/sdk/extract_xip.py` | el SDK de iPhoneOS desde `Xcode.xip` |
| `win/doctor.py`, `win/compile_check.py` | comprobación de la cadena de herramientas; compilar todas las fuentes de la app sin archivos de juego |
| `win/tests/test_win.py` | pruebas unitarias de las partes de Windows |
| `win/TUTORIAL.md` | la guía paso a paso en indonesio |
| `win/LINUX.md` | compilar en Linux, paso a paso |
| `win/README.md` | notas técnicas del port |
| todo lo demás | el nxnative de upstream ([README.nxnative.md](README.nxnative.md), [docs/development.md](docs/development.md)) |

Archivos locales que git ignora: `win/toolchain.json`, `win/gui_settings.json`, `win/sdk/out/`
(el SDK extraído) y `win/build/`.

## Actualizar desde upstream

Última sincronización con [seedds/nxnative](https://github.com/seedds/nxnative) el 2026-10-27
(135 commits de upstream: el perfil de Kirby and the Forgotten Land, la extracción de la
imagen de RomFS, la comprobación de región, el contrato más nuevo del launcher, y más). La
sincronización anterior, el 2026-10-26 (46 commits de upstream), trajo el escalado con
MetalFX y el launcher de una pantalla, los archivos de pipelines sin conexión, el paso de
preparación, las pipelines híbridas, Pokémon Shield y Brilliant Diamond, Echoes of Wisdom
1.1.0 y los límites de fps por temperatura. El archivo de pipelines sin conexión
(`DM_PSO_GPUS`, por defecto en los juegos cuyo perfil pone `pso_mtl4`) también compila en
Windows: Metal Developer Tools for Windows trae `metal-tt`.

```
git remote add upstream https://github.com/seedds/nxnative.git
git fetch upstream
git merge upstream/main
python win\tests\test_win.py
python win\compile_check.py
```

`win/build_app.py` comprueba las reglas de fuentes del `dm/host/Makefile` y se detiene con un
mensaje claro cuando upstream las cambia. Las funciones que envuelve el driver también
pueden cambiar sus argumentos en upstream; después de una fusión, contrástalas con
`scripts/build_ipa_from_nsp.py` antes de la primera compilación. Cuando una fusión traiga
una compilación nueva del traductor, deja en `dm/gfx/tools/dmsh_chain.lock` las líneas de las
nativo de upstream y las de spirv-cross y Metal de este port, y ejecuta luego
`dmsh_chain.py --header`.

## Créditos y licencia

- **[seedds/nxnative](https://github.com/seedds/nxnative)** y todo lo que hay detrás:
  [d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile), Ryujinx, Atmosphère, yuzu, LibHac,
  SPIRV-Cross, glslang, deko3d y las librerías de `dm/third_party` (ver
  [README.nxnative.md](README.nxnative.md#acknowledgements)).
- El **Metal Developer Tools for Windows** de Apple y el SDK de iPhoneOS los descarga cada
  usuario bajo los términos de Apple y no forman parte de este repositorio.
- **[LLVM](https://llvm.org/)** (clang, ld64.lld) compila la app en Windows y en Linux, y
  **[Wine](https://www.winehq.org/)** hace correr el compilador de Metal de Apple en Linux.
- El soporte de Linux, por [amansingh909](https://github.com/amansingh909).

Licencia MIT, como upstream ([LICENSE](LICENSE)).

## Aviso legal

Esta es una herramienta de desarrollo independiente y no oficial para interoperabilidad y
investigación de preservación. No está afiliada, respaldada ni patrocinada por Nintendo,
Apple ni ninguna editora. Todas las marcas y los títulos de los juegos son de sus Owners y se
nombran solo para describir la compatibilidad; las portadas se muestran solo para
identificación.

Este repositorio no contiene juegos, archivos de juego, llaves, firmware ni ningún medio de
evadir la protección de copia. Tienes que aportar archivos extraídos por ti mismo de un
hardware y un software que te pertenecen legalmente. No uses este proyecto para obtener o
compartir material con derechos de autor, ni abras issues pidiendo archivos de juego o llaves.
