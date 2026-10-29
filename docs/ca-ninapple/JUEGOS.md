# Juegos

La lista completa de juegos con perfil propio, sus versiones probadas y lo que se sabe de
cada uno está en [`../../dm/games/README.md`](../../dm/games/README.md). Cada juego tiene su
carpeta con las notas de la versión con la que se probó.

## BALL x PIT

| | |
|---|---|
| Title ID | `010086A022444000` |
| Motor | Unity 6000.0.50f1 (IL2CPP), FMOD |
| Versión del perfil | **actualización 1.293 (v393216)** |
| Versión de estas pruebas | **base 1.251 (v0)**, perfil derivado |
| Estado | en validación en iPhone 16 Pro Max (A18 Pro, iOS 26) |

Notas de la base 1.251:

- El RomFS trae 33 archivos y **ningún bundle de Addressables**: los `Shader` están en
  `Data/sharedassets1.assets`, `Data/resources.assets`, `Data/sharedassets3.assets` y en los
  dos archivos de `Data/Resources`, sin árbol de tipos, con el hash `2ec7223d…` que
  `dm/gfx/tools/unityfs.py` ya sabe leer.
- En total **552 `Shader` + 19 `ComputeShader`**, que dan **22.313 programas** tras el split.
  Antes del arreglo de `romfs.py` solo salían 11 (los de `main`), y el juego arrancaba con
  música y pantalla negra.
- Los `sdk` de esta versión (`14113deb…`) reciben el corte de la zona de nodos por búsqueda
  de código, no por dirección fija.

Si pruebas otra versión, compila y mira el aviso del perfil: dirá si es la registrada o una
derivada. Manda el `log.txt` si algo falla.

## Añadir un juego nuevo

1. Una carpeta con el NSP base (y la actualización, si la tienes).
2. `python win\build_ipa_windows.py "C:\Juegos\Nuevo" -k "C:\Juegos\prod.keys"`.
3. Si el juego no tiene perfil, el script escribe un **perfil provisional** con lo que deduce
   del propio juego y avisa de que el IPA puede no arrancar. Es el punto de partida para
   portarlo, no una garantía.
4. Con el juego funcionando, las notas van a `dm/games/<title ID>/README.md` y las tablas que
   genere la compilación, a esa misma carpeta. Así el siguiente que lo compile no vuelve a
   pasar por lo mismo.
