# Diseño — Fase 4 (sub-fase 1): Caja CTA + recuadro de descripción configurable

Fecha: 2026-07-09
Roadmap: `AGENTS.md`/`CLAUDE.md` sección 6, Fase 4 — "Texto rico + capas nuevas"
(esta es la primera de varias sub-entregas de Fase 4; texto rico por elemento,
líneas decorativas y puntos de carrusel quedan para sub-fases posteriores)

## Contexto

Durante el testeo en vivo de Fase 1, el usuario pidió dos features concretas
que caen dentro de Fase 4 (ver memoria de proyecto `fase4-feedback-usuario`):

1. Una capa CTA (llamado a la acción) con color de caja, transparencia de
   caja y color de texto configurables.
2. El recuadro de descripción (`BoxLayer`) con ancho/alto/color propios en
   vez de los valores fijos actuales.

La exploración de código previa (`docs/superpowers/specs/2026-07-09-fase4-hallazgos.md`,
hecha por Codex) confirmó los hardcodes exactos: `box_w = int(W * 0.90)` en
`render.py:441`, `BOX_COLOR` fijo de `constants.py` usado directo en
`render.py:462`, texto siempre `BLANCO` en `render.py:469`. También confirmó
que `CTALayer` no existe todavía, pero `batch_import.py` ya guarda el CTA
importado como string suelto en `slide.extra["cta"]`, a la espera de que
exista la clase.

## Alcance

**Incluye:**
- `BoxLayer` gana campos `fill` (rgba) y `text_color` (rgba), y empieza a
  usar sus campos heredados `w`/`h` (hoy presentes pero ignorados por el
  render) para controlar tamaño real de la caja.
- Overflow de texto: si el contenido no entra en el `h` configurado, se
  dibuja igual por fuera de la caja (sin recortar, sin achicar fuente
  automáticamente).
- Nueva clase `CTALayer`: mismo estilo visual que `BoxLayer` (rectángulo
  redondeado, mismo `corner_r`), sin ícono, con `fill`/`text_color`/`size`
  propios.
- Botón "+ Agregar CTA" en el panel de capas, que crea una `CTALayer` con
  valores por defecto.
- `batch_import.py` crea una `CTALayer` real en `slide.layers` cuando el
  JSON importado trae un `cta` no vacío (en vez de dejarlo solo en
  `slide.extra["cta"]`).
- Migración automática al cargar proyectos viejos: `BoxLayer` con `w<=0` o
  `h<=0` se completa con los defaults nuevos al abrir el `.json`.
- Selector de color (nuevo patrón de UI: color picker + alpha) para `fill`
  y `text_color`, tanto en `desc` como en `cta`.

**No incluye (sub-fases futuras de Fase 4):**
- Fuente por elemento, bold/italic/underline, tracking, stroke — eso es la
  sub-fase de "texto rico", separada de esta.
- `rotation` aplicado de verdad al render (hoy es un campo fantasma, sigue
  sin aplicarse; no se toca en esta sub-fase).
- `LineLayer`/`DotsLayer` — sub-fase separada, más chica.
- Generalizar `TextLayer` (título/subtítulo) con estos mismos colores
  configurables — esta sub-fase solo toca `BoxLayer`/`CTALayer`.

## Modelo de datos (`dcpub/models.py`)

```python
@dataclass
class BoxLayer(Layer):
    type: str = "box"
    text: str = ""
    icon: str = "ninguno"
    size: float = 0.033
    fill: list = field(default_factory=lambda: list(BOX_COLOR))
    text_color: list = field(default_factory=lambda: list(BLANCO) + [255])


@dataclass
class CTALayer(Layer):
    type: str = "cta"
    text: str = ""
    size: float = 0.033
    fill: list = field(default_factory=lambda: list(BOX_COLOR))
    text_color: list = field(default_factory=lambda: list(BLANCO) + [255])
```

- `LAYER_CLASSES` (models.py:99-104) suma `"cta": CTALayer`.
- `LAYER_STYLE_FIELDS` (models.py:213-220): la entrada `("box", None)` ya
  incluye `w`/`h`; se le suman `fill` y `text_color`, quedando
  `("x", "y", "w", "h", "rotation", "opacity", "size", "icon", "fill", "text_color")`.
  Se agrega una entrada nueva `("cta", None): ("x", "y", "w", "h", "rotation", "opacity", "size", "fill", "text_color")`.
- `crear_slide_por_defecto` (models.py:180-193) fija explícitamente
  `w=0.90, h=0.12` en el `BoxLayer` por defecto (hoy no los fija, quedan en
  `0.0`/`0.0` heredados de `Layer`).

## Motor de render (`dcpub/render.py`)

Rama `"desc"` (línea 436 en adelante):
- `box_w = int(W * layer.get("w", 0) or W * 0.90)` — si `w` viene en `0` o
  ausente, cae al `0.90` legado.
- `box_h`: si `layer.get("h", 0) > 0`, usar `int(H * layer["h"])`; si no,
  mantener el cálculo automático actual desde texto/ícono/padding (líneas
  455-458), igual que hoy.
- El texto/ícono se siguen dibujando en las mismas coordenadas relativas
  aunque el contenido exceda `box_h` — sin clip, sin achicar fuente.
- `box_fill = _apply_opacity(layer.get("fill", BOX_COLOR), opacity)`.
- `text_color = _apply_opacity(layer.get("text_color", BLANCO + (255,)), opacity)`
  (nota: `fill`/`text_color` ya traen su propio alpha; `_apply_opacity`
  sigue aplicando la opacidad general de la capa encima, igual que hoy).

Rama nueva `"cta"`:
- Rectángulo redondeado con el mismo `corner_r` que `"desc"`
  (`int(W * 0.033)`), posición/tamaño desde `layer["x"]`, `layer["y"]`,
  `layer["w"]`, `layer["h"]` (fracciones del lienzo, sin fallback legado
  porque es una capa nueva sin proyectos viejos que migrar).
- Fill desde `layer["fill"]`, texto centrado horizontal y verticalmente
  dentro del rectángulo, color desde `layer["text_color"]`.
- Sin ícono, sin wrap complejo más allá del mismo `wrap_text` que ya usa
  `"desc"` para no desbordar horizontalmente.

`compose()` (docstring y dispatch, líneas 277-310): se documenta el nuevo
tipo `"cta"` igual que los demás.

## Adaptadores UI ↔ render

- `App._build_layers_for()` (app.py, rama `desc` ~1383-1389): suma `"w"`,
  `"h"`, `"fill"`, `"text_color"` al dict. Nueva rama para capas `type ==
  "cta"` que arma el dict `"cta"` completo.
- `Exporter._layers_from_slide()` (exporter.py, rama `desc` ~78-88): mismos
  campos nuevos. Nueva rama para `"cta"`.
- `dcpub/project_io.py` (carga de proyecto): al reconstruir cada `BoxLayer`
  desde JSON, si `w <= 0` o `h <= 0`, sobrescribir con los defaults nuevos
  (`0.90`, `0.12`) antes de dejarlo en memoria. Esto cubre los `.dcpub.json`
  de las verificaciones de Fase 1-3 sin que el usuario tenga que hacer nada.

## UI

**Panel de propiedades**, capa `desc`: se suman sliders de `w`/`h` (mismo
patrón que zoom/offset de la foto), un selector de color con alpha para
`fill`, y otro para `text_color`. El proyecto no tiene todavía ningún color
picker real (solo sliders numéricos) — se introduce por primera vez un
diálogo simple: `tkinter.colorchooser.askcolor()` para RGB + un slider
aparte de 0-255 (o 0.0-1.0) para el alpha, siguiendo el mismo patrón de
comando/undo que el resto (`DictItemChangeCommand` no aplica aquí porque
`fill`/`text_color` son atributos planos tipo `list`, no dicts anidados —
se usa `PropertyChangeCommand` normal, con el valor viejo/nuevo siendo la
lista `[r,g,b,a]` completa).

**Panel de propiedades**, capa `cta`: mismos controles que `desc` menos
`icon`.

**Panel de capas** (izquierda): botón nuevo "+ Agregar CTA", mismo patrón
que `_duplicate_layer` (app.py:508-519) pero creando una `CTALayer` nueva
con texto placeholder ("Reservá ahora"), tamaño/posición razonables, en vez
de clonar una capa existente.

## Importador por lotes (`dcpub/batch_import.py`)

Cuando `entrada.get("cta", "")` no está vacío: además de guardar el string
en `slide.extra["cta"]` (se mantiene, no se rompe compatibilidad), se
agrega una `CTALayer` real a `slide.layers` con ese texto y los colores
default de marca (`BOX_COLOR`, `BLANCO+(255,)`).

## Testing

- Modelo: `BoxLayer`/`CTALayer` serializan/deserializan `fill`/`text_color`
  (y `w`/`h` para `BoxLayer`) correctamente.
- Render: `"desc"` respeta `w`/`h`/`fill`/`text_color` cuando vienen
  seteados; cae a comportamiento legado cuando `w`/`h` vienen en `0`; rama
  `"cta"` nueva dibuja sin ícono, con fill/texto configurables.
- `project_io.py`: cargar un JSON con `BoxLayer` en `w=0,h=0` dejalo en
  memoria con los defaults nuevos tras `load_project()`.
- `batch_import.py`: JSON con `cta` no vacío produce una `CTALayer` real en
  `slide.layers`, no solo en `extra["cta"]`.
- Verificación headless de cierre con una lámina que use CTA + descripción
  con colores no default, para dejar evidencia visual.

## Riesgos / decisiones registradas

- El overflow de texto sin recorte es una decisión explícita: prioriza
  previsibilidad (el usuario ve el problema en la vista previa) sobre
  "que nunca se vea roto el diseño". Si en el uso real esto genera quejas,
  se puede revisar en una sub-fase posterior sin romper el modelo de datos.
- `CTALayer` se mantiene separada de `BoxLayer` por decisión explícita del
  usuario (no generalizar), aunque comparten casi todos los campos —
  duplicación aceptada a cambio de claridad conceptual (dos elementos con
  propósito distinto: informativo vs. llamada a la acción).
- El color picker es la primera vez que se introduce en el proyecto; se
  usa el diálogo nativo de tkinter (`colorchooser`) en vez de una paleta
  custom, para no inflar el alcance de esta sub-fase.
