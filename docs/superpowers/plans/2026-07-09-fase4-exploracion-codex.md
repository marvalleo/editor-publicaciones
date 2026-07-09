# Fase 4 — Brief de exploración para Codex

> Este documento es un encargo de **investigación**, no de implementación.
> Objetivo: catalogar el estado actual del código relevante a la Fase 4
> ("Texto rico + capas nuevas", ver `AGENTS.md` sección 6-7) para que la
> próxima sesión de brainstorming/diseño parta de hechos verificados en vez
> de suposiciones.

## Alcance — qué SÍ hacer

Producir un único documento de hallazgos en
`docs/superpowers/specs/2026-07-09-fase4-hallazgos.md`, con una sección por
cada punto de la lista de abajo. Cada hallazgo debe citar archivo y número
de línea exactos (usar `grep`/lectura directa, no memoria ni suposición).

## Alcance — qué NO hacer

- **No modificar código de producción** (`dcpub/`, `generar_publicacion.py`).
  Esto es lectura y documentación pura.
- No tomar decisiones de diseño (qué campos agregar, cómo se ve la UI). Eso
  se define después, con el usuario, en la sesión de brainstorming.
- No crear `CTALayer` ni tocar el modelo. Solo documentar qué existe hoy.
- Si algo no está claro o falta contexto, anotarlo como pregunta abierta en
  el propio documento de hallazgos — no bloquearse ni improvisar una
  respuesta.

## Puntos a investigar

### 1. `TextLayer` — brecha entre lo que existe y lo que pide Fase 4

- Archivo: `dcpub/models.py` — leer la clase `TextLayer` completa (campos
  actuales: `text`, `role`, `size`).
- El plan maestro (`AGENTS.md` sección 6, fila Fase 4) pide: fuente por
  elemento (dropdown), bold/italic/underline, interlineado, tracking
  (letter-spacing), stroke, rotación.
- Documentar: de esa lista, ¿cuáles NO existen hoy como campo del modelo?
  ¿Cuáles existen en el modelo pero no se usan en el render (buscar en
  `dcpub/render.py` cómo se dibuja el título/subtítulo/texto libre)?

### 2. `rotation` — campo fantasma

- `Layer.rotation` existe en la clase base (`dcpub/models.py`, buscar
  `rotation: float = 0.0`) y aparece en las tuplas de campos usadas para
  guardar/copiar estilo (buscar `"rotation"` en `dcpub/models.py`).
- Pero ¿se usa realmente en algún lado de `dcpub/render.py` para rotar el
  dibujo de una capa? Confirmar con grep si `layer.get("rotation")` o
  similar aparece en `render.py`. Documentar si es un campo que se guarda
  pero nunca se aplica visualmente (deuda pendiente, no bug — solo dejar
  constancia).

### 3. `BoxLayer` (recuadro de descripción) — hardcodes conocidos

Ya hay un pedido concreto del usuario registrado en memoria de proyecto
(ver `RESUMEN` más abajo) para que este recuadro tenga ancho/alto/color
configurables. Confirmar y precisar:

- `dcpub/render.py`, rama `elif kind == "desc":` (buscar el bloque
  completo): ¿dónde está hardcodeado el ancho al 90% del lienzo?
  (pista: buscar `0.90`).
- ¿Dónde se usa `BOX_COLOR` de `dcpub/constants.py` directo, sin pasar por
  el modelo de la capa? (pista: buscar `BOX_COLOR` en `render.py`).
- ¿El color del texto dentro del recuadro está hardcodeado a `BLANCO`
  también, o es configurable? Confirmar con el mismo bloque.
- `dcpub/models.py`, clase `BoxLayer`: listar exactamente los campos que
  tiene hoy (`text`, `icon`, `size` — confirmar si hay algo más) y cuáles
  le faltan para soportar ancho/alto/color/transparencia por capa.

### 4. `CTALayer` — qué tan preparado está el resto del sistema

- Confirmar que `CTALayer` NO existe todavía en `dcpub/models.py` (buscar
  `CTALayer` en todo `dcpub/`).
- `dcpub/batch_import.py`: ya guarda datos de CTA importados en
  `slide.extra["cta"]` (buscar `extra\["cta"\]` o `"cta"`). Documentar
  exactamente qué forma tiene ese dato hoy (¿string simple? ¿dict?) para
  que el futuro `CTALayer` sepa qué consumir cuando se implemente.
- El pedido del usuario (memoria de proyecto) es: capa CTA con color de
  caja, transparencia de caja, y color de texto configurables. Documentar
  si `BoxLayer` (punto 3) podría generalizarse para cubrir esto, o si hace
  falta una clase separada — sin decidir, solo listar la pregunta abierta.

### 5. Fuentes — soporte de fuente por elemento

- `dcpub/fonts.py`, clase `FontManager`: leer el método `load(role, size)`
  completo. Documentar si ya soporta pedir una fuente específica por
  nombre/familia, o si solo soporta roles fijos (ej. "title", "body").
- Documentar qué fuentes están disponibles hoy (buscar `download_fonts` o
  la lista de fuentes de marca) para saber qué opciones tendría un futuro
  dropdown de tipografía.

### 6. `LineLayer` / `DotsLayer` (líneas decorativas, puntos de carrusel)

- Confirmar que ninguna de las dos existe todavía en `dcpub/models.py` ni
  `dcpub/render.py` (buscar `LineLayer`, `DotsLayer`, `"line"`, `"dots"`).
  Solo constancia de que Fase 4 arranca desde cero en esto — no investigar
  más a fondo, es contexto menor.

## Formato del documento de salida

`docs/superpowers/specs/2026-07-09-fase4-hallazgos.md`, con esta estructura:

```markdown
# Fase 4 — Hallazgos de exploración (código actual)

## 1. TextLayer — campos existentes vs. pedidos
[hallazgos con archivo:línea]

## 2. rotation — campo fantasma
[hallazgo]

## 3. BoxLayer — hardcodes
[hallazgos]

## 4. CTALayer — estado de preparación
[hallazgos]

## 5. Fuentes por elemento
[hallazgos]

## 6. LineLayer / DotsLayer
[confirmación]

## Preguntas abiertas para el brainstorming
[lista, si las hay]
```

Al terminar: commitear el documento con
`git add docs/superpowers/specs/2026-07-09-fase4-hallazgos.md && git commit -m "docs: agregar hallazgos de exploracion de Fase 4"`.
No hace falta correr la suite de tests — este trabajo no toca código.

## RESUMEN — pedido del usuario que motiva esta exploración

> Durante el testeo en vivo de la Tarea 1.4, el usuario pidió dos features
> que encajan en Fase 4:
> 1. Caja CTA: color de la caja, transparencia de la caja, color del texto.
> 2. Recuadro de descripción (BoxLayer) configurable: ancho y alto propios
>    (hoy hardcodeado al 90% del lienzo en `render.py`), más opciones de
>    color (hoy usa `BOX_COLOR` fijo de `constants.py`).
