# Fase 4 — Brief de exploración para Codex: líneas decorativas + puntos de carrusel

> Este documento es un encargo de **investigación**, no de implementación.
> Objetivo: catalogar el estado actual del código relevante a las dos
> últimas piezas de Fase 4 ("líneas decorativas" y "puntos de carrusel",
> ver `AGENTS.md` sección 6-7) para que la próxima sesión de
> brainstorming/diseño parta de hechos verificados.

## Alcance — qué SÍ hacer

Producir un único documento de hallazgos en
`docs/superpowers/specs/2026-07-09-fase4-lineas-puntos-hallazgos.md`, con
una sección por cada punto de la lista de abajo. Cada hallazgo debe citar
archivo y número de línea exactos (usar `grep`/lectura directa, no memoria
ni suposición).

## Alcance — qué NO hacer

- **No modificar código de producción** (`dcpub/`, `generar_publicacion.py`).
  Esto es lectura y documentación pura.
- No tomar decisiones de diseño (qué campos exactos, cómo se ve la UI). Eso
  se define después, con el usuario, en la sesión de brainstorming.
- No crear `LineLayer` ni `DotsLayer` ni tocar el modelo. Solo documentar
  qué existe hoy.
- **Importante — evitar conflictos:** en paralelo a este encargo, otra
  sesión está trabajando en `dcpub/render.py`, `dcpub/models.py`,
  `dcpub/fonts.py` y `dcpub/app.py` (texto rico por elemento). No edites
  ninguno de esos archivos bajo ningún concepto — este encargo es 100%
  de lectura.
- Si algo no está claro o falta contexto, anotarlo como pregunta abierta en
  el propio documento de hallazgos — no bloquearse ni improvisar una
  respuesta.

## Puntos a investigar

### 1. Confirmar que `LineLayer`/`DotsLayer` no existen

- Buscar `LineLayer` y `DotsLayer` en todo `dcpub/` (deberían no aparecer
  en ningún lado excepto quizás comentarios/docstrings). Confirmar con
  grep exacto y citar que la búsqueda no encontró nada, o documentar
  cualquier mención parcial que sí exista.
- Confirmar en `dcpub/models.py` que `LAYER_CLASSES` no incluye `"line"`
  ni `"dots"` como claves (buscar la definición actual del dict).

### 2. Líneas decorativas que YA existen (hardcodeadas, no son una capa)

- `dcpub/render.py`, rama `elif kind == "sub":` (buscar el bloque
  completo, dibuja el subtítulo): documentar exactamente cómo se dibujan
  las líneas horizontales a los costados del subtítulo hoy — buscar
  `line_len`, `gap`, `lw_deco`, `deco_layer`, `deco_draw`. Citar: de dónde
  sale el largo de la línea (fracción de qué), el grosor, el color
  (¿fijo? ¿de qué constante?), y el espacio (`gap`) entre la línea y el
  texto.
- Documentar si esta lógica está atada 1:1 al subtítulo (imposible de
  reutilizar como capa independiente sin refactor) o si ya tiene alguna
  forma reusable (función separada, parámetros claros).

### 3. Qué pediría una `LineLayer` según el plan maestro

- Leer `CLAUDE.md` (o `AGENTS.md`, son equivalentes), sección 4
  "Subtipos", la entrada `LineLayer`. Citar textualmente los campos que
  menciona (`length`, `thickness`, `color`, `gap`).
- Comparar esos campos contra lo que ya existe hardcodeado en el punto 2:
  ¿cuáles de esos campos ya tienen un valor calculado hoy (aunque sea fijo,
  no configurable) y cuáles no existen en absoluto?

### 4. Qué pediría una `DotsLayer` según el plan maestro

- Mismo ejercicio: leer la entrada `DotsLayer` en `CLAUDE.md`/`AGENTS.md`
  sección 4, citar los campos (`count`, `active`, `color`, `spacing`).
- Buscar en todo `dcpub/` si existe *cualquier* noción de "posición dentro
  del carrusel" o "cantidad de láminas" ya disponible en el modelo o en
  algún panel de UI, que una futura `DotsLayer` podría necesitar leer
  (pista: revisar `dcpub/models.py` la clase `Project`/`Slide`, y
  `dcpub/slides_panel.py` si existe, para ver cómo se sabe "cuántas
  láminas hay" y "cuál es la actual"). Documentar qué API ya existe para
  eso (nombres de atributos/métodos exactos), sin proponer diseño nuevo.

### 5. Patrón de capas "puramente decorativas, sin texto ni contenido editable"

- Las capas existentes (`PhotoLayer`, `LogoLayer`, `TextLayer`, `BoxLayer`,
  `CTALayer`) todas tienen algún contenido central (foto, imagen, texto).
  `LineLayer`/`DotsLayer` serían las primeras capas puramente gráficas/
  geométricas, sin texto. Documentar como pregunta abierta (no resolver):
  ¿el panel de propiedades genérico actual (`_build_property_panel` en
  `dcpub/app.py`, buscar el bloque que arma x/y/size/opacidad para
  cualquier capa no-foto) ya soportaría una capa sin campo `size` de
  fuente, o asume implícitamente que siempre hay un "tamaño de fuente"?
  Citar la línea exacta donde se arma el label "Tamaño de fuente" para
  confirmar si depende de asumir texto.

## Formato del documento de salida

`docs/superpowers/specs/2026-07-09-fase4-lineas-puntos-hallazgos.md`, con
esta estructura:

```markdown
# Fase 4 — Hallazgos de exploración: líneas decorativas + puntos de carrusel

## 1. Confirmación de ausencia de LineLayer/DotsLayer
[hallazgos]

## 2. Líneas decorativas existentes (subtítulo)
[hallazgos con archivo:línea]

## 3. LineLayer segun el plan maestro vs. lo que ya existe
[comparación]

## 4. DotsLayer segun el plan maestro vs. API de láminas disponible
[hallazgos]

## 5. Patrón de capas puramente decorativas
[hallazgo + pregunta abierta]

## Preguntas abiertas para el brainstorming
[lista, si las hay]
```

Al terminar: commitear el documento con
`git add docs/superpowers/specs/2026-07-09-fase4-lineas-puntos-hallazgos.md && git commit -m "docs: agregar hallazgos de exploracion de lineas y puntos de Fase 4"`.
No hace falta correr la suite de tests — este trabajo no toca código.

Nota de entorno: si `git commit` falla por permisos (`.git/index.lock`,
`Permission denied`), es un problema conocido de este entorno — dejar el
archivo creado sin commitear y avisarlo en la respuesta final, otra sesión
se encarga del commit.
