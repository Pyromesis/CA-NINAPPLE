# Compilar más rápido: dónde se va el tiempo y qué se puede hacer

Medido en este PC (Windows 11, Ryzen 5 5600G de 6 núcleos / 12 hilos, 32 GB de
RAM, SSD NVMe, Metal Developer Tools 32023.850) con los shaders reales de
BALL x PIT y de Pokémon Pokopia (Switch 2), y contrastado con las medidas que
publica upstream (nxnative) para ese mismo juego.

## 0. Resumen: qué es lo que más acelera

| Palanca | Ganancia medida | Dificultad aquí |
|---|---|---|
| **Terminar los shaders en procesos trabajadores** (upstream `8b55ebb3`, 11/11/2026) | **×1,9** (3.506 s → 1.826 s con 42.848 shaders) | Alta: upstream usa `fork`, que en Windows no existe |
| **Compilar en un Mac** (M4 Pro: 12 núcleos a 4,4 GHz, `posix_spawn`) | **×3-5** frente a este PC | Baja si hay un Mac; el flujo es el de upstream |
| **Una máquina en la nube con 32-64 vCPU** (vía Linux + Wine) | ×3-4 | Media: hay que subir ~10 GB del juego |
| **Repartir la compilación entre varios equipos** | ×N | Media: el motor ya sabe importar librerías hechas en otro sitio (ver §6) |
| **Instalar las Metal Developer Tools más recientes** (32023.922, la que espera el lock) | sin medir | Baja: descarga de Apple con tu Apple ID |
| Un trabajador por núcleo lógico (`NXW_SHADER_JOBS`) | ya está | Hecho |
| `-O0`, `-Os`, compartir la caché entre juegos, la GPU | **nada** | — (ver §4) |

## 1. La parte lenta es el compilador de Metal

El pipeline tiene dos etapas largas y una rápida:

| Etapa | Qué hace | Pokopia (131.382 shaders) |
|---|---|---|
| Traducción | El binario de shaders del juego → SPIR-V (`dmsh_xlate`, el traductor de Ryujinx) → MSL (`spirv-cross`) | **58 min** (≈ 38 shaders/s) |
| Compilación | MSL → `.metallib` para iPhoneOS (`metal.exe` + `metallib.exe` de Apple) | **≈ 10 h** (2,35 shaders/s) |
| Empaquetado | El IPA, la app y la firma | minutos |

O sea: **el 90 % del tiempo es el compilador de Metal de Apple**, y no hay
forma de que lo haga la GPU: `metal.exe` es un compilador de host (un driver
de clang con el back end de Metal), se ejecuta en la CPU y no toca la GPU del
PC. El juego sí usa la GPU cuando corre; la compilación, no.

Lo único de Apple que usa la GPU es el *back end* del compilador
(`applegpu-nt`), que se ejecuta en el dispositivo o en `metal-tt` para el
archivo de pipelines sin conexión. Ese `metal-tt` **no viene** en las Metal
Developer Tools de Windows, así que esa vía no existe aquí.

Coste por shader medido (BALL x PIT, shaders de Switch 1):

| Paso | Tiempo |
|---|---|
| `metal.exe` (MSL → `.air`) | 0,374 s de CPU |
| `metallib.exe` (`.air` → `.metallib`) | 0,047 s de CPU |
| **Total** | **0,42 s de CPU por shader** |

Con 12 shaders/s, los 131.382 de Pokopia serían 3,1 h… pero costaron 10 h:
los shaders de Switch 2 son **unas 5 veces más caros** que los de Switch 1
(programas Ampere SM86 mucho más grandes), así que la cifra realista para un
juego de Switch 2 grande es ese orden de 10 h en este equipo.

## 2. Lo que el build ya hace bien

No hay que tocar nada de esto:

- **Cabecera precompilada** (`dmsh_pch.py`): el front end de cada `metal.exe`
  pasa un 80 % de su tiempo instanciando las plantillas de `metal::texture2d`
  y compañía; la cabecera las trae ya hechas. Ahorra ~0,3 s por shader.
- **`-O1`**: ni `-O0` ni `-O2` sirven. Medido: `-O0` es **más lento** (6,6
  shaders/s frente a 10,5 con `-O1`), porque el coste está en el front end, no
  en el optimizador. `-O2` deja un grafo de control que el back end de Apple
  tarda mucho en bajar, y el motor lo rechaza por eso.
- **Caché por texto de MSL**: la misma fuente produce el mismo `.metallib`, así
  que se compila una vez por texto distinto. En BALL x PIT hay 22.319 archivos
  `.metal` pero solo **6.584 textos distintos**: el 70 % son duplicados que no
  se compilan dos veces.
- **Solo librerías de iOS**: un build para iPhone no compila las de macOS
  (que nunca entran en el IPA).

## 3. Lo que encontró upstream para ese mismo juego

Upstream ([seedds/nxnative](https://github.com/seedds/nxnative)) documenta en
`docs/reference/shaders.md` y en la nota de
[Pokémon Pokopia](https://github.com/seedds/nxnative/blob/main/dm/games/0400A3A01EE4C000/README.md)
cinco problemas de velocidad de la etapa de shaders, todos medidos en un
M4 Pro. **Cuatro ya están en este motor** (los arreglamos al portarlo a
Windows); **el quinto, el más grande, no**.

| Problema (upstream) | Qué pasaba | Arreglo | Ganancia medida | ¿Lo tenemos? |
|---|---|---|---|---|
| El build leía cada paquete de shaders entero en memoria (105.118 registros de los 4,25 GB de `ps_rdb.bin` de Pokopia) | Cada proceso hijo (spirv-cross, metal, metallib) arrancaba de una copia de 8,7 GB: 75 ms en vez de 3, y con el GIL los `J` trabajadores se hacían cola | `record_index` escanea el paquete con un mapeo de solo lectura y guarda **solo las direcciones**; `rec_of` lee un registro con `pread` cuando hace falta | 1.001 shaders: 528 s → 240 s (1,9 → 4,2 shaders/s) | **Sí** (nuestro `record_index` con `O_BINARY` y el `os.pread` del shim) |
| Cada `metal` volvía a instanciar las plantillas de `metal::texture2d` | 722 ms de los 902 ms del front end eran las plantillas | `dmsh_pch.py`: una cabecera precompilada por convención de compilación | 1.019 shaders: CPU de los hijos 981-1.077 s → 574-605 s; el mapa entero, ~9 h → ~6,4 h | **Sí** |
| Las reescrituras del builder probaban el patrón en cada carácter de un fuente de 220 KB | 0,12 s de Python por shader, casi todo bajo el GIL: **4,2 h** de Python serializado en el build completo | `str.find`, de paréntesis a paréntesis, y un test antes de cada patrón | 8.157 shaders (Mac+iOS): 1.426 s → 607 s; el mapa entero, ~5 h → ~2,5 h | **Sí** |
| Los puntos de entrada laterales (`_ba`, `_bl`) se compilaban aparte | 366.805 compilaciones para el mapa de Pokopia, **57 %** para esas dos | Un solo cuerpo por shader y un corte del `.metallib` | CPU de Metal por shader de píxel: 0,830 s → 0,285 s (banderas de iPhone); 2.445 → 1.094 compilaciones | **Sí** (`compile_split` + `dmsh_side.cut`) |
| **El builder terminaba un shader a la vez** | El Python que reescribe el MSL, calcula la reflexión y escribe las salidas corre en hilos con **un solo GIL**: un núcleo hacía ese trabajo mientras los demás compiladores de Metal esperaban | **`DMSH_PROCS`**: terminar los shaders en **procesos** trabajadores, hechos una vez con `fork` | 42.848 shaders (Ocarina of Time) en un M3 Max: **3.506 s → 1.826 s (×1,9)**; "Mac+iOS, 84 s → 53 s" en Red Dead Redemption | **No** (es el commit `8b55ebb3` del 11/11/2026) |

Ese último es el que explica la diferencia entre los 2,35 shaders/s que vimos
aquí y los ~13 shaders/s que upstream mide en el mismo juego en un M4 Pro: el
suelo del build es el Python serializado por el GIL (0,05 s por shader =
**1,8 h** para 131.382 shaders), y mientras tanto los doce núcleos no
terminan shaders.

**El problema para portarlo**: upstream usa `fork`, que en Windows no existe.
Sus autores midieron la alternativa (`spawn`) y la descartaron: cada
trabajador tendría que releer las tablas del perfil (0,4 s y 58 MB en Cuphead;
3,7 s y 346 MB en el mapa de Ocarina of Time) y `dmsh_build.py` tendría que
dejar de arrancar un build al importarse. Hasta que eso se haga, en Windows el
interruptor es `DMSH_PROCS=0` (hilos, como ahora).

Lo que sí se puede hacer mientras tanto, y está medido:

- **Actualizar el motor** a `seedds/nxnative` actual: trae el arreglo de los
  trabajadores (con `fork`, o sea que en Windows habría que dejar
  `DMSH_PROCS=0`), la lectura de uniformes acotada (`e45694b7`), la
  reescritura de los tests de uniformes (`dfc5a15f`, que evita que el front
  end de Metal convierta una cadena de comparaciones en un `switch` que el
  compilador de GPU de Apple tardaba *minutos u horas* en bajar) y más juegos de
  Switch 2.
- **Compilar en un Mac**: upstream mide 13,4 shaders/s para el mismo juego en
  un M4 Pro (12 núcleos a 4,4 GHz, `posix_spawn` en vez de `CreateProcess`).
  Con 2,6× los núcleos y ~1,3× por núcleo, un Mac es **×3-5** frente a este
  PC, y sin el problema del GIL.
- **Una máquina en la nube con 32-64 vCPU** por la vía de Linux + Wine
  ([`../../win/LINUX.md`](../../win/LINUX.md)): ×3-4, subiendo los ~10 GB del
  juego.
- **Repartir la compilación entre varios equipos**: el motor ya sabe importar
  librerías compiladas en otro sitio (`dmsh_mtlcache.py` las recoge de un
  build anterior y las contrasta con una compilación de muestra). Se ha
  comprobado aquí que **el `.metallib` sale byte a byte igual** se compile
  donde se compile (la ruta de la cabecera precompilada y el nombre del fuente
  no cambian el resultado), así que un segundo equipo con las mismas Metal
  Developer Tools puede compilar una parte del mapa y sus `.metallib` se
  pueden copiar a la carpeta del build.

## 4. Los cinco mercado que sí aceleran

| Palanca | Efecto | Cómo se usa |
|---|---|---|
| **Más núcleos** | Lineal: el doble de núcleos, la mitad de tiempo | `NXW_SHADER_JOBS` fija los trabajadores; por defecto, uno por hilo del sistema |
| **No tirar la carpeta `<id>_build`** | Es la caché: sin ella se recompila todo | Borra solo el IPA, nunca la carpeta del build |
| **No mezclar un build de Mac en la misma carpeta** | Si la carpeta ya tiene las librerías de macOS de esta cadena, el build las compila **también**: el trabajo de Metal se duplica | Compila siempre en Windows o siempre en Mac, no las dos en la misma carpeta |
| **Un equipo con más núcleos o un Mac** | Un M5 Pro hace los 11.567 shaders de Mario Kart World en ~30 min según su autor | Nube con 32 vCPU (vía Linux + Wine, ver [`../../win/LINUX.md`](../../win/LINUX.md)) o un Mac |
| **Dejar que corra** | El build se puede parar y seguir: la caché guarda lo compilado | `Ctrl+C` y relanzar el mismo comando |

Medido de los trabajadores (`J`), 72 shaders de BALL x PIT:

| Trabajadores | shaders/s | Para 131.382 shaders |
|---|---|---|
| 6 | 9,2 | 4,0 h |
| **12** (un hilo por núcleo lógico) | **14,8** | **2,5 h** |
| 18 | 14,6 | 2,5 h |
| 24 (2 por núcleo, el valor anterior) | 14,6 | 2,5 h |

Con 12 ya no se gana nada: **más trabajadores que núcleos no aceleran nada**
y en los shaders grandes de Switch 2 solo suman procesos `metal.exe`
(≈ 46 MB cada uno, sin problema de memoria). Upstream lo midió igual en un
M3 Max: 0,066 s por archivo con 8 trabajos, 0,060 s con 10 y **0,093 s con
14** (más trabajadores, más lento).

Para fijarlos:

```powershell
$env:NXW_SHADER_JOBS = '12'
python win\build_ipa_windows.py "C:\Juegos\MiJuego" -k "C:\Juegos\prod.keys"
```

## 5. Lo que se ha probado y NO sirve

| Idea | Resultado |
|---|---|
| Que la GPU compile los shaders | Imposible: `metal.exe` es un compilador de host, no usa la GPU |
| `-O0` para compilar antes | **Más lento** (6,6 frente a 10,5 shaders/s) |
| `-Os` (optimizar por tamaño) | Igual de lento y con las mismas librerías (26 KB de media) |
| Quitar `-fpreserve-invariance` | Sin diferencia medible (10,2 frente a 10,5 shaders/s) |
| Compartir la caché entre juegos | El solape es del **0,2 %**: entre BALL x PIT y Cuphead solo hay 4 textos de MSL idénticos de 1.625. No compensa |
| Más de 12 trabajadores | Sin ganancia (tabla de arriba) |
| `metal -filetype=metallib` (un solo proceso) | No lo soporta este compilador: no genera el `.metallib` |
| `metallib` con varios `.air` de una vez | No: todos los shaders se llaman `main0` (`multiple symbols ('main0')`) |
| `metal` con varios fuentes de una vez | No con `-o` (`cannot specify -o when generating multiple output files`) |

## 6. Otros repositorios: qué hay y qué no

Se revisaron los proyectos que compilan juegos de Switch (y de Switch 2) a
Apple Silicon. **Ninguno compila más rápido**: el `.metallib` para iPhoneOS
solo lo produce el compilador de Apple, y todos usan el mismo.

| Proyecto | Qué es | Qué cambia respecto a este repo |
|---|---|---|
| [seedds/nxnative](https://github.com/seedds/nxnative) | El motor (reescritor, host de Horizon, NVN sobre Metal) | Es la base de este repositorio, y el único con las reparaciones de velocidad de la etapa de shaders |
| [LNPANDY/NX2Apple](https://github.com/LNPANDY/NX2Apple) | *Launcher* de escritorio (macOS y Windows) sobre nxnative | Su `nxb 0.6` traduce los shaders con su propio traductor en vez de `spirv-cross`: acelera la **traducción** (58 min en Pokopia), no la compilación con Metal. Publica además `NX2Apple-windows-x64.zip` |
| [pahorema/kartnative](https://github.com/pahorema/kartnative) | Fork de nxnative para Mario Kart World (Switch 2) | Front end SM86 propio y NVN2; 11.567 shaders en ~30 min en un M5 Pro |
| [robldctrl/nxnative-pokopia](https://github.com/robldctrl/nxnative-pokopia) | Fork de nxnative para Pokémon Pokopia (Switch 2) | Shaders de KTGL y captura en ejecución; ~1 h de traducción en Mac |
| [shirai91/nx2android](https://github.com/shirai91/nx2android) | Investigación: portar el motor a Android con Vulkan | Al borrar el paso de Metal, el PC de compilación ya no necesitaría herramientas de Apple, pero es un port a Android, no a iPhone |

Conclusión: lo único que cambia entre proyectos es **el traductor** (la etapa
de 1 h) y el soporte del juego. La etapa de 10 h es la misma en todos ellos,
y la única forma de acortarla es más CPU, el arreglo del GIL o repartir el
trabajo.

## 7. El caso de Pokémon Pokopia (Switch 2)

Lo que se midió en el build que se paró:

| Dato | Valor |
|---|---|
| Shaders del juego | 131.382 (+ las librerías laterales que se generan aparte) |
| Traducción | 58 min, completa |
| Compilación con Metal | 2,35 shaders/s → 28.382 shaders en 3 h 21 min (22 %) |
| Estimación del resto | ~10 h de compilación + empaquetado |
| Caché | `shader/ios/b-<cadena>` (6,18 GB) y `shader/cache/cas` (16 GB) |

Upstream, para el mismo juego: **~2,5 h** en un M4 Pro con todas sus
reparaciones, y **13,4 shaders/s** en las 8.157 librerías que usaron sus
pruebas de juego (Mac+iOS). La diferencia con los 2,35 shaders/s de aquí es el
GIL (§3) y los núcleos.

Ese build se paró y se borró después (los fuentes y la caché), así que volver a
empezar con Pokopia es desde cero: bajar el `.nup`, volver a separar los
shaders, 1 h de traducción y ~10 h de compilación (o ~3 h si se compila en un
Mac, o en una nube con muchos núcleos).

Si hay que hacerlo, el orden que sale bien es: translation → compilación de
Metal → empaquetado, con la carpeta del build intacta entre medias para poder
parar y seguir.
