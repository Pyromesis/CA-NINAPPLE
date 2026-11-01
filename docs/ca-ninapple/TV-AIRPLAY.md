# Jugar en la televisión (AirPlay o cable)

La imagen del juego se muda a la tele y ocupa toda la pantalla, a 16:9. El iPhone se queda
como mando: en él siguen el gamepad en pantalla y el contador de FPS.

Es el comportamiento de **todos los juegos** y viene **activado por defecto**: no hay que
tocar nada en el lanzador ni por juego.

## 1. Cómo se usa

1. iPhone y tele en la misma red WiFi, con el AirPlay de la tele disponible.
2. Abre el juego y deja que arranque.
3. **Centro de control → Duplicar pantalla** y elige la tele.
4. La imagen salta al televisor en cuanto la pantalla externa aparece. Si la tele ya estaba
   conectada antes de abrir el juego, salta sola al empezar la partida.

Con cable: un adaptador de Lightning o USB-C a HDMI hace lo mismo; la pantalla aparece sola,
sin pasar por el Centro de control.

## 2. Comprobar que ha entrado

En `Documentos/log.txt` del juego (se saca con la app Files o con `ios fsync pull`) salen
estas líneas:

```
front end: TV output registered (an external display gets the game at 16:9)
front end: external display connected: 1920 x 1080 points, 1.00x
front end: game picture on the external display (1920 x 1080 points)
```

Al desconectar la pantalla:

```
front end: external display disconnected; the game picture is back on the phone
```

## 3. Apagarlo

En `Documents/env.txt`:

```
DM_TV_OUT=0
```

y reinicia el juego. La imagen se queda en el iPhone como antes. No hay interruptor en el
lanzador a propósito: el modo es parte del front end común, no una opción de cada juego.

## 4. Cómo funciona

- En iOS 27 el sistema ya no ofrece sola la escena de pantalla externa. Hay que registrar un
  `UISceneAccessory` no interactivo (`externalNonInteractiveSceneAccessoryWithConfiguration:`)
  sobre un controlador de la interfaz principal. El front end lo registra al empezar la
  partida, en `dm/ios/Sources/front_ios.m`.
- Cuando la pantalla aparece, el sistema crea una escena con `DmTVSceneDelegate`. Ahí se monta
  una `UIWindow` con su controlador, y la vista del juego (`DmGameView`, la capa
  `CAMetalLayer`) se mueve a esa ventana. La ventana del iPhone conserva el mando y los FPS.
- La capa toma `contentsScale` y `drawableSize` de la pantalla en la que está: 3x en el
  iPhone, 1x en la tele. Así el drawable de la tele es 1920x1080 y no 5760x3240.
- `present_viewport` (en `dm/gfx/nvn/nvn_mtl.m`) ya respeta la relación de aspecto del juego:
  un lienzo 16:9 dentro de un drawable 16:9 se dibuja a pantalla completa, sin bandas.
- En iOS 26 la escena externa se conecta sola; `App` (`dm/ios/Sources/main.m`) le devuelve
  este mismo delegado, así que el modo también funciona ahí.

## 5. Problemas

| Síntoma | Causa y solución |
|---|---|
| En el log no aparece `TV output registered` | El IPA es de antes de este cambio: recompílalo con este repositorio. |
| Aparece `registered` pero nunca `external display connected` | AirPlay no está iniciado, o la tele no admite AirPlay. Usa **Duplicar pantalla**; con cable, comprueba el adaptador. |
| La tele muestra el iPhone entero, con barras | Sigue siendo duplicación de pantalla: la escena externa no llegó a conectar. Revisa el paso 1 y el log. |
| Se ve con bandas arriba y abajo o a 4:3 | Ajusta la tele a 16:9 o a *Just scan* / *Ajustar a pantalla*. |
| Se ve borroso | La tele está reescalando; el juego se dibuja a 1920x1080. Usa el modo *Just scan* y desactiva el suavizado del televisor. |
| Al desconectar, el iPhone se queda en negro | El juego vuelve solo; si no, ciérralo y ábrelo. |
| El mando táctil no responde en la tele | Es normal: la escena externa no recibe toques. Se juega con el iPhone o con un mando Bluetooth. |
| Se oye, pero no se ve nada en la tele | Espera a que el juego termine de cargar: la ventana externa se crea al empezar la partida, no en el lanzador. |

Reinstalar el IPA encima de la misma app (mismo *bundle ID*) conserva `Documents/romfs.img` y
`Documents/save/`. Cierra el juego antes de instalar.
