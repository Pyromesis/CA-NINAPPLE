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
| `[RED] this IPA uses vX (…), a version game profile … was not brought up on` | El perfil registrado es de otra versión | Es un aviso, no un error: el IPA usa un perfil derivado. La ruta soportada es poner la actualización que el perfil espera en la carpeta del juego |
| `doctor.py` muestra `MISSING` | Falta una herramienta | Instala lo que dice su línea `get it:` o fija la ruta en `win\toolchain.json` |
| La app se llama distinto o el bundle ID no es el del build | El firmador los sobreescribió | Mantén el nombre y el bundle ID del build en la herramienta de firma |
| Va lento, se calienta y baja de FPS | GPU al límite | *Render scale* al 75 %, *Console mode: Handheld*, *Upscaling: Standard* |

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

## Memoria

`log.txt` dice al arrancar:

```
boot: memory limit 6000 MB
```

- ~3375 MB: la firma no pidió **Increased Memory Limit**.
- ~6000 MB: correcto en un iPhone reciente.

Si el juego muere justo después de esa línea, o al entrar a una fase, es memoria. Prueba
`--split-data` (los datos no van dentro de la app), *Render scale* más bajo y *Handheld*.

## El juego no arranca y `log.txt` está vacío

- La app se cerró antes de que el host escribiera: firma, *Modo desarrollador* o el propio
  iOS. Revisa el log del sistema o vuelve a firmar.
- En LiveContainer, comprueba que estás mirando los *Documentos de la app del juego*, no los
  de LiveContainer.

## Recopilar un informe

```powershell
python scripts\bug_report.py "C:\Juegos\BALLxPIT" --ios-log "C:\ruta\a\log.txt"
```

Recoge la versión del host, el perfil, el registro de la compilación y el `log.txt` que le
indiques, en un zip. **Revisa lo que adjuntas**: no incluyas `prod.keys`, NSP ni capturas con
datos personales. El script solo lee una lista blanca de archivos y tacha las rutas de tu
usuario, pero la última palabra es tuya.
