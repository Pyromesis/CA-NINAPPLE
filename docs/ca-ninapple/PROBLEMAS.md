# Problemas y cómo diagnosticarlos

## Dónde mirar

| Qué | Dónde |
|---|---|
| Log de la compilación | `<title ID>_build\logs\` (una etapa por archivo) y la consola |
| Log del juego en el iPhone | *Documentos* de la app → `log.txt` (y `log.prev.txt`) |
| Ajustes del juego | *Documentos* → `env.txt` |
| Partidas | *Documentos* → `save/` |

Empieza siempre por el **final** de `log.txt`: ahí está lo que pasó justo antes de cerrarse.

## Tabla rápida

| Síntoma | Qué suele ser | Qué hacer |
|---|---|---|
| Se oye la música pero la pantalla está negra | No hay shaders traducidos: el juego dibuja con programas que no están en el mapa | Mira `shader split: N shaders` en el log de build y `[RED] shader ... is not in the shader map` en `log.txt`. Ver [Pantalla negra](#pantalla-negra-con-música) |
| Se cierra solo al arrancar | iOS lo mata por memoria | Firma con **Increased Memory Limit**; comprueba `boot: memory limit` en `log.txt` |
| Se cierra al cargar una fase | Memoria o un recurso que el host aún no traga | Últimas líneas de `log.txt`; prueba `--split-data` y baja *Render scale* |
| `[RED] this IPA uses vX (…), a version game profile … was not brought up on` | El perfil registrado es de otra versión | Es un aviso, no un error: el IPA usa un perfil derivado. La ruta soportada es poner la actualización que el perfil espera en la carpeta del juego |
| `doctor.py` muestra `MISSING` | Falta una herramienta | Instala lo que dice su línea `get it:` o fija la ruta en `win\toolchain.json` |
| La app se llama distinto o el bundle ID no es el del build | El firmador los sobreescribió | Mantén el nombre y el bundle ID del build en la herramienta de firma |
| Va lento, se calienta y baja de FPS | GPU al límite | *Render scale* al 75 %, *Console mode: Handheld*, *Upscaling: Standard* |
| El build muere con `a split build copies the RomFS as a folder…` | El XCI se extrajo como una sola `RomFS.img` | Usa `--romfs separate` (`-RomfsSeparate`). Ver [El build partido falla con un XCI grande](#el-build-partido-falla-con-un-xci-grande) |
| `UnicodeEncodeError` con `'\u2713'` | Consola de Windows en cp1252 | `build.ps1`, o `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8`. Ver [UnicodeEncodeError al imprimir el progreso](#unicodeencodeerror-al-imprimir-el-progreso) |
| `ios install` termina con `ExtractionFailed` | El firmador dejó el ejecutable en `0644` | `python win\fix_ipa_mode.py <IPA firmado>` y reinstala. Ver [La instalación falla con ExtractionFailed](#la-instalación-falla-con-extractionfailed) |

## Pantalla negra con música

Es el fallo clásico de un juego Unity: el audio (FMOD) suena, pero nada se dibuja porque los
programas que el juego pide no están en el **shader map** del IPA.

1. En el log de build busca la línea de la etapa 5:

   ```
   ✓ [5/8] shader split (0:05): 22,313 shaders
   ```

   Un juego Unity grande tiene miles o decenas de miles. Si pone **11**, o un número
   sospechosamente pequeño, el split no está leyendo los assets del juego.

2. En `log.txt` del dispositivo busca:

   ```
   [RED] shader <clave> is not in the shader map
   ```

   Cada línea es un programa que el juego pidió y el IPA no trae.

### El caso de BALL x PIT v0 (1.251)

Síntoma: música, pantalla negra, y el build decía `shader split: 11 shaders`.

Causa: en Windows, `dm/tools/romfs.py` abría `RomFS.img` **sin `O_BINARY`**. El runtime de C
trata entonces el archivo como texto y **se detiene en el primer byte `0x1A`** (Ctrl-Z). En
`Data/sharedassets1.assets` ese byte cae en el offset 78, así que cada `.assets` se leía como
un trozo de 78 bytes, `is_serialized()` decía que no era un archivo de Unity y el split se
quedaba solo con los 11 shaders que hay dentro de `main`.

Arreglado en este repositorio (`O_RDONLY | O_BINARY` y una prueba de regresión con `0x1A` y
CRLF). Con el arreglo salen **552 objetos `Shader` + 19 `ComputeShader`** y **22.313
programas** para BALL x PIT v0.

Cómo saber si tu copia es la antigua: si el log dice 11 shaders en un juego Unity con
`sharedassets1.assets` de cientos de MB, es la antigua. Actualiza y vuelve a compilar; la
caché se invalida sola al cambiar las herramientas.

## Perfiles derivados (`this IPA uses vX…`)

El perfil de un juego está atado a **una** versión concreta (la que se probó). Si compilas
otra, el script deriva un perfil: copia las llaves del registrado, pone la fila de compilación
de tu versión y construye las tablas con **tus** archivos. El aviso `[RED]` es para que no se
te olvide que esa combinación no está probada.

Qué implica:

- Los cortes de direcciones del `sdk` se buscan por código (`win/sdk_auto_cuts.py`), no por
  dirección fija. Si no encuentra un corte, lo dice.
- Las tablas de shaders se generan de los archivos de tu versión, así que un Unity con el
  mismo formato funciona igual (BALL x PIT v0 usa el mismo layout `2ec7223d…` que 1.293).
- Aun así, puede haber diferencias de comportamiento que solo se ven jugando.

Si tienes la versión registrada, úsala: es la ruta con la que el juego se probó.

## El build partido falla con un XCI grande

Síntoma, al final de una compilación larga (extracción y shaders ya hechos):

```
FAIL: a split build copies the RomFS as a folder, and this extraction is one RomFS image (RomFS.img): build without --split-data
```

Causa: al extraer un **XCI**, el RomFS queda como **una sola imagen**
(`<title ID>_build\extract\vX\RomFS.img`), que es lo que lee el host. `--split-data` construye
la carpeta de datos copiando el RomFS archivo por archivo, así que el empaquetador de Windows
(`win/build_app.py`) rechazaba esa combinación en vez de partir la imagen.

Solución: usa **`--romfs separate`**, no `--split-data`. El IPA se queda pequeño (app y
shaders) y el RomFS se copia **una vez** a `Documents/romfs.img`:

```powershell
.\build.ps1 -Game "C:\Juegos\TotK" -RomfsSeparate
```

Sin el script:

```powershell
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
python win\build_ipa_windows.py "C:\Juegos\TotK" -k "C:\Juegos\TotK\prod.keys" --romfs separate
```

Por qué este modo y no la carpeta: un RomFS así ronda los **300.000 archivos** (Tears of the
Kingdom: 304.000, 17 GB). Copiarlos uno a uno por el servicio de archivos del iPhone agota los
descriptores abiertos; una imagen se copia de una vez y se puede verificar entera.

Qué cambia en el IPA:

- El RomFS **no** va dentro. En su lugar la app lleva `romfs.id`, con el tamaño y el hash del
  índice de la imagen (`dm/tools/romfs_image.py --identity`).
- Al arrancar solo acepta un `Documents/romfs.img` con esa identidad. Si es de otra versión o
  la copia se cortó, lo dice en `log.txt` (`[RED] boot: …`) y con un aviso en pantalla, y no
  usa datos incorrectos.
- Los shaders (`msl/`) sí van dentro del IPA: no hay que copiarlos aparte.

El arreglo está en [`win/build_app.py`](../../win/build_app.py): `--romfs separate` activa
`DM_COPY_ROMFS=NO` en el pipeline, y el port de Windows ahora lo respeta. Antes lo ignoraba y
volvía a meter el RomFS; la única forma de evitarlo era `--split-data`, que es justo lo que
falla con una imagen. El modo se reutiliza: si el build falla al empaquetar, relanzarlo conserva
la extracción y los shaders ya compilados.

Copia la imagen con la app ya instalada: en Windows sirve `ios fsync` (go-ios) o el panel de
archivos de LiveContainer; el archivo debe llamarse **`romfs.img`** dentro de *Documentos* de la
app. En macOS, `scripts/push_romfs.sh <UDID> <bundle ID> "<...>\RomFS.img"`.

### Nombres de archivo que el build necesita

El build identifica cada paquete por el **nombre**:

| Archivo | Etiqueta | Por qué |
|---|---|---|
| Base `.xci` | `[0100F2C0115B6000]` | un XCI no trae ticket; el título sale de la etiqueta de 16 hex |
| Actualización `.nsp` | `[v655360]` | la versión sale de `[vN]`; el ticket da el título, no la versión |

```text
The Legend of Zelda Tears of the Kingdom [0100F2C0115B6000][v0][Base].xci
The Legend of Zelda Tears of the Kingdom [0100F2C0115B6800][v655360][UPD].nsp
```

Sin la etiqueta, el archivo se ignora o se toma por otro paquete. El número de la actualización
es la versión en decimal: `1.4.2` es `655360`; `1.4.3` es `720896`.

## La instalación falla con `ExtractionFailed`

Síntoma al instalar el IPA firmado:

```
{"level":"ERROR","msg":"failed writing","err":"invalid progressUpdate, missing InstallProgressDict field:+map[Error:ExtractionFailed]"}
```

Causa: algunos firmadores reconstruyen el ZIP y escriben **todos** los archivos con modo `0644`,
incluido el ejecutable principal. iOS extrae `Payload/<App>.app/<App>` con el modo Unix que hay
en el directorio central del ZIP; si no tiene permiso de ejecución, cancela la instalación.

Compruébalo sin instalar:

```powershell
python -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); i=z.getinfo('Payload/DmIOS.app/DmIOS'); print(oct(i.external_attr>>16))" "ruta\Juego-signed.ipa"
```

Si sale `0o100644`, es esto. Repara el IPA (solo cambia los atributos del ZIP; la firma de
dentro no se toca) y vuelve a instalar:

```powershell
python win\fix_ipa_mode.py "ruta\Juego-signed.ipa"
ios install --path "ruta\Juego-signed.ipa"
```

El script lee `CFBundleExecutable` del `Info.plist` y pone `0755` en el binario principal. Es
idempotente: si ya está bien, no cambia nada.

Antes de esto puede aparecer un fallo distinto, `failed writing … Read: failed to read message
length: EOF`: es una conexión que se cortó (pantalla bloqueada o cable). Reintenta con el iPhone
desbloqueado.

## UnicodeEncodeError al imprimir el progreso

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 11: character maps to <undefined>
```

Una consola de Windows en cp1252 no puede escribir el `✓` del progreso. No es un fallo del
build: la extracción y los shaders ya hechos quedan en caché. Usa `build.ps1`, que fuerza
UTF-8, o define las variables antes de llamar al driver:

```powershell
$env:PYTHONUTF8 = '1'; $env:PYTHONIOENCODING = 'utf-8'
```

## Memoria

`log.txt` dice al arrancar:

```
boot: memory limit 6000 MB
```

- ~3375 MB: la firma no pidió **Increased Memory Limit**.
- ~6000 MB: correcto en un iPhone reciente.

Si el juego muere justo después de esa línea, o al entrar a una fase, es memoria. Prueba
`--split-data` (los datos no van dentro de la app), *Render scale* más bajo y *Handheld*.

## El juego no arranca y `log.txt` está vacío

- La app se cerró antes de que el host escribiera: firma, *Modo desarrollador* o el propio
  iOS. Revisa el log del sistema o vuelve a firmar.
- En LiveContainer, comprueba que estás mirando los *Documentos de la app del juego*, no los
  de LiveContainer.

## Recopilar un informe

```powershell
python scripts\bug_report.py "C:\Juegos\BALLxPIT" --ios-log "C:\ruta\a\log.txt"
```

Recoge la versión del host, el perfil, el registro de la compilación y el `log.txt` que le
indiques, en un zip. **Revisa lo que adjuntas**: no incluyas `prod.keys`, NSP ni capturas con
datos personales. El script solo lee una lista blanca de archivos y tacha las rutas de tu
usuario, pero la última palabra es tuya.
