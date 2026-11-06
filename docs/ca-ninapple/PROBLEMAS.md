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
| Se cierra al pulsar *Play* y `log.prev.txt` termina en `[RED] sf: the game connects to service bt itself` | El juego usa Bluetooth (`bt`), que el host no sirve | La API de Bluetooth queda inerte en el host. Ver [Se cierra al pulsar Play con Bluetooth](#se-cierra-al-pulsar-play-con-bluetooth) |
| `[RED] this IPA uses vX (…), a version game profile … was not brought up on` | El perfil registrado es de otra versión | Es un aviso, no un error: el IPA usa un perfil derivado. La ruta soportada es poner la actualización que el perfil espera en la carpeta del juego |
| `doctor.py` muestra `MISSING` | Falta una herramienta | Instala lo que dice su línea `get it:` o fija la ruta en `win\toolchain.json` |
| La app se llama distinto o el bundle ID no es el del build | El firmador los sobreescribió | Mantén el nombre y el bundle ID del build en la herramienta de firma |
| Va lento, se calienta y baja de FPS | GPU al límite | *Render scale* al 75 %, *Console mode: Handheld*, *Upscaling: Standard* |
| El personaje va más rápido de lo normal (Zelda) | El IPA es de una versión del juego sin los parches del frame step, y el host fija los presentes a 30 o 60 | Pon `DM_FPS_TARGET=0` en `Documents/env.txt` o elige *Game's own* en *Frame rate*. Ver [Va más rápido de lo normal](#va-más-rápido-de-lo-normal) |
| Mario Kart 8 va al doble de velocidad pero el contador marca 60 | *Performance → Frame order* en **Newest**: el display link descarta los frames viejos y el juego corre por delante | Ponlo en **In order** (`DM_PRESENT_FIFO=1`, el valor por defecto). Ver [Mario Kart 8: Frame order](#mario-kart-8-frame-order-en-newest) |
| El build muere con `a split build copies the RomFS as a folder…` | El XCI o el NSP se extrajo como una sola `RomFS.img` | Usa `--romfs separate` (`-RomfsSeparate`). Ver [El build partido falla con una imagen RomFS](#el-build-partido-falla-con-una-imagen-romfs) |
| `UnicodeEncodeError` con `'\u2713'` | Consola de Windows en cp1252 | `build.ps1`, o `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8`. Ver [UnicodeEncodeError al imprimir el progreso](#unicodeencodeerror-al-imprimir-el-progreso) |
| `ios install` termina con `ExtractionFailed` | El firmador dejó el ejecutable en `0644` | `python win\fix_ipa_mode.py <IPA firmado>` y reinstala. Ver [La instalación falla con ExtractionFailed](#la-instalación-falla-con-extractionfailed) |
| `ios install` se corta **siempre a los ~2 min** con `failed writing … wsasend` en un IPA grande | El IPA lleva dentro una entrada de **más de 4 GiB** (ZIP64): el extractor del iPhone la rechaza | Saca el RomFS del IPA (`--romfs separate`) y copia `romfs.img` a *Documentos*. Ver [El IPA con una entrada de más de 4 GiB se corta a los 2 min](#el-ipa-con-una-entrada-de-más-de-4-gib-se-corta-a-los-2-min) |
| `plumesign … --udid <UDID>` dice `Device ID … not found` | Su `--udid` espera el id numérico de usbmuxd, no el UDID | `python win\usbmuxd_id.py` y pasa ese número. Ver [Instalar en un segundo iPhone](INSTALAR-DESDE-PC.md#a2b-instalar-en-un-segundo-iphone) |
| Al abrir sale «Desarrollador no confiable» | Falta confiar en el certificado de desarrollo en ese teléfono | Ajustes → General → VPN y gestión de dispositivos → Apple Development: <cuenta> → Confiar; una vez por teléfono. Abrir la app otra vez no lo arregla |
| Sale «game data needed» y no arranca | El IPA es de build partida y falta `Documents/romfs.img` | Cópialo con `ios fsync push` (17 GB en TotK). Ver [Copiar los datos del juego](INSTALAR-DESDE-PC.md#a2c-copiar-los-datos-del-juego-build-partida) |
| `ios install` falla en `PostflightingApplication` (70 %) con `maximum number of installed apps using a free developer profile` | Ya hay 3 apps instaladas con el perfil gratuito | Desinstala una con `ios uninstall <bundle>` y repite. Ver [El perfil gratuito solo deja tres apps](#el-perfil-gratuito-solo-deja-tres-apps-instaladas) |
| `ios fsync push` de `romfs.img` se corta con `framedIPv6Reader … EOF` y luego «could not connect to RSD» | El túnel de usuarios se cayó a mitad de la copia; el archivo queda a medias (`invalid RomFS image … errno=22`) | Reinicia el túnel, borra el `romfs.img` parcial y repite el push. Ver [La copia de romfs.img se corta a mitad](#la-copia-de-romfsimg-se-corta-a-mitad) |
| La tele no recibe la imagen del juego | La escena de pantalla externa no llegó a conectar | Busca `front end: TV output registered` en `log.txt`. Ver [TV y AirPlay](TV-AIRPLAY.md) |

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

## El build partido falla con una imagen RomFS

Síntoma, al final de una compilación larga (extracción y shaders ya hechos):

```
FAIL: a split build copies the RomFS as a folder, and this extraction is one RomFS image (RomFS.img): build without --split-data
```

Causa: al extraer un **XCI o un NSP**, el RomFS queda como **una sola imagen**
(`<title ID>_build\extract\vX\RomFS.img`), que es lo que lee el host; pasa también con
Pokémon: Let's Go, Pikachu!, cuya imagen ocupa 4,4 GB. `--split-data` construye la carpeta de
datos copiando el RomFS archivo por archivo, así que el empaquetador de Windows
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

## El IPA con una entrada de más de 4 GiB se corta a los 2 min

Síntoma: `ios install` se queda en `inittransfer` y a los **~2 minutos exactos**
(cuenta atrás muy constante: 1:57, 2:04, 3:21 según el tamaño) termina con:

```
{"level":"ERROR","msg":"failed writing","err":"write tcp 127.0.0.1:…->127.0.0.1:27015: wsasend: An existing connection was forcibly closed by the remote host."}
```

No es el límite de 3 apps del perfil gratuito (ese aparece más tarde, en
`PostflightingApplication` al 70 %), ni el espacio del teléfono, ni el túnel, ni la firma.
El log del **iPhone** lo dice claro:

```powershell
ios syslog --udid <UDID> *> syslog.txt   # en otra ventana, durante la instalación
```

```text
streaming_zip_conduit(StreamingZip) <Error>: Stream extractor got error:
  Error Domain=SZExtractorErrorDomain **Code=2** UserInfo={… SZExtractorFileOffsetErrorKey=4673799313 …}
streaming_zip_conduit <Error>: Failed to finish extraction: … "Connection invalidated to streaming unzip service."
```

Causa: el IPA contiene una entrada **mayor de 4 GiB** y va en ZIP64 (versión 45 en el
directorio central). El extractor en streaming de iOS 27 la rechaza; el corte llega justo
al entrar en esa entrada. En Mario Kart 8 Deluxe es `Payload/DmIOS.app/romfs.img`
(12.132.043.035 bytes) y el error cae en el byte 4.673.799.313, dentro de ella.

Comprobarlo sin instalar (dice qué entrada hay en el offset del error y cuáles pasan de 4 GiB):

```powershell
python -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); t=4673799313; print([i.filename for i in z.infolist() if i.header_offset<=t][-1]); print([(i.filename,i.file_size) for i in z.infolist() if i.file_size>0xF0000000])" "ruta\Juego.ipa"
```

El **total** del IPA no importa: Cuphead (4,58 GB, 7.749 entradas, la mayor de 3,58 GB)
se instala sin problema. Lo que rompe es una **entrada** de más de 4 GiB, y también un
repack que escriba *todas* las entradas en ZIP64 (`force_zip64` en Python).

Solución: que el RomFS no viaje dentro del IPA.

- Build nuevo: `python win\build_ipa_windows.py "<Juego>" --romfs separate`. El IPA queda en
  ~1 GB (app + `msl/`), y `romfs.img` se copia una vez a *Documentos*
  (`ios fsync` o `ios file push`, ver [Copiar los datos del juego](INSTALAR-DESDE-PC.md#a2c-copiar-los-datos-del-juego-build-partida)).
- IPA ya firmado, sin recompilar:
  1. saca `Payload/DmIOS.app/romfs.img` de la app y guárdalo;
  2. vuelve a firmar la app en el sitio: `plumesign sign --package <…\DmIOS.app> --apple-id`
     (sin `-o`: con una `.app` firma en el sitio y no reempaqueta);
  3. empaqueta el IPA **sin** `force_zip64` (todas las entradas quedan por debajo de 4 GiB;
     el ZIP64 del índice final no molesta);
  4. instala el IPA pequeño y copia `romfs.img` a *Documentos* de la app.

`plumesign device --install` **no** sirve como alternativa: con el túnel de iOS 17+ no ve el
dispositivo (`Error: Other error: Device ID … not found`).

## El perfil gratuito solo deja tres apps instaladas

Síntoma: la instalación llega al 70 % (`PostflightingApplication`) y termina con:

```
{"level":"ERROR","msg":"failed writing","err":"your app is not properly signed for this device …
 'ApplicationVerificationFailed' errorDescription:'This device has reached the maximum number of
 installed apps using a free developer profile: {(\n \"986S29SKK3.org…\",\n …)}'"}
```

No es la firma: la cuenta gratuita permite **tres apps a la vez** con perfil de desarrollo, y las
tres plazas están ocupadas. Cuentan las que están instaladas, no las que hayas borrado del PC.
Lista las tuyas con `ios apps` y busca los bundle ID que empiezan por el Team ID:

```powershell
ios apps *> apps.json
python -c "import json; [print(a['CFBundleIdentifier'], '|', a.get('CFBundleDisplayName')) for a in json.load(open('apps.json', encoding='utf-16')) if 'nxnative' in a['CFBundleIdentifier'] or 'livecontainer' in a['CFBundleIdentifier'].lower()]"
```

Desinstala la que sobre con `ios uninstall <bundle>` y repite `ios install`. Ojo: al desinstalar se
borran también sus `Documents` (el `romfs.img` incluido), así que habrá que volver a copiarlos.

En este iPhone (6/11/2026) las tres eran Zelda TotK, Mario Kart 8 y LiveContainer; Silksong entró
al quitar LiveContainer.

## La copia de romfs.img se corta a mitad

Síntoma: `ios fsync push` de un archivo grande (6-17 GB) tarda varios minutos y termina con:

```
userspace tunnel inbound dispatch loop stopped … framedIPv6Reader: failed to read IPv6 header: EOF
userspace tunnel data plane stopped unexpectedly, tearing down tunnel
```

y los comandos siguientes fallan con `could not connect to RSD … ConnectUserSpaceTunnel: failed to
dial … actively refused it`. El `romfs.img` queda a medias y el juego lo dice al arrancar:
`[RED] boot: invalid RomFS image …/romfs.img (errno=22)` y `boot: game files not found`.

Qué hacer, en orden:

1. Comprueba el túnel con `ios tunnel ls`. Si no hay túnel o el puerto no responde:
   `ios tunnel stopagent` y `ios tunnel start --userspace` en una ventana aparte (se queda
   corriendo). Conecta el iPhone por cable y déjalo desbloqueado.
2. Borra el archivo a medias: `ios fsync --app=<bundle> rm --path=/Documents/romfs.img`.
3. Repite el push completo (`ios fsync --app=<bundle> push --srcPath=<romfs.img> --dstPath=/Documents`).
4. Abre el juego y mira `Documents/log.txt`: debe salir `boot: game files …/Documents/romfs.img`
   sin `invalid RomFS`.

Medido en Silksong (6,29 GB): el primer intento murió a los 6:40 y el segundo tardó ~7,5 min.
Tener la app en primer plano no evita el corte; lo que importa es que el túnel siga vivo.

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

## Se cierra al pulsar Play con Bluetooth

Pokémon: Let's Go, Pikachu! se cerraba al pulsar *Play*, sin informe de fallo. `log.prev.txt`
(la ejecución que se cerró) termina así:

```
[RED] sf: the game connects to service bt itself, which the host does not serve
Break#1 reason=0 Result=0 svc at sdk+0xd989c
bt: sdk+0x4c780 ...
main+0x1139d4
```

No es memoria ni shaders. El juego llama a `nn::bluetooth::InitializeBle` al arrancar
(`main+0x1139d4`) y después pide los eventos de escaneo, conexión, descubrimiento de servicios,
MTU y operaciones GATT del Poké Ball Plus. `InitializeBle` arranca el cliente `btm` del SDK, que
se conecta al servicio `bt` por sm y aborta dentro del cliente cuando la conexión se rechaza. El
host no sirve `bt`, y la capa `sf` no podía entregar los handles de evento que llevan las
respuestas del servicio.

La solución es `dm/host/hle_bluetooth.c`: deja la API de Bluetooth inerte. `InitializeBle`
devuelve éxito, cada `AcquireBle…Event` ata el `SystemEventType` del llamador a un evento del
kernel que no se dispara nunca, las listas de escaneo y conexión están vacías (las llamadas que
devuelven un contador devuelven 0) y toda operación GATT falla. El juego funciona como una
consola sin mando Bluetooth emparejado; el multijugador con Poké Ball Plus queda abierto. En la
referencia: [Bluetooth LE (`bt`) para el Poké Ball Plus](../reference/services.md#bluetooth-le-bt-for-the-poké-ball-plus).

## Va más rápido de lo normal

En Zelda: Tears of the Kingdom en el iPhone, con *Frame rate* en 30 o 60, el personaje a veces
corre más de la cuenta aunque el juego siga a 30 fps. No es memoria ni GPU: el IPA se compiló con
una versión del juego (1.4.2) distinta de la que el perfil del repositorio tiene probada (1.4.3).
Los parches del *frame step* están atados a los build IDs de 1.4.3, así que en 1.4.2 el host no
los aplica y fija la pantalla a un intervalo constante (1 vsync a 60, 2 a 30), mientras el juego
elige el suyo (2 = 30 fps, 3 = 20 fps con carga) y avanza el tiempo por ese intervalo. Un momento
de 20 fps mostrado a 30 corre un 50 % más rápido; a 60, todo corre al doble.

Solución inmediata, sin recompilar, en `Documents/env.txt`:

```
DM_FPS_TARGET=0
```

Cierra la app del todo y ábrela: el juego lleva su propio ritmo (30 fps, 20 en escenas cargadas) y
la velocidad vuelve a ser la normal. En un IPA con este cambio, elige *Game's own* en
**Frame rate**. Si consigues la actualización 1.4.3 (v720896), el perfil registrado ya trae los
parches y 30/60 funcionan a velocidad correcta. En la referencia:
[A frame-rate cap on a build without the frame-step stubs](../reference/frame-rate.md#a-frame-rate-cap-on-a-build-without-the-frame-step-stubs).

### Mario Kart 8: *Frame order* en Newest

En Mario Kart 8 Deluxe el juego iba al doble de velocidad aunque el contador de FPS marcara 60.
La opción **Performance → Frame order** estaba en *Newest* (`DM_PRESENT_FIFO=0`): el display link
toma el frame más reciente de cada tick y descarta los anteriores, así que el juego no recibe la
contrapresión del present y avanza dos frames por tick. Los frames fusionados no cuentan en el
contador, por eso seguía mostrando 60.

Solución: **Performance → Frame order → In order** (`DM_PRESENT_FIFO=1`, el valor por defecto).
No hace falta recompilar ni tocar `env.txt`; se cambia en el launcher y se vuelve a abrir el juego.

## La televisión no muestra el juego

El juego sale a la tele con **Centro de control → Duplicar pantalla** (AirPlay) o con un
adaptador HDMI. En `log.txt` tienen que salir estas dos líneas:

```
front end: TV output registered (an external display gets the game at 16:9)
front end: external display connected: 1920 x 1080 points, 1.00x
```

Si la primera no aparece, el IPA es de antes de este cambio. Si aparece la primera pero no la
segunda, AirPlay no está iniciado o la tele no lo admite. Está todo, con el resto de síntomas
(bandas, 4:3, imagen borrosa, vuelta al iPhone), en **[TV-AIRPLAY.md](TV-AIRPLAY.md)**.

## El juego no arranca y `log.txt` está vacío

- La app se cerró antes de que el host escribiera: firma, *Modo desarrollador* o el propio
  iOS. Revisa el log del sistema o vuelve a firmar.
- En LiveContainer, comprueba que estás mirando los *Documentos de la app del juego*, no los
  de LiveContainer.

## El build dice `nx_extract built without an executable`

Pasa si llamas directamente a `scripts\build_ipa_from_nsp.py` en Windows: ese script espera un
`nx_extract` sin extensión, pero .NET en Windows genera `nx_extract.exe`. No es un fallo de la
extracción ni de las llaves; el paso de Windows no se sustituye solo. Usa el driver de Windows:

```powershell
.\build.ps1 -Game "C:\Juegos\Pokemon" -Keys "C:\ruta\a\prod.keys"
# o, sin el envoltorio:
python win\build_ipa_windows.py "C:\Juegos\Pokemon" -k "C:\ruta\a\prod.keys"
```

`build.ps1` además pone la consola en UTF-8, así que evita el `UnicodeEncodeError` de la sección
anterior. El script de `scripts\` sigue siendo el correcto en macOS y Linux.

## El motor nuevo (Switch 2) falla en Windows

Al portar `seedds/nxnative` (el motor con soporte de Switch 2) sobre la capa de
Windows aparecieron estos fallos; están resueltos en la rama `switch2-engine`
del worktree `C:\Users\berna\nxw\NX2Apple-engine`:

| Mensaje | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'fcntl'` | `dm/tools/tree_tar.py` importa `fcntl` para bloquear la carpeta que empaqueta | `win/pyshim/fcntl.py` con `flock` inerte; `tree_tar.py` acepta que no haya `fcntl` |
| `OSError: [Errno 22] Invalid argument: '…\game.nup'` | `mmap` de un archivo vacío en Windows | `scripts/pack_nup.py` lo trata como “archivo vacío” |
| `PermissionError: [WinError 32] … being used by another process` al borrar un `.nup` | La prueba borra el archivo mientras sigue mapeado | Es de la limpieza de la prueba, no del build: el archivo se cierra al salir del proceso |
| `dm/host/Makefile changed (SRC= line)` | El motor nuevo añade `save_sync.c`, `web_apple.m`, dav1d y los shaders MSL del host | `win/build_app.py` actualizado; si vuelve a salir, compara la línea `SRC=`/`GFX=` con `host_sources()` |
| `host_msl_gen.h: No such file` | En Mac lo genera `make`; en Windows no hay `make` | `win/build_app.py` lo genera con `dm/gfx/tools/host_msl.py --sdk iphoneos` |
| `Error: the Mac platforms need a Mac` | `--platform mac` o `mac-app` en Windows | Es deliberado: usa iOS o compila en un Mac |
| `FileNotFoundError: …\RomFS.img\LD_C0_R.BIN` al derivar el perfil | `dm/tools/romfs.py` resolvía las rutas internas de una imagen RomFS con `/` y usaba `os.pread`, que no existen en Windows | `_resolve` normaliza `\`→`/`; `_File` abre con `O_BINARY` y lee con `lseek`+`read` (portado del motor estable `nxnative-win`) |
| `[RED] this Mac's Metal compiler is not the one the shaders were tested with (…): metal_macosx … metalfe-custom-windows (tested: … 32023.922)` | En Windows el compilador Metal es el front-end propio (`metalfe-custom-windows`, 32023.850) y `dmsh_chain.lock` espera el de Xcode 27.2 | Añade `--allow-other-metal` al build (o `DM_ALLOW_OTHER_METAL=1`); en Windows es la única opción |
| `AttributeError: module 'signal' has no attribute 'pthread_sigmask'` en `patch_nso.py` | `in_parallel` usa un pool `fork` y bloquea `SIGTERM` con `pthread_sigmask`; Windows no tiene ni uno ni otro | `in_parallel` cae a ejecución serie cuando falta `pthread_sigmask` |
| `OSError: [WinError 87] The parameter is incorrect` en `shader_split.py` | Un worker devuelve su lista de shaders por la tubería de `multiprocessing`; en Pokopia un solo `.fdata` de KTGL produce 203.120 shaders (6,3 GB de datos) y no cabe | En Windows `shader_split.py` escanea en serie dentro del proceso (`_pool_init` + lista), sin `ProcessPoolExecutor` |
| `[RED] translation chain tools do not match the lock file: spirv-cross …` y `the translator was not built from the in-repo source` | El lock guarda las huellas de macOS; en Windows el traductor y `spirv-cross` son otros binarios | Reconstruye `dmsh_xlate` con `dotnet publish`, ejecuta `win/update_tools_lock.py` (deja las líneas de Metal) y `dmsh_chain.py --header`. Ver [Reconstruir el traductor](NX2APPLE-SWITCH2.md#si-el-build-se-para-en-translation-chain-tools-do-not-match-the-lock-file) |

Los juegos de Switch 2 (`.nup` o carpeta `base/updates/dlc`) no necesitan
`prod.keys`. La guía completa está en
[NX2APPLE-SWITCH2.md](NX2APPLE-SWITCH2.md).

## Recopilar un informe

```powershell
python scripts\bug_report.py "C:\Juegos\BALLxPIT" --ios-log "C:\ruta\a\log.txt"
```

Recoge la versión del host, el perfil, el registro de la compilación y el `log.txt` que le
indiques, en un zip. **Revisa lo que adjuntas**: no incluyas `prod.keys`, NSP ni capturas con
datos personales. El script solo lee una lista blanca de archivos y tacha las rutas de tu
usuario, pero la última palabra es tuya.
