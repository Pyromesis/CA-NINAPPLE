# Instalar y firmar el IPA en el iPhone

## Lo mínimo

1. Instala **[Sideloadly](https://sideloadly.io/)** en el PC. Cuando lo pida, instala también
   iTunes y iCloud **desde la web de Apple**, no desde la Microsoft Store.
2. Conecta el iPhone, arrastra el `.ipa` a Sideloadly, escribe tu Apple ID y pulsa **Start**.
   Deja vacíos los campos *Bundle ID* y *App Name*: así se respetan los del build.
3. En *Advanced options*, activa **Increased Memory Limit** si aparece. Sin ese permiso iOS
   deja a la app unos 3,4 GB y cierra los juegos grandes; con él, un iPhone reciente llega a
   unos 6 GB.
4. En el iPhone: **Ajustes → Privacidad y seguridad → Modo desarrollador**, reinicia, y luego
   confía en tu Apple ID en **Ajustes → General → VPN y gestión de dispositivos**.
5. Abre la app: sale el lanzador, pulsa **Play**.

Con un Apple ID gratis hay que volver a firmar cada **7 días**.

## LiveContainer

LiveContainer ejecuta el IPA dentro de su propia app, así que hereda **su** firma y **sus**
permisos. Es la forma cómoda de tener varios juegos sin volver a firmar cada uno.

- Instala LiveContainer firmado **con Increased Memory Limit**. Si LiveContainer no lo lleva,
  el juego tampoco lo tendrá, por muy grande que sea el IPA.
- Dentro de LiveContainer, instala `Juego.ipa` como app contenedora y ábrela desde ahí.
- Si usas compilación partida (`--split-data`), copia la carpeta `Juego-data` en
  *Documentos* de **la app del juego dentro de LiveContainer**, no en los Documentos de
  LiveContainer.
- El juego se cierra si iOS mata a LiveContainer: no lo cierres desde el selector de apps
  mientras juegas.

### Comprobar el límite de memoria

En `Documentos/log.txt` del juego, la línea de arranque dice cuánta memoria le ha dado iOS:

```
boot: memory limit 6000 MB
```

Si pone ~3375 MB, la firma no llevó el permiso: vuelve a firmar con **Increased Memory Limit**
(o compila con `--entitlements` y firma ese IPA).

## Qué necesita el dispositivo

- **iOS / iPadOS 26 o posterior.**
- **A17 Pro o superior** (iPhone 15 Pro y posteriores) o **iPad con M1 o superior**. Las
  texturas de los juegos vienen en BC y solo esos chips las leen en la GPU. En un A16 o
  anterior este fork las decodifica en CPU: carga más lenta y más memoria.
- Espacio libre: el IPA + los datos extraídos (el doble, si no usas compilación partida).

## Ajustes del lanzador

Antes de *Play*, el lanzador deja elegir:

| Ajuste | Para qué |
|---|---|
| **Frame rate** | 30 o 60 fps en los juegos cuyo perfil lo permite |
| **Render scale** | bajar la resolución 3D (al 50–100 %) si el juego va justo de GPU |
| **Console mode** | *Docked* o *Handheld* (en *Handheld* casi todo renderiza a 720p) |
| **Upscaling** | *Standard* o *MetalFX* |
| **Game language** | idioma del sistema que ve el juego |
| **Frame-rate counter** | FPS en pantalla |

Solo se guardan los valores distintos de los probados. Un `env.txt` en *Documentos* del juego
sigue mandando sobre cualquier ajuste (por ejemplo `DM_SHOW_FPS=0`).

## Copiar archivos al juego

Con la app **Files**: *En mi iPhone → <juego>* y ahí están `Documents/` (logs, `env.txt`,
`saves/`) y, si compraste el juego en la tienda, nada más. En un IPA compilado los datos van
dentro de la app; solo la compilación partida usa *Documentos*.

## Guardar partidas

Las partidas viven en `Documents/save/` del juego. Cópialas con la app Files antes de borrar
la app: al reinstalar se pierden.
