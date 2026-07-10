# Fase 4 — Líneas decorativas + puntos de carrusel — Tareas para Codex

> Basado en `docs/superpowers/specs/2026-07-09-fase4-lineas-puntos-hallazgos.md`.
> Este documento resuelve las 6 preguntas abiertas de ese hallazgo con
> decisiones concretas (ver abajo) para poder trabajar en paralelo. Si
> alguna decisión no encaja al implementar, documentarlo y avisar — no es
> inamovible, es el punto de partida más razonable dado el código actual.

## Decisiones de diseño (resuelven las preguntas abiertas del hallazgo)

1. **`LineLayer` es independiente**, no reemplaza ni refactoriza las líneas
   hardcodeadas del subtítulo (`dcpub/render.py` rama `elif kind == "sub":`).
   Esas líneas quedan como están (riesgo innecesario tocarlas ahora, recién
   salieron de Fase 4 sub-fase 2). `LineLayer` es una capa nueva que el
   usuario agrega donde quiera, con controles propios.
2. **`gap`** en `LineLayer` = separación entre los dos segmentos de línea
   cuando se usa como par (izquierda/derecha de un centro), igual semántica
   que el `gap` ya usado en el subtítulo. Si `gap == 0`, se dibuja un solo
   segmento continuo de largo `length` (no dos mitades).
3. **`thickness`** se expresa como fracción del ancho del lienzo (`frac`),
   igual convención que el resto del modelo (todo en `Layer` ya es fracción
   0.0–1.0). No aceptar píxeles absolutos — mantiene consistencia con
   preview/export escalando igual que todo lo demás.
4. **`DotsLayer.count` y `DotsLayer.active` se derivan automáticamente**
   de `len(project.slides)` y `current_slide_index` en los adaptadores
   (`_build_layers_for` / `_layers_from_slide`), no son campos editables
   a mano en el modelo — evita que se desincronicen del carrusel real. El
   modelo solo persiste `color` y `spacing` (frac).
5. **`DotsLayer` vive como capa por lámina** (igual que `CTALayer`, `BoxLayer`,
   etc.), no como overlay global — así el usuario puede posicionarla y
   ocultarla por lámina como cualquier otra capa, reusando toda la
   infraestructura de selección/drag/undo existente.
6. **El panel de propiedades necesita un camino sin "Tamaño de fuente"**:
   `LineLayer`/`DotsLayer` no usan el slider genérico de `"size"` con label
   de fuente — usan sliders con labels propios (`length`/`thickness` para
   línea, `spacing` para puntos).

## Cómo paralelizar

`LineLayer` y `DotsLayer` son independientes entre sí (no comparten código
más allá del boilerplate de "nueva capa" que ya existe para `cta`/`box`).
Se pueden trabajar como **dos tracks separados en dos worktrees distintos**
(mismo patrón que Fases 2/3/4 ya usaron), cada uno con su propia serie de
tareas secuenciales, y mergear a `main` uno después del otro (no al mismo
tiempo, para evitar conflictos en `dcpub/models.py`/`dcpub/app.py` que
tocan ambos).

Dentro de cada track, las tareas son secuenciales (modelo → render →
adaptadores → UI → verificación), igual que en la sub-fase de texto rico.

---

## Track A — `LineLayer`

**A1. Modelo:** agregar `LineLayer` a `dcpub/models.py` (campos: `length`,
`thickness`, `color`, `gap`, más los de `Layer` base: `x`,`y`,`rotation`,
`opacity`,`visible`,`locked`,`z`). Registrar `"line"` en `LAYER_CLASSES`.
Tests de defaults + round-trip `to_dict`/`from_dict`.

**A2. Render:** nueva rama `elif kind == "line":` en `compose()`
(`dcpub/render.py`) que dibuja el segmento (o par de segmentos si
`gap > 0`) centrado en `(x,y)`, con `length`/`thickness`/`color` propios,
respetando `rotation`/`opacity`. Reusar `_apply_rotation` de Fase 4
sub-fase 2 si aplica.

**A3. Adaptadores:** agregar la rama `"line"` en `_build_layers_for`
(`dcpub/app.py`) y `_layers_from_slide` (`dcpub/exporter.py`), mismos
campos que expone el modelo.

**A4. Panel de capas:** agregar botón "Agregar línea" (mismo patrón que
`_add_cta_layer`).

**A5. Panel de propiedades:** reconocer `kind == "line"` en `_kind_of` y
`_build_property_panel`, con sliders `length`/`thickness`/`gap` y color
picker (reusar `_color_picker` de Fase 4 sub-fase 1), sin el slider
genérico de tamaño de fuente.

**A6. Verificación headless de cierre** del track (script en
`verificaciones/`, mismo patrón que los anteriores).

---

## Track B — `DotsLayer`

**B1. Modelo:** agregar `DotsLayer` a `dcpub/models.py` (campos
persistidos: `color`, `spacing`; `count`/`active` NO se persisten, se
calculan al render). Registrar `"dots"` en `LAYER_CLASSES`.

**B2. Render:** nueva rama `elif kind == "dots":` en `compose()` que
dibuja `count` círculos separados por `spacing`, resaltando el índice
`active` (por ejemplo, más grande u opaco), centrados en `(x,y)`.

**B3. Adaptadores:** en `_build_layers_for` y `_layers_from_slide`, calcular
`count = len(project.slides)` y `active = current_slide_index` (o el índice
de la lámina que se está exportando, en el caso de export por lote) y
pasarlos junto con `color`/`spacing` del modelo.

**B4. Panel de capas:** botón "Agregar puntos de carrusel" — deshabilitado
o con aviso si el proyecto tiene una sola lámina (no tiene sentido en un
post simple).

**B5. Panel de propiedades:** reconocer `kind == "dots"`, sliders
`spacing` + color picker, sin tamaño de fuente. Mostrar `count`/`active`
como texto informativo (no editable).

**B6. Verificación headless de cierre** del track.

---

## Notas para Codex

- Seguir las convenciones de `CLAUDE.md` sección 8 (español, sin
  pseudocódigo, un módulo una responsabilidad).
- Cada tarea: TDD (test que falla → implementar → test pasa), un commit
  por tarea, mensaje en español, conventional commits, suite completa en
  verde antes de commitear (`python -m unittest discover -s tests -v`).
- Antes de fusionar cualquiera de los dos tracks a `main`, correr una
  revisión final de rama completa (mismo proceso que las fases anteriores:
  ver `.superpowers/sdd/progress.md` para el formato de bitácora esperado).
- Si al implementar alguna de las 6 decisiones de diseño de arriba resulta
  incorrecta o inviable, documentarlo explícitamente y consultar antes de
  improvisar una alternativa.
