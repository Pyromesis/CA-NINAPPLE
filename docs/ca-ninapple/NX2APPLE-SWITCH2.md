# NX2Apple y los juegos de Switch 2 en Windows

Estado a 6 de noviembre de 2026. Este documento explica qué es
[NX2Apple](https://github.com/LNPANDY/NX2Apple), qué parte sirve en un PC con
Windows, qué hay que instalar y qué se puede esperar de rendimiento.

## Qué es y de dónde sale el soporte de Switch 2

NX2Apple **no es un emulador ni un motor**: es un *launcher* (una app de
escritorio) que hace de interfaz para [nxnative](https://github.com/seedds/nxnative).
El trabajo real —reescribir los módulos del juego, el host de Horizon, NVN sobre
Metal y el perfil de cada juego— está en **nxnative**.

El soporte de **Switch 2** también está en el motor, no en el launcher:

| Pieza | Dónde está |
|---|---|
| GPU NVN2 / *Ounce* (Ampere) traducida a Metal | `dm/gfx/nvn/`, `dm/gfx/tools/dmsh_ampere.py` |
| Shaders Ampere (SPIR-V → MSL) | `dm/gfx/tools/shader_split.py` |
| Contenedores `.nup` sin `prod.keys` | `scripts/pack_nup.py` |
| Perfiles `0400…` (Ocarina of Time, Kirby Air Riders, Pokopia, Mario Kart World…) | `dm/games/` |

La rama `main` de nxnative recibe versiones nuevas casi a diario. El *pin* que
usa NX2Apple 1.2.3 es `88c7e03f51e3`; el motor integrado aquí
(`C:\Users\berna\nxw\NX2Apple-engine`, rama `switch2-engine`) parte de
`c229bd7d`, **6 commits por delante y 0 por detrás** de ese pin, así que ya
incluye todo lo que trae NX2Apple y las correcciones posteriores.

## Qué hay que instalar

### En este PC (Windows), para compilar IPAs con el motor nuevo

Nada nuevo si ya compilas IPAs de Switch 1 en este equipo. `python win\doctor.py`
del motor nuevo comprueba lo mismo de siempre y hoy sale todo en `[ok ]`:

| Herramienta | Estado en este PC |
|---|---|
| Python 3.13 con `lz4`, `capstone`, `fonttools`, `Pillow`, `zstd` | instalado |
| .NET SDK 10 (extractor `nx_extract`) | 10.0.400 |
| LLVM `clang` + `ld64.lld` | instalado |
| SDK de iPhoneOS 27.1 (extraído de Xcode) | `C:\Users\berna\nxw\nxnative-win\win\sdk\out\iPhoneOS.sdk` |
| Compilador Metal para Windows (`metal.exe`, `metallib.exe`) | instalado |
| `spirv-cross`, `glslangValidator`, `zstd` | instalados |
| Traductor `dmsh_xlate.dll` | en el propio repo |

Para un juego de Switch 2 **no hace falta `prod.keys`**: los `.nup` y las
 carpetas `base/updates/dlc` van sin cifrar. Para Switch 1 sigue haciendo falta
el `prod.keys` de tu consola.

### Si prefieres el launcher oficial

NX2Apple publica `NX2Apple-windows-x64.zip` (unos 217 MB) en sus *releases*.
Es la vía con interfaz gráfica; el motor que lleva dentro es el mismo nxnative
con su pin y sus parches. El zip trae 5.695 archivos: `NX2Apple.exe`, PySide6 y
Python 3.12 embebidos en `_internal`, 14 *wheels*, y el motor completo en
`engine` (500 MB, 3.126 archivos). No trae compiladores ni SDK.

El propio launcher tiene su capa Windows (`_internal/nspb_qt/win/`): `doctor`,
`fetch`, `sdk_fetch`, `build_app`, `macho_sign`, `fix_ipa_modes`, `shim`
(`xcrun`/`xcodebuild` falsos) y `mp_worker`. Se usa desde la GUI o desde consola:

```powershell
python -m nspb_qt.win.doctor              # qué falta
python -m nspb_qt.win.doctor --fix        # baja LLVM-MinGW fijado
python -m nspb_qt.win.doctor --sdk        # baja el SDK de iPhoneOS (git xybp888/iOS-SDKs)
python -m nspb_qt.win.doctor --sdk-xip Xcode.xip
python -m nspb_qt.win.doctor --import-sdk D:\SDKs\iPhoneOS26.0.sdk
```

Qué instala solo y qué no:

| Componente | Launcher oficial |
|---|---|
| LLVM/clang + `ld64.lld` (LLVM-MinGW fijado; renombra `ld.lld.exe`) | lo descarga con `--fix` |
| SDK de iPhoneOS 26+ (hace falta Metal 4) | lo descarga con `--sdk` (o lo importas) |
| Metal Developer Tools para Windows (`metal.exe`, `metallib.exe`) | **manual**, con Apple ID |
| .NET 10 (para `nx_extract` y `dmsh_xlate`) | **manual** |
| `zstd` | obligatorio; la GUI lo descarga, por consola hay que ponerlo a mano |
| `spirv-cross`, `glslangValidator` | vienen en `engine/dm/gfx/tools/spirv_cross_bin` |
| Fuente Unicode (`STD_FONT`) | opcional, cualquier TTF amplio |

`metal-tt` (el archivador de pipelines) no viene en las herramientas Metal de
Windows, así que el archivo de pipelines offline queda desactivado en esa vía.

En macOS pide macOS 13 o superior, Xcode 27.2 con el SDK de iOS y el .NET SDK 10.

## Rendimiento: qué mejora y qué no

- **Juegos de Switch 1**: el motor nuevo no es “más fps” por sí solo. Lo que
  cambia son 465 commits de correcciones del host (mando por jugador, tablas de
  uniform buffers, servicios de captura, encadenado de shaders, pipelines de
  Metal 4…). Algunas quitan trabajo por fotograma y otras arreglan dibujado; la
  ganancia concreta depende del juego y aquí no se ha medido.
- **Juegos de Switch 2**: es soporte nuevo, no una optimización. El juego corre
  nativo sobre la GPU de Apple con NVN2 traducido a Metal. Las notas de nxnative
  (en Mac) dan **60 fps en Kirby Air Riders**, **unos 59 fps en Ocarina of Time
  (Switch 2)** y **unos 60 fps en Pokopia**; en iPhone no hay pruebas publicadas.
- El límite en iPhone será la **memoria**: el perfil de Pokopia pide 9 GB
  (`mem_reserve 0x270000000`, `app_pool 0x240000000`), el mismo esquema que
  Donkey Kong Bananza. Si el juego no cabe, iOS lo cierra al arrancar.
- **Tiempo de compilación**: los juegos de Switch 2 son el caso más caro de la
  cadena, porque sus shaders (Ampere SM86) son mucho más grandes. Pokopia
  (131.382 shaders) tardó **58 min en traducirlos** y **unas 10 h en compilarlos
  con Metal** en un equipo de 12 hilos; el resto del pipeline son minutos. Las
  medidas y lo que sí acelera están en
  [COMPILAR-RAPIDO.md](COMPILAR-RAPIDO.md).

## Cómo se compila con este repo

La capa Windows vive en la rama `switch2-engine` del worktree
`C:\Users\berna\nxw\NX2Apple-engine` (no en `main`, que sigue con el motor
estable). Desde esa carpeta:

```powershell
$env:PYTHONUTF8='1'
python win\build_ipa_windows.py "C:\ruta\al\juego" --allow-other-metal          # carpeta con base/, updates/, dlc/
python win\build_ipa_windows.py "C:\ruta\al\juego.nup" --allow-other-metal      # contenedor NUP de Switch 2
```

`--allow-other-metal` es obligatorio en Windows: el compilador Metal del port es
`metalfe-custom-windows` (32023.850) y el motor solo acepta por defecto el de
Xcode 27.2 (32023.922). Sin la opción, cualquier juego NVN se detiene antes de
traducir shaders con `[RED] this Mac's Metal compiler is not the one the shaders
were tested with`. Es el mismo interruptor documentado por el motor
(`ALLOW_OTHER_METAL` / `--allow-other-metal`).

### Si el build se para en `translation chain tools do not match the lock file`

El lock (`dm/gfx/tools/dmsh_chain.lock`) guarda las huellas del traductor, de
`spirv-cross` y de los compiladores Metal **de macOS**. En Windows el traductor
y `spirv-cross` son otros binarios, así que un repo recién clonado se detiene en
`[4/6] iOS shaders` con:

```
[RED] translation chain tools do not match the lock file: spirv-cross: lock e37945d8e441d34d / actual 6702f1d74b2aaff0
[RED] translation chain tools do not match the lock file: the translator was not built from the in-repo source:
      embedded source 0bd66426675438a9 / in repo f08e2efd04100435 (rebuild dmsh_xlate)
```

No es un fallo del juego: hay que reconstruir el traductor con el fuente del repo
y apuntar el lock a las herramientas nativas. En este PC:

```powershell
cd C:\Users\berna\nxw\NX2Apple-engine
dotnet publish dm\gfx\tools\dmsh_xlate\dmsh_xlate.csproj -c Release -f net10.0 -o "$env:TEMP\xlate_build"
Get-ChildItem "$env:TEMP\xlate_build" -File | Where-Object { $_.Name -ne 'dmsh_xlate.exe' } |
  Copy-Item -Destination dm\gfx\tools\dmsh_xlate_bin -Force
$env:SPIRV_CROSS = 'C:\VulkanSDK\1.4.363.0\Bin\spirv-cross.exe'
python win\update_tools_lock.py
python dm\gfx\tools\dmsh_chain.py --header
```

`update_tools_lock.py` cambia solo las líneas que dependen de Windows
(`dmsh_xlate.dll`, las DLL de Ryujinx, `xlate_source` y `spirv-cross`) y deja las
de Metal, que son las de macOS con las que se probaron los shaders.
`dmsh_chain.py --header` sube la versión de la cadena (`DMSH_CHAIN`) y el host
solo carga la carpeta `b-<V>` que le corresponde, así que hay que recompilar la
app. El `spirv-cross` nativo es el del Vulkan SDK (`6702f1d7…`); el del repo
(`spirv_cross_bin/spirv-cross`) es Mach-O y no arranca en Windows.

Sin `-k` para Switch 2. El resto del flujo (firma con plumesign, instalación y
arranque) es el mismo de [INSTALAR-DESDE-PC.md](INSTALAR-DESDE-PC.md).

## Qué se tocó para que el motor nuevo compile en Windows

| Problema | Solución |
|---|---|
| `dm/tools/tree_tar.py` importa `fcntl` y abre la carpeta padre como archivo | `win/pyshim/fcntl.py` (sin `flock`) y guarda en `tree_tar.py`: sin bloqueo, el build ya va en serie |
| `dm/host/Makefile` añade `save_sync.c`, `web_apple.m`, dav1d y `host_msl` | `win/build_app.py` actualizado: lista de fuentes, includes de dav1d y generación de `host_msl_gen.h` con `dm/gfx/tools/host_msl.py` |
| `mmap` de un `.nup` vacío lanza `OSError` en Windows | `scripts/pack_nup.py` lo trata como “archivo vacío” |
| Las pruebas de NUP borran un `.nup` mapeado | `PermissionError [WinError 32]`: es de la limpieza de la prueba, no del build |
| `dm/tools/romfs.py` no encuentra los archivos dentro de `RomFS.img` | `_resolve` parte por `/` (Windows usa `\`) y `_File` usa `os.pread` (no existe en Windows): normaliza la ruta, abre con `O_BINARY` y lee con `lseek`+`read` |
| `signal.pthread_sigmask` no existe en `patch_nso.py` | `in_parallel` cae a ejecución serie en Windows (no hay pool `fork` ni `pthread_sigmask`) |
| `OSError: [WinError 87]` al escanear shaders | El resultado de un `.fdata` de KTGL (203.120 shaders, 6,3 GB) no cabe en la tubería de `multiprocessing`; en Windows el escaneo de `shader_split.py` corre en serie dentro del proceso |
| `[RED] translation chain tools do not match the lock file` / `the translator was not built from the in-repo source` | El lock guarda las huellas de macOS; el traductor y `spirv-cross` de Windows son otros binarios | `win/update_tools_lock.py` reescribe solo esas líneas (deja las de Metal) y `dmsh_chain.py --header` sube la versión. Ver [Reconstruir el traductor](#si-el-build-se-para-en-translation-chain-tools-do-not-match-the-lock-file) |

## Pendiente

- **Pokopia** (Switch 2) se llegó a compilar: la traducción de sus 131.382
  shaders se completó (58 min) y la compilación con Metal llegó al 22 %
  (28.382 shaders en 3 h 21 min) antes de pararse. No se llegó a empaquetar ni
  a probarlo en el iPhone. Los fuentes del juego y la caché de shaders se
  borraron después, así que repetirlo es desde cero: otra traducción y otras
  ~10 h de compilación. Las medidas están en
  [COMPILAR-RAPIDO.md](COMPILAR-RAPIDO.md).
- Upstream compila ese mismo juego en **~2,5 h en un M4 Pro**: la diferencia
  es sobre todo el GIL (el builder termina los shaders en hilos que comparten
  uno solo) y el número de núcleos. Upstream lo arregló el 11/11/2026
  terminando cada shader en un proceso trabajador; en Windows hay que portarlo
  porque upstream usa `fork`. Detalle en
  [COMPILAR-RAPIDO.md](COMPILAR-RAPIDO.md).
- `--seen-shaders` (compilar solo los shaders ya vistos) sigue siendo solo para
  Mac; en iOS hay que traducir el mapa completo, que en Pokopia son 131.426
  shaders.
- Las plataformas `mac` y `mac-app` se rechazan en Windows con un mensaje claro.
