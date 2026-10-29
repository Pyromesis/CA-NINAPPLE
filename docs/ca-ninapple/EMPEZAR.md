# Empezar en Windows: del NSP al IPA

Esta guía es el camino corto. El manual completo (en inglés, con todas las opciones y el
funcionamiento interno) está en [`../../README.md`](../../README.md).

## 1. Lo que necesitas

| Cosa | Detalle |
|---|---|
| PC | Windows 10 u 11 de 64 bits, con ~2× el tamaño de tus NSP + 10 GB libres |
| iPhone / iPad | iOS / iPadOS 26 o posterior, chip **A17 Pro o superior** (iPhone 15 Pro en adelante) o iPad con **M1 o superior**: las texturas vienen comprimidas en BC y solo esos chips las leen en la GPU |
| Juego | tu propio volcado (NSP, XCI, NSZ o XCZ): base, y actualización/DLC si los tienes |
| Llaves | tu propio `prod.keys` |
| Apple ID | gratis, para descargar dos cosas de Apple y para firmar |

## 2. Instalación (una sola vez)

```powershell
winget install --id LLVM.LLVM -e
winget install --id Microsoft.DotNet.SDK.10 -e
winget install --id KhronosGroup.VulkanSDK -e
winget install --id Meta.Zstandard -e
python -m pip install lz4 capstone fonttools pillow "backports.zstd; python_version < '3.14'"
```

Python 3.10 o posterior desde [python.org](https://www.python.org/downloads/), marcando
**Add python.exe to PATH**.

De [developer.apple.com/download](https://developer.apple.com/download/all/) (con tu Apple ID):

1. **Metal Developer Tools for Windows** (5.x o 6.x). Instálalo donde quieras.
2. **Xcode 26 o 27** (`Xcode_27.1.xip`, ~2 GB). Solo se usa su SDK de iPhoneOS. Se extrae una vez:

```powershell
python win\sdk\extract_xip.py E:\ProjectIOS\Xcode_27.1.xip
```

El SDK queda en `win\sdk\out\iPhoneOS.sdk`. También vale copiar `iPhoneOS.sdk` de un Mac.
El acuerdo de licencia de Xcode y de los SDK de Apple cubre estos archivos: léelo antes de
usarlos en hardware que no es de Apple.

Comprueba que todo está en su sitio:

```powershell
python win\doctor.py
```

Cada línea `MISSING` dice qué falta y de dónde bajarlo; también puedes fijar su ruta en
`win\toolchain.json` (ese archivo no se sube al repositorio).

## 3. Preparar el juego

Una carpeta por juego, con el NSP base dentro (y la actualización y los DLC si los tienes,
en la misma carpeta). Por ejemplo:

```
C:\Juegos\BALLxPIT\
    BALL x PIT [010086A022444000][v0][Base].nsp
    prod.keys          <- el tuyo; no se comparte ni se sube
```

## 4. Compilar

```powershell
python win\build_ipa_windows.py "C:\Juegos\BALLxPIT" -k "C:\Juegos\BALLxPIT\prod.keys"
```

El IPA aparece en esa misma carpeta. Al lado queda `<title ID>_build\`, que se reutiliza en
la siguiente compilación (caché de shaders), y dentro `logs\` con el log completo de cada etapa.

La primera compilación de un juego compila **todos** sus shaders con el compilador Metal de
Windows: cuenta entre varios minutos y media hora según el juego y la CPU. Las siguientes
tardan segundos o minutos.

Opciones útiles (todas las de upstream con `-h`):

| Opción | Efecto |
|---|---|
| `-o D:\out\Juego.ipa` | dónde se escribe el IPA |
| `--app-name "Nombre"` | nombre en la pantalla de inicio |
| `--bundle-id com.tu.juego` | otro identificador (por defecto `org.nxnativewindows.<title ID>`) |
| `-l es` | idioma del juego que se empaqueta |
| `--show-fps` / `--no-show-fps` | contador de FPS por defecto |
| `--split-data` | IPA pequeño + carpeta de datos (ver abajo) |
| `--entitlements` | firma ad-hoc pidiendo **Increased Memory Limit** |

### Compilación partida (IPA pequeño + carpeta de datos)

Firmar e instalar 3 GB cada 7 días con un Apple ID gratis es incómodo. Con `--split-data`:

- `Juego.ipa`: solo la app (unos MB).
- `Juego-data\`: `romfs\`, `msl\` (las librerías de shaders) y `aoc\`, enlazados con hard links
  (no ocupan más disco).

Instalas el IPA, abres la app una vez (avisa de que faltan los datos) y copias la carpeta
`Juego-data` entera dentro de *Documentos* de la app, con la app **Files** o con el panel de
LiveContainer. Al volver a abrir, el juego arranca.

## 5. Instalarlo en el iPhone

Sigue [`IPHONE.md`](IPHONE.md).

## 6. Si algo falla

[`PROBLEMAS.md`](PROBLEMAS.md) empieza por los síntomas: pantalla negra con música, cierre al
arrancar, avisos `[RED]` del compilador y qué mirar en `Documents/log.txt`.
