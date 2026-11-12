# Compilar más rápido: dónde se va el tiempo y qué se puede hacer

Medido en este PC (Windows 11, Ryzen 5 5600G de 6 núcleos / 12 hilos, 32 GB de
RAM, SSD NVMe, Metal Developer Tools 32023.850) con los shaders reales de
BALL x PIT y de Pokémon Pokopia (Switch 2).

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

## 3. Los cinco市场价 que sí aceleran

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
(≈ 46 MB cada uno, sin problema de memoria).

Para fijarlos:

```powershell
$env:NXW_SHADER_JOBS = '12'
python win\build_ipa_windows.py "C:\Juegos\MiJuego" -k "C:\Juegos\prod.keys"
```

## 4. Lo que se ha probado y NO sirve

| Idea | Resultado |
|---|---|
| Que la GPU compile los shaders | Imposible: `metal.exe` es un compilador de host, no usa la GPU |
| `-O0` para compilar antes | **Más lento** (6,6 frente a 10,5 shaders/s) |
| Quitar `-fpreserve-invariance` | Sin diferencia medible (10,2 frente a 10,5 shaders/s) |
| Compartir la caché entre juegos | El solape es del **0,2 %**: entre BALL x PIT y Cuphead solo hay 4 textos de MSL idénticos de 1.625. No compensa |
| Más de 12 trabajadores | Sin ganancia (tabla de arriba) |
| `metal -filetype=metallib` (un solo proceso) | No lo soporta este compilador: no genera el `.metallib` |

## 5. Otros repositorios: qué hay y qué no

Se revisaron los proyectos que compilan juegos de Switch (y de Switch 2) a
Apple Silicon. **Ninguno compila más rápido**: el `.metallib` para iPhoneOS
solo lo produce el compilador de Apple, y todos usan el mismo.

| Proyecto | Qué es | Qué cambia respecto a este repo |
|---|---|---|
| [seedds/nxnative](https://github.com/seedds/nxnative) | El motor (reescritor, host de Horizon, NVN sobre Metal) | Es la base de este repositorio |
| [LNPANDY/NX2Apple](https://github.com/LNPANDY/NX2Apple) | *Launcher* de escritorio (macOS y Windows) sobre nxnative | Su `nxb 0.6` traduce los shaders con su propio traductor en vez de `spirv-cross`: acelera la **traducción** (58 min en Pokopia), no la compilación con Metal. Publica además `NX2Apple-windows-x64.zip` |
| [pahorema/kartnative](https://github.com/pahorema/kartnative) | Fork de nxnative para Mario Kart World (Switch 2) | Front end SM86 propio y NVN2; 11.567 shaders en ~30 min en un M5 Pro |
| [robldctrl/nxnative-pokopia](https://github.com/robldctrl/nxnative-pokopia) | Fork de nxnative para Pokémon Pokopia (Switch 2) | Shaders de KTGL y captura en ejecución; ~1 h de traducción en Mac |
| [shirai91/nx2android](https://github.com/shirai91/nx2android) | Investigación: portar el motor a Android con Vulkan | Al borrar el paso de Metal, el PC de compilación ya no necesitaría herramientas de Apple, pero es un port a Android, no a iPhone |

Conclusión: lo único que cambia entre proyectos es **el traductor** (la etapa
de 1 h) y el soporte del juego. La etapa de 10 h es la misma en todos ellos.

## 6. El caso de Pokémon Pokopia (Switch 2)

Lo que se midió en el build que se paró:

| Dato | Valor |
|---|---|
| Shaders del juego | 131.382 (+ las librerías laterales que se generan aparte) |
| Traducción | 58 min, completa |
| Compilación con Metal | 2,35 shaders/s → 28.382 shaders en 3 h 21 min (22 %) |
| Estimación del resto | ~10 h de compilación + empaquetado |
| Caché | `shader/ios/b-<cadena>` (6,18 GB) y `shader/cache/cas` (16 GB) |

Ese build se paró y se borró después (los fuentes y la caché), así que volver a
empezar con Pokopia es desde cero: bajar el `.nup`, volver a separar los
shaders, 1 h de traducción y ~10 h de compilación.

Si hay que hacerlo, el orden que sale bien es: translation → compilación de
Metal → empaquetado, con la carpeta del build intacta entre medias para poder
parar y seguir.
