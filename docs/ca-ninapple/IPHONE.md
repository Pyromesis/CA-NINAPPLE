# Instalar el IPA en el iPhone con LiveContainer

LiveContainer ejecuta el IPA dentro de su propia app: una sola firma sirve para varios juegos y
no hay que volver a firmar cada uno. Es la vía que documenta este proyecto.

> Si prefieres los comandos exactos de principio a fin, con los errores que ya salieron y su
> solución, está todo junto en **[INSTALAR-DESDE-PC.md](INSTALAR-DESDE-PC.md)**. Esta página
> explica el porqué de cada paso; esa otra es la receta que se copia y se pega.

## Herramientas (enlaces oficiales)

| Herramienta | Descarga oficial | Para qué |
|---|---|---|
| LiveContainer | <https://github.com/LiveContainer/LiveContainer> | ejecutar los IPAs dentro de su app |
| SideStore | <https://sidestore.io/> | firmar en el propio iPhone, sin PC |
| AltStore | <https://altstore.io/> | firmar desde el PC con AltServer |
| PlumeImpactor | <https://github.com/khcrysalis/PlumeImpactor> | firmador open source para Windows, Linux y macOS |

## 1. Instalar LiveContainer (una sola vez)

LiveContainer no se instala solo: hay que firmarlo con tu Apple ID usando uno de los firmadores
de arriba, **pidiendo el permiso Increased Memory Limit**
(`com.apple.developer.kernel.increased-memory-limit`).

- Ese permiso se pide al firmar **LiveContainer**, no el juego. Si LiveContainer no lo lleva,
  el juego tampoco lo tendrá, por grande que sea el IPA.
- Sin el permiso, iOS deja a la app unos 3,4 GB y cierra los juegos grandes; con él, un iPhone
  reciente llega a unos 6 GB.
- En el iPhone: **Ajustes → Privacidad y seguridad → Modo desarrollador**, reinicia, y confía
  en el certificado en **Ajustes → General → VPN y gestión de dispositivos**.

Con un Apple ID gratis hay que volver a firmar cada **7 días**.

En iOS 26 LiveContainer firma los juegos en modo **JIT-less** y necesita un **certificado
importado**. Sin certificado el `.ipa` se copia, pero el juego no arranca. Se importa en
**LiveContainer → Ajustes → Certificado**, desde SideStore/AltStore o con tu `.p12` y su
contraseña. Es un paso aparte de firmar LiveContainer: el permiso de memoria va en la firma de
LiveContainer; el certificado sirve para firmar cada juego dentro.

## 2. Instalar el juego dentro de LiveContainer

1. Copia `Juego.ipa` al iPhone: con la app **Files** (iCloud Drive, AirDrop o *En mi iPhone*).
   También puedes dejarlo en los *Documentos* de LiveContainer por USB (copia de archivos de la
   app) y elegirlo desde el botón **+**.
2. Abre **LiveContainer** y usa el botón de instalar (**+**) para elegir el `.ipa`.
3. El juego aparece como una app más dentro de LiveContainer. Ábrelo desde ahí.
4. La primera vez, deja que llegue al menú antes de tocar nada.

No cierres LiveContainer desde el selector de apps mientras juegas: iOS mata al anfitrión y con
él al juego.

## ¿Y un mando?

Sí: se empareja por Bluetooth en **Ajustes → Bluetooth** y el mando en pantalla desaparece. El
mapeo es por posición, como un mando de Switch. Está todo en **[MANDOS.md](MANDOS.md)**.

## 2b. Instalar directo, sin LiveContainer

Si no quieres configurar el certificado de LiveContainer, **[PlumeImpactor](https://github.com/khcrysalis/PlumeImpactor)**
firma e instala el `.ipa` directamente con tu Apple ID. El IPA ya pide *Increased Memory Limit*
al firmarse, así que el juego recibe la memoria extra igual. Es la vía que se usó para probar
BALL x PIT v0 en un iPhone 16 Pro Max. Los comandos están en
**[INSTALAR-DESDE-PC.md, ruta A](INSTALAR-DESDE-PC.md#ruta-a-instalación-directa-la-que-se-usó)**.

## 3. Comprobar la memoria

En `Documentos/log.txt` del juego, la línea de arranque dice cuánta memoria le ha dado iOS:

```
boot: memory limit 6000 MB
```

Si pone ~3375 MB, la firma de LiveContainer no llevó el permiso: vuelve a firmarlo con
**Increased Memory Limit**.

## 4. Compilación partida (IPA pequeño + carpeta de datos)

Si compilaste con `--split-data`, el IPA solo trae la app:

1. Instala el IPA en LiveContainer y ábrelo una vez (avisa de que faltan los datos).
2. Copia la carpeta `Juego-data` entera en *Documentos* de **la app del juego dentro de
   LiveContainer**, no en los Documentos de LiveContainer.
3. Vuelve a abrir el juego.

## 5. Qué necesita el dispositivo

- **iOS / iPadOS 26 o posterior.**
- **A17 Pro o superior** (iPhone 15 Pro y posteriores) o **iPad con M1 o superior**. Las
  texturas de los juegos vienen en BC y solo esos chips las leen en la GPU. En un A16 o
  anterior este fork las decodifica en CPU: carga más lenta y más memoria.
- Espacio libre: el IPA + los datos extraídos (el doble, si no usas compilación partida).

## 6. Ajustes del lanzador

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

## 7. Archivos y partidas

Las partidas viven en `Documents/save/` del juego. Cópialas con la app Files antes de borrar la
app: al reinstalar se pierden.
