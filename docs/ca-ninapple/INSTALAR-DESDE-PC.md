# Instalar el juego en el iPhone desde el PC

Esta es la ruta completa que se usó para dejar **BALL x PIT v0 (1.251)** funcionando en un
iPhone 16 Pro Max desde Windows, sin Mac. Sirve para cualquier IPA que haya salido de este
repositorio.

Hay dos caminos. El **A** es el más corto y el que se usó al final; el **B** deja el juego dentro
de LiveContainer, pero en iOS 26 exige un certificado importado en el propio teléfono.

| | Ruta A: instalación directa | Ruta B: LiveContainer |
|---|---|---|
| Quién firma | PlumeImpactor, desde el PC | LiveContainer, en el teléfono |
| Pasos en el teléfono | ninguno | importar certificado y pulsar **+** |
| Tiempo | ~5 min | ~10–15 min la primera vez |
| Memoria extra | sí, va en la firma del IPA | sí, va en la firma de LiveContainer |
| Varios juegos | uno por app | todos dentro de LiveContainer |

> Ningún comando de esta guía necesita `prod.keys`, el NSP ni el IPA dentro del repositorio.
> Usa tus propios volcados y tus propias llaves. No subas el UDID, el Apple ID, el `.p12` ni el
> perfil de aprovisionamiento a ningún sitio.

## 0. Lo que hay que tener

En el PC:

- El IPA ya compilado (por ejemplo `C:\Juegos\BALLxPIT\BallXPit.ipa`). Cómo se compila:
  [EMPEZAR.md](EMPEZAR.md).
- **Node.js** y **go-ios**, que es quien habla con el iPhone por USB:
  ```powershell
  winget install --id OpenJS.NodeJS.LTS -e
  npm install -g go-ios
  ios --help
  ```
- **PlumeImpactor** (`plumesign.exe`), el firmador open source:
  <https://github.com/khcrysalis/PlumeImpactor/releases>. El ejecutable de Windows se llama
  `plumesign.exe`. Es el único firmador que hace falta.
- Un **Apple ID** (vale una cuenta gratuita) y el iPhone con **Modo desarrollador** activo:
  *Ajustes → Privacidad y seguridad → Modo desarrollador*, reiniciar, y confiar en el
  certificado en *Ajustes → General → VPN y gestión de dispositivos*.

En el iPhone:

- Cable USB, desbloqueado, y **Confiar** en el PC cuando lo pregunte.
- iOS/iPadOS 26 o posterior y un chip A17 Pro o superior (o iPad con M1 o superior) para los
  juegos con texturas BC.

Comprueba que el PC ve el teléfono:

```powershell
ios list
```

Sale algo así (el UDID es tuyo, no lo publiques):

```json
{"deviceList":["00008140-XXXXXXXXXXXXXXXX"]}
```

Si sale `{"deviceList":[]}`, el cable, el desbloqueo o el «Confiar» están fallando. Nada de lo
que sigue funciona sin ese paso.

## 1. Entrar en la cuenta de Apple (una sola vez)

```powershell
plumesign account login
plumesign account list
```

La primera vez pide el Apple ID, la contraseña y el código de dos factores. La cuenta queda
guardada; `account list` muestra el equipo y el `TEAM_ID`, que hace falta más abajo.

No pegues la contraseña ni el código en un chat, en un issue ni en el repositorio.

## Ruta A: instalación directa (la que se usó)

### A1. Firmar el IPA

```powershell
plumesign sign --package "C:\Juegos\BALLxPIT\BallXPit.ipa" --apple-id -o "C:\Juegos\BALLxPIT\BallXPit-signed.ipa"
```

- `--apple-id` usa la cuenta guardada y pide el 2FA si hace falta.
- El IPA de salida lleva la firma de desarrollo y conserva los permisos que el binario pide,
  incluido `com.apple.developer.kernel.increased-memory-limit` si el build lo activó.
- Tarda uno o dos minutos con un IPA de 800 MB. Al final imprime
  `Saved signed package to: ...`.

Si el juego se compiló con **Increased Memory Limit** desactivado (`--no-entitlements`), el IPA
no pedirá el permiso y iOS le dará unos 3,4 GB. Para BALL x PIT v0 se dejó activado.

Para comprobarlo antes de instalar, sin abrir el juego: descomprime el IPA, saca el binario de
`Payload/<App>.app/<App>` y pide sus permisos.

```powershell
plumesign mach-o --entitlements "C:\Temp\DmIOS"
```

Tiene que salir `com.apple.developer.kernel.increased-memory-limit`. Si no aparece, el IPA se
firmó sin el permiso y hay que volver a compilarlo con él.

### A2. Instalar

```powershell
ios install --path "C:\Juegos\BALLxPIT\BallXPit-signed.ipa"
```

La salida termina en:

```
level=INFO msg="installation successful" module=go-ios/zipconduit
```

`plumesign device -i` también instala, pero en algunas cuentas gratuitas falla con
`Device ID not found`; `ios install` no tiene ese problema. Si `ios install` se queda parado,
mira que el teléfono siga desbloqueado y conectado.

### A3. Abrir y comprobar

Lo normal es abrir la app desde la pantalla de inicio. Para lanzarla desde el PC hace falta un
túnel de desarrollador:

```powershell
ios tunnel start --userspace
```

Déjalo en una ventana aparte y, en otra:

```powershell
ios apps --list | Select-String "BALL"
ios launch org.nxnativewindows.010086a022444000.<TEAM_ID>
```

El bundle ID real lo da `ios apps --list`; PlumeImpactor le añade el `TEAM_ID` al final. Si el
túnel se cae, abre la app con el dedo: es lo mismo y no depende del PC.

### A4. Leer el `log.txt` del juego

```powershell
ios fsync --app=org.nxnativewindows.010086a022444000.<TEAM_ID> pull --srcPath=/Documents/log.txt --dstPath="C:\Temp\ball-log"
Get-Content "C:\Temp\ball-log\log.txt" -Tail 40
```

`ios fsync` usa *house arrest*, no necesita el túnel ni la imagen de desarrollo. El destino se
crea como carpeta y dentro queda `log.txt`.

En un arranque correcto tienen que aparecer estas líneas:

```
launcher: Increased Memory Limit on (the app's signature)
memory guard: normal, the game's own frame rate (.... MB left before the system's memory limit)
[nvn-mtl] on-screen ... 300 frames, dropped 0 ... p99 16.67 ms
```

`Increased Memory Limit on` confirma que la firma llevó el permiso. Si el juego va a 60 fps, el
frame time p50 ronda 16,67 ms.

### A5. Renovar a los 7 días

Con Apple ID gratis la firma caduca. Vuelve a firmar el **mismo IPA sin firmar** y reinstala:

```powershell
plumesign sign --package "C:\Juegos\BALLxPIT\BallXPit.ipa" --apple-id -o "C:\Juegos\BALLxPIT\BallXPit-signed.ipa"
ios install --path "C:\Juegos\BALLxPIT\BallXPit-signed.ipa"
```

Las partidas viven en `Documents/save/` y no se borran al reinstalar la misma app. Aun así,
cópialas antes si vas a desinstalar.

## Ruta B: LiveContainer

LiveContainer ejecuta el IPA dentro de su propia app. La ventaja es que una sola firma de
LiveContainer sirve para varios juegos; el inconveniente es que en iOS 26 necesita un
**certificado de firma importado** para poder firmar cada juego en modo JIT-less.

### B1. Instalar LiveContainer

Descarga el paquete oficial **LiveContainer + SideStore** de
<https://github.com/LiveContainer/LiveContainer/releases> (probado con 3.8.0) y fírmalo con
PlumeImpactor:

```powershell
plumesign sign --package "C:\Descargas\LiveContainer+SideStore.ipa" --apple-id -o "C:\Descargas\LC-signed.ipa"
ios install --path "C:\Descargas\LC-signed.ipa"
```

- Si la firma falla con `An Application Group with Identifier ... is not available`, vuelve a
  ejecutar el mismo comando: PlumeImpactor crea los grupos de la app uno por uno y a la
  siguiente pasa.
- El paquete incluye SideStore y pide los permisos de memoria y HealthKit que LiveContainer
  necesita. No los quites.
- El bundle ID instalado lleva el equipo al final:
  ```powershell
  ios apps --list | Select-String "livecontainer"
  ```
  Por ejemplo `com.kdt.livecontainer.<TEAM_ID>`.

### B2. Importar el certificado en el teléfono

Abre **LiveContainer → Ajustes → Certificado** e impórtalo desde SideStore/AltStore o con tu
`.p12` y su contraseña. Sin este paso el `.ipa` se instala pero el juego no arranca. Es un paso
distinto de firmar LiveContainer: el permiso de memoria va en la firma de LiveContainer; el
certificado sirve para firmar cada juego dentro.

### B3. Copiar el IPA dentro de LiveContainer

Con el teléfono conectado:

```powershell
ios fsync --app=com.kdt.livecontainer.<TEAM_ID> push --srcPath="C:\Juegos\BALLxPIT\BallXPit.ipa" --dstPath=/Documents/BallXPit.ipa
```

`ios fsync` funciona porque LiveContainer comparte sus Documents (`UIFileSharingEnabled`). En el
teléfono, abre LiveContainer, pulsa **+** y elige `BallXPit.ipa`; también puedes dejarlo en la
app **Files** y elegirlo desde ahí. Espera a que termine: son 800 MB y tarda un par de minutos.

Cuando el juego ya esté instalado dentro de LiveContainer, borra la copia para recuperar espacio:

```powershell
ios fsync --app=com.kdt.livecontainer.<TEAM_ID> rm --path=/Documents/BallXPit.ipa
```

Si el teléfono no está conectado, bórralo desde **Files → En mi iPhone → LiveContainer**.
El juego instalado no se toca.

### B4. Abrir el juego

Desde la lista de LiveContainer, no desde la pantalla de inicio. No cierres LiveContainer desde
el selector de apps mientras juegas: iOS mata al anfitrión y con él al juego.

## Problemas que ya salieron

| Síntoma | Causa y solución |
|---|---|
| `plumesign device -i` dice `Device ID not found` | fallo de esa cuenta gratuita; usa `ios install --path ...` |
| `ios list` devuelve `{"deviceList":[]}` | cable, pantalla bloqueada o «Confiar» sin aceptar |
| `ios file` pide túnel o imagen de desarrollo | usa `ios fsync` para los Documents de una app; no instales certificados raíz para evitarlo |
| `ios image auto` falla con `x509: certificate signed by unknown authority` | el PC no confía en la raíz de Apple; no hace falta para instalar. No añadas certificados al almacén de Windows por esto |
| `ios launch` dice `could not connect to RSD` | el túnel no está corriendo: `ios tunnel start --userspace` en otra ventana, o abre la app con el dedo |
| `listen tcp 127.0.0.1:60105: bind: Only one usage...` | quedó un `ios tunnel` viejo; ciérralo con el Administrador de tareas y vuelve a empezar |
| La firma de LiveContainer falla por *Application Group* | vuelve a ejecutar `plumesign sign`; crea los grupos uno a uno |
| LiveContainer instala el IPA pero no lo abre | falta el certificado de B2, o caducó la firma de 7 días |
| Pantalla negra con música | mira `[RED] shader ... is not in the shader map` en `log.txt`; si no aparece, es el arranque, no los shaders |

### Detalles de Windows que hacen fallar comandos correctos

Ninguno de estos es un fallo del teléfono ni del IPA. Son trampas de PowerShell.

- **El comando termina en rojo y con código 1 aunque haya funcionado.** `go-ios` escribe sus
  trazas por *stderr*, y PowerShell las pinta como error. Lo que vale es la última línea:
  `installation successful`, `Process launched`, `Saved signed package to:`. Si aparece, ignorad
  el color y el código de salida.
- **No metas comillas dentro del patrón de `Select-String`.** Algo como
  `Select-String -Pattern "percentComplete\":100"` rompe el parseo de PowerShell
  (`The string is missing the terminator`). Filtra por una palabra sin comillas
  (`Select-String "installation successful"`) o quita el filtro y lee la salida entera.
- **`ios fsync pull --dstPath` crea una carpeta, no un archivo.** Si apuntas a
  `C:\Temp\ball-log.txt`, queda una carpeta `ball-log.txt` con `log.txt` dentro. Usa un nombre de
  carpeta y lee `C:\Temp\ball-log\log.txt`.
- **El túnel hay que dejarlo en otra ventana.** `ios tunnel start --userspace` no vuelve: se queda
  sirviendo. Si lo ejecutas en la misma consola, el siguiente comando no corre.
- **Un `ios` viejo ocupa el puerto 60105.** Si sale
  `bind: Only one usage of each socket address`, cierra el proceso `ios` en el Administrador de
  tareas (o `Stop-Process -Name ios -Force`) y vuelve a empezar. El túnel también se cae solo si
  desconectas el cable o bloqueas el teléfono: es normal, se relanza.
- **Rutas con espacios, entre comillas.** `--package "C:\Mis Juegos\BallXPit.ipa"`. Sin comillas,
  PowerShell parte el argumento y PlumeImpactor dice que no encuentra el paquete.

## Antes de dar por terminado

1. `ios apps --list` muestra el juego con la versión correcta (`1.251` en BALL x PIT v0).
2. El juego abre y llega al menú sin pantalla negra.
3. `log.txt` tiene `launcher: Increased Memory Limit on (the app's signature)`.
4. `log.txt` tiene `on-screen ... 300 frames, dropped 0` y un `p50` cercano a 16,67 ms.
5. Si algo falla, guarda el `log.txt` completo antes de tocar nada y mira
   [PROBLEMAS.md](PROBLEMAS.md); ahí está el diagnóstico de shaders, memoria y arranque.

## Caso real: BALL x PIT v0 (1.251)

- Build en Windows: `22.313` shaders, IPA de `802,9 MB`, perfil derivado del de la 1.293 y aviso
  `[RED] this IPA uses v0 (1.251)`.
- Firma con PlumeImpactor e instalación directa con `ios install` (ruta A).
- En el iPhone 16 Pro Max: `Increased Memory Limit on`, `1.461 MiB` residentes, `4,7 GB` de
  margen, `60 fps` (p50 16,67 ms) y `300/300` frames presentados.
- LiveContainer 3.8.0 quedó instalado, pero el juego se ejecuta con la ruta A: en iOS 26
  LiveContainer necesita el certificado de B2 antes de poder abrir un juego.
- Avisos que no impiden jugar: `174` claves de shader que no están en el mapa (el perfil es de
  otra versión) y alguna librería `_bp.metallib` que falta. Si un efecto concreto se ve mal,
  guarda el `log.txt` y revisa esas líneas.

## Limpieza

Después de instalar, puedes borrar:

- el IPA firmado (`*-signed.ipa`), porque se regenera firmando el original;
- la copia dentro de LiveContainer (B3);
- los `log.txt` que hayas copiado al PC.

**No borres** el IPA sin firmar que salió del build: es el original que se vuelve a firmar cada
7 días. Tampoco borres `Documents/save/` del juego si quieres conservar la partida.
