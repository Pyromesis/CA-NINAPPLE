# Mandos para jugar en el iPhone

El port incluye soporte de mandos físicos con **GameController** de Apple. No hace falta
jailbreak, ni PC, ni una app extra: se empareja por Bluetooth como cualquier auricular y el juego
lo usa directamente. Funciona igual con la instalación directa y con LiveContainer.

## Mandos que sirven

Cualquier mando que iOS presente con perfil **ExtendedGamepad**:

| Mando | Conexión | Notas |
|---|---|---|
| Xbox Series X\|S | Bluetooth | el más habitual en iPhone |
| Xbox One (modelo Bluetooth) | Bluetooth | los mandos Xbox One antiguos sin Bluetooth no sirven |
| PlayStation 5 DualSense | Bluetooth | tiene gyro y vibración fina |
| PlayStation 4 DualShock 4 | Bluetooth | tiene gyro; la vibración va por su informe de efectos |
| Backbone One, Razer Kishi, GameSir | USB-C / Lightning | se presentan como ExtendedGamepad |
| Mandos MFi | Bluetooth / cable | los que llevan el sello "Made for iPhone" |

Los mandos con perfil **MicroGamepad** (los de Apple TV) no se usan. Tampoco los que están en
modo "Android" o "XInput": esos no exponen el perfil que iOS necesita.

El IPA de BALL x PIT ya lleva el soporte declarado. Se puede comprobar sin abrir el juego:

```powershell
python -c "import zipfile,plistlib; d=plistlib.loads(zipfile.ZipFile(r'C:\Juegos\BALLxPIT\BallXPit.ipa').read('Payload/DmIOS.app/Info.plist')); print(d['GCSupportsControllerUserInteraction'], d['GCSupportedGameControllers'])"
```

Sale `True [{'ProfileName': 'ExtendedGamepad'}]`.

## Emparejar

### Xbox

1. Enciende el mando.
2. Mantén el botón de emparejar (el del canto superior, junto al USB) hasta que el logo de Xbox
   parpadee rápido.
3. En el iPhone: **Ajustes → Bluetooth** y toca **Xbox Wireless Controller**.

### PlayStation 5 (DualSense)

1. Con el mando apagado, mantén **PS + Create** hasta que la barra de luz parpadee dos veces.
2. **Ajustes → Bluetooth → DualSense Wireless Controller**.

### PlayStation 4 (DualShock 4)

1. Con el mando apagado, mantén **PS + Share** hasta que la luz parpadee.
2. **Ajustes → Bluetooth → Wireless Controller**.

Si el mando ya estaba emparejado con una consola o un PC, apaga el Bluetooth de ese equipo o
desempareja allí: el mando solo se conecta a un dispositivo a la vez.

## Qué pasa al conectarlo

- El **mando en pantalla desaparece** y todos los toques van al juego. Vuelve solo cuando se
  desconecta el mando.
- El mando pasa a ser **jugador 1**, junto con el mando táctil. Se pueden conectar hasta **8**
  mandos; cada uno es un jugador distinto (útil en juegos con cooperativo local).
- Si el mando ya estaba conectado antes de abrir el juego, también se detecta al arrancar.
- La vibración del juego se manda al mando. En DualSense/DualShock va por su motor; en Xbox el
  puerto usa el motor del mando con las limitaciones conocidas del servidor háptico de iOS.
- El gyro del mando se usa si lo tiene (DualSense, DualShock 4, mandos con sensores). Xbox no
  tiene gyro y no lo necesita.

## Mapeo de botones

El port mapea **por posición**, como un mando de Switch. Los textos del juego son de Switch, así
que hay que mirar la posición, no la letra:

| El juego dice | Posición | Xbox | PlayStation |
|---|---|---|---|
| **A** | derecha | **B** | **Círculo** |
| **B** | abajo | **A** | **Cruz** |
| **X** | arriba | **Y** | **Triángulo** |
| **Y** | izquierda | **X** | **Cuadrado** |
| L / R | bumpers | LB / RB | L1 / R1 |
| ZL / ZR | gatillos | LT / RT | L2 / R2 |
| + | menú | Menu | Options |
| − | vista | View | Create / Share |
| L3 / R3 | pulsar sticks | clic del stick | clic del stick |
| Cruceta | — | D-pad | D-pad |

En BALL x PIT, en una partida:

| Acción | Switch | Xbox | PlayStation |
|---|---|---|---|
| Mover | stick izquierdo | stick izquierdo | stick izquierdo |
| Apuntar | stick derecho | stick derecho | stick derecho |
| Disparar | ZR | RT | R2 |
| Fuego automático | X | **Y** | **Triángulo** |
| Confirmar | A | **B** | **Círculo** |
| Volver | B | **A** | **Cruz** |
| Barra lateral | X | **Y** | **Triángulo** |
| Enviar trabajador | ZR | RT | R2 |
| Desplazar el mapa | ZL + R | LT + RB | L2 + R1 |

## Comprobar que el juego lo ve

En `Documents/log.txt` del juego aparecen estas líneas:

```text
front end: each controller is a player of its own, the touch gamepad plays with player 1
controller 'Xbox Wireless Controller' connected: player 1 (npad 0)
```

La segunda solo sale al conectar o al arrancar con el mando ya encendido. Para leer el log:

```powershell
ios fsync --app=org.nxnativewindows.<...> pull --srcPath=/Documents/log.txt --dstPath="C:\Temp\ball-log"
Get-Content "C:\Temp\ball-log\log.txt" | Select-String "controller|front end"
```

## Si no funciona

| Síntoma | Causa y solución |
|---|---|
| No aparece en **Ajustes → Bluetooth** | el mando no está en modo emparejamiento, o está conectado a otro equipo. Mantén el botón de emparejar y apaga el Bluetooth del otro dispositivo |
| Aparece y conecta, pero el juego no responde | el mando no expone **ExtendedGamepad** (modo Android/XInput). Cámbialo a modo iOS/XInput si lo tiene, o usa otro mando |
| El mando en pantalla no desaparece | la app no ha visto el mando: mira el log; si no hay línea `controller ... connected`, el emparejamiento es del sistema pero el perfil no sirve |
| Los botones no coinciden con los textos | normal: el juego muestra letras de Switch y el mapeo es por posición; usa la tabla de arriba |
| Se desconecta solo | batería baja, distancia o suspensión del iPhone. Vuelve a **Ajustes → Bluetooth** y reconéctalo |
| No vibra | el juego puede no mandar vibración en esa escena; si manda y el mando es Xbox, es una limitación conocida del motor háptico, no del puerto |
| Dos mandos y el segundo no hace nada | el juego es de un jugador; el segundo mando es otro jugador y el juego lo ignora |
| Latencia | Bluetooth añade unos pocos milisegundos; a 60 fps no se nota. El cable solo hace falta para cargar |

## ¿Hace falta configurar algo en el juego?

No. No hay que activar nada en el launcher ni en `env.txt`. El puerto detecta el mando solo y
oculta el táctil. Si algún día hace falta que todos los mandos cuenten como jugador 1, existe la
variable `DM_PAD_MERGE=1`, pero para BALL x PIT no es necesaria.
