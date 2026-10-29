# Procedencia y alcance

CA-NINAPPLE es una distribución para Windows de **NXNative**. No es un emulador: el código
arm64 del propio juego se ejecuta en el chip de Apple y los gráficos de Switch se reconstruyen
sobre Metal. El proyecto no está afiliado a Nintendo, Apple ni a ninguna distribuidora.

## Cadena de autoría

| Proyecto | Autor | Licencia | Qué aportó |
|---|---|---|---|
| [d2r-mobile](https://github.com/jhaizhou-ops/d2r-mobile) | jhaizhou-ops y colaboradores | MIT | El enfoque de ejecución nativa, el reescritor de NSO, el host que sustituye a Horizon y la capa NVN-sobre-Metal |
| [nxnative](https://github.com/seedds/nxnative) | seedds | MIT | El proyecto general, los perfiles de juego, la cadena de shaders y la app iOS |
| [NXNativeWindows](https://github.com/zenvyzenshiro/NXNativeWindows) | ZenvyZenshiro | MIT | La ruta de compilación en Windows (`win/`), sin Mac |
| **CA-NINAPPLE** | Pyromesis | MIT | Documentación en español, recetas verificadas y los arreglos de esta distribución |

El texto de la licencia MIT y sus titulares se conservan en [`LICENSE`](LICENSE). Cada archivo
sigue siendo de quien lo escribió; este repositorio no reclama autoría sobre el trabajo de los
anteriores.

## Qué añade CA-NINAPPLE

- `docs/ca-ninapple/`: guías en español (Windows, iPhone/LiveContainer, problemas y juegos).
- `build.ps1`: un solo comando desde PowerShell, con la consola en UTF-8.
- Arreglo en `dm/tools/romfs.py`: en Windows el `RomFS.img` se abría sin `O_BINARY`, así que
  la lectura se cortaba en el primer byte `0x1A` y los `.assets` de Unity se leían truncados
  (11 shaders en vez de 22.313 en BALL x PIT v0). Con su prueba de regresión en
  `dm/tools/tests/test_romfs_read.py`.
- Los arreglos de la ruta Windows ya presentes en el fork (`-mcpu=apple-a17`, rutas `-F` del
  SDK, `os.pread` sustituido donde Windows no lo tiene, `normpath` al materializar enlaces).

## Qué no contiene este repositorio

- **Ningún juego**, ni archivos extraídos de juegos, ni capturas de datos del juego.
- **Ninguna llave** (`prod.keys`, `title.keys`).
- **Ningún SDK de Apple** ni las Metal Developer Tools: se descargan de Apple con tu cuenta y
  se extraen en tu equipo (`win/sdk/out/`, ignorado por git).
- **Ningún IPA compilado**.

## Uso

Necesitas tus propios volcados y tus propias llaves, hechos con tu consola. Descargar juegos
de internet no es lo que este proyecto permite ni lo que documenta.
