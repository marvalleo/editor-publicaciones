# Diseño — Fase 3: Edición de foto base

Fecha: 2026-07-09
Roadmap: `CLAUDE.md` sección 6, Fase 3 — "Edición de foto base"

## Contexto

El motor de render (`dcpub/render.py`) ya soporta ajustes fotográficos completos
(brillo, contraste, saturación, calidez, nitidez, sombras, viñeta) y overlays
de degradado (superior/inferior + intensidad) sobre `PhotoLayer`, con tests
propios en `tests/test_render_adjust.py`. El modelo (`dcpub/models.py`) ya
tiene los campos `adjust: dict` y `overlay: dict` con sus defaults
(`DEFAULT_PHOTO_ADJUST`, `DEFAULT_PHOTO_OVERLAY`).

Zoom y posición de recorte (`zoom`, `offset_x`, `offset_y`) ya tienen sliders
en el panel de propiedades desde Fase 1/2.

Lo que falta para cerrar la Fase 3:

1. Un bug bloqueante: el adaptador `App._build_layers()` arma el dict de la
   capa `photo` para `render.compose()` sin incluir `adjust` ni `overlay`.
   Hoy esos valores existen en el modelo pero nunca se renderizan — están
   muertos. Cualquier UI nueva no tendría efecto visible hasta corregir esto.
2. UI para los 7 controles de ajuste + overlay en el panel de propiedades.
3. Interacción directa de encuadre: arrastrar la foto en el canvas y usar la
   rueda del mouse para zoom, además de los sliders existentes.
4. Soporte de undo/redo para valores dentro de dicts anidados (`adjust`,
   `overlay`), que el sistema de comandos actual no cubre (solo atributos
   planos vía `setattr`).

## Alcance

**Incluye:**
- Fix del bug de `_build_layers` (con test de regresión).
- Sección colapsable "Ajustes" en el panel de propiedades de la capa foto,
  con los 7 sliders de `adjust` + overlay (2 checkboxes + 1 slider de
  intensidad) + botón "Restablecer".
- Rangos de cada control en `constants.py` (`ADJUST_RANGE`), alineados a los
  clamps que ya usa `render.py`.
- Nuevo comando `DictItemChangeCommand` para valores dentro de dicts
  anidados, reversible igual que `PropertyChangeCommand`.
- Extensión de `_get_layer_value`/`_set_layer_value` para reconocer params
  con prefijo `"adjust."` / `"overlay."` y delegar al dict correspondiente,
  sin duplicar el flujo de sliders/undo existente.
- Drag sobre la foto en el canvas: panea el contenido (cambia `offset_x`/
  `offset_y`), no mueve la capa como si fuera libre — la foto sigue cubriendo
  siempre el lienzo tipo `cover`, sin deformarse.
- Rueda del mouse sobre la foto: ajusta `zoom` dentro de [1.0, 3.0].
- Actualización de la verificación headless de cierre de fase.

**No incluye (fuera de alcance, otra fase):**
- Caja CTA y recuadro de descripción configurable (ancho/alto/color) —
  quedan para Fase 4, ya registrados en memoria de proyecto.
- Recorte por selección de área libre (crop rectangular tipo Photoshop) — el
  encuadre sigue siendo cover + zoom + offset, no un recorte arbitrario.
- Persistencia del estado colapsado/expandido del panel entre sesiones.

## Componentes y cambios

### 1. `dcpub/app.py::_build_layers()` (fix)

Agregar `"adjust": layer.adjust, "overlay": layer.overlay` al dict que arma
para la capa `photo`, tanto para la lámina activa como para las demás
(exportación de carrusel / miniaturas ya usan esta misma función).

### 2. `dcpub/constants.py`

```python
ADJUST_RANGE = {
    "brightness": (0.0, 2.0),
    "contrast": (0.0, 2.0),
    "saturation": (0.0, 2.0),
    "warmth": (-1.0, 1.0),
    "sharpness": (0.0, 2.0),
    "shadows": (-1.0, 1.0),
    "vignette": (0.0, 1.0),
}
ADJUST_LABELS = {
    "brightness": "Brillo", "contrast": "Contraste", "saturation": "Saturación",
    "warmth": "Calidez", "sharpness": "Nitidez", "shadows": "Sombras",
    "vignette": "Viñeta",
}
OVERLAY_STRENGTH_RANGE = (0.0, 1.0)
```

### 3. `dcpub/commands.py`

```python
class DictItemChangeCommand:
    """Como PropertyChangeCommand pero para un valor dentro de un dict
    (adjust/overlay de PhotoLayer), reversible igual."""
    def __init__(self, target_dict, key, old_value, new_value):
        self.target_dict = target_dict
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

    def execute(self):
        self.target_dict[self.key] = self.new_value

    def undo(self):
        self.target_dict[self.key] = self.old_value
```

### 4. `dcpub/app.py` — `_get_layer_value` / `_set_layer_value`

Reconocer params con prefijo `"adjust."` o `"overlay."`:

```python
def _get_layer_value(self, elem, param):
    layer = self._layer_by_token(elem)
    if "." in param:
        group, key = param.split(".", 1)
        return getattr(layer, group)[key]
    if self._kind_of(layer) == "logo" and param == "size":
        return layer.w
    return getattr(layer, param)

def _set_layer_value(self, elem, param, value):
    layer = self._layer_by_token(elem)
    if "." in param:
        group, key = param.split(".", 1)
        getattr(layer, group)[key] = value
        return
    ...
```

Los puntos donde se construye el `Command` a partir de `old_value`/`new_value`
(`_on_entry_commit`, `_on_slider_release`) también deben detectar el `"."` en
`param` y usar `DictItemChangeCommand(getattr(layer, group), key, ...)` en
vez de `PropertyChangeCommand(layer, param, ...)`.

### 5. `dcpub/app.py` — panel de propiedades

Dentro del bloque `if kind == "photo":`, después de los sliders existentes
(zoom, offset_x, offset_y, opacidad), agregar una sección colapsable única
"Ajustes" (`BooleanVar` en memoria, arranca colapsada) que contiene, en este
orden:
- 7 sliders de `adjust.*` usando `ADJUST_RANGE`/`ADJUST_LABELS`.
- Separador visual.
- 2 `Checkbutton` para `overlay.bottom_grad` / `overlay.top_grad` (siguiendo
  el patrón ya usado para "Usar en todo el carrusel").
- 1 slider para `overlay.strength` (`OVERLAY_STRENGTH_RANGE`).
- Botón "Restablecer" que empuja un `CompositeCommand` con un
  `DictItemChangeCommand` por cada clave de `adjust` (vuelta a
  `DEFAULT_PHOTO_ADJUST`), y refresca los sliders (`_sync_sliders`).

Los checkboxes de overlay necesitan su propio manejador (no pasan por
`_slider`), pero reutilizan `DictItemChangeCommand` igual al hacer toggle.

### 6. `dcpub/app.py` — interacción de canvas

**Drag (panear):**
- `_on_press`: si el punto cae sobre la foto y no hay otra capa encima ni
  está bloqueada, setear `self._drag_elem = "__photo_pan__"` y guardar
  `self._drag_start_offset = (layer.offset_x, layer.offset_y)`.
- `_on_drag`: si `self._drag_elem == "__photo_pan__"`, traducir el delta de
  mouse en px de imagen a delta de offset fraccional, invertido (arrastrar a
  la derecha revela contenido a la izquierda), escalado por el zoom actual
  del área "excedente" (misma matemática que ya usa `_get_background` en
  `render.py` para `crop_x`/`crop_y`). Clampear a [0.0, 1.0]. Actualiza
  directo sobre `layer.offset_x/offset_y` (sin Command todavía) y llama
  `_schedule_render()`, igual que el drag de otras capas.
- `_on_release`: si el modo era `"__photo_pan__"`, comparar offset inicial
  vs. final y empujar un único `CompositeCommand` con dos
  `DictItemChangeCommand`... **no** — `offset_x`/`offset_y` son atributos
  planos de `PhotoLayer` (no están dentro de un dict), así que se usa
  `PropertyChangeCommand` normal para cada uno, agrupados en
  `CompositeCommand`. (Distinto de `adjust`/`overlay`, que sí son dict.)

**Rueda del mouse (zoom):**
- `bind` de `<MouseWheel>` en el canvas principal (no `bind_all`), activo
  solo cuando el cursor está sobre el bbox de la foto y esta no está
  bloqueada.
- Cada evento de rueda ajusta `zoom` en pasos de `0.1`, clamp `[1.0, 3.0]`.
- Para no generar un paso de undo por cada tick de rueda, se agrupa con un
  debounce corto (~400ms sin nuevos eventos de rueda) antes de empujar el
  `PropertyChangeCommand` final, comparando el valor de `zoom` al primer
  evento del gesto contra el valor al finalizar el debounce.

### 7. Testing

- `tests/test_app_build_layers.py` (o extensión de uno existente): confirma
  que `adjust`/`overlay` de una `PhotoLayer` llegan al dict que
  `_build_layers` produce.
- `tests/test_commands.py`: casos de `DictItemChangeCommand` (execute/undo,
  incluida su combinación dentro de `CompositeCommand`).
- Tests puros (sin tkinter) para la función que traduce delta de mouse →
  delta de offset, y para el clamp de zoom por rueda.
- Verificación headless de cierre (`verificaciones/fase3_cierre_control/`):
  una lámina con ajustes fotográficos no neutros y overlay activo, para
  dejar evidencia visual de que el render final refleja los valores.

## Riesgos / decisiones registradas

- El drag de foto y el drag de capas normales comparten `_on_press`/
  `_on_drag`/`_on_release`, pero divergen en el tipo de comando final
  (`CompositeCommand` de `PropertyChangeCommand` vs. de
  `DictItemChangeCommand`). Se mantiene en el mismo método para no duplicar
  la lógica de conversión canvas↔imagen y snapping, discriminando por un
  sentinel (`"__photo_pan__"`) en vez de crear un segundo handler paralelo.
- El debounce de rueda usa `after()` de tkinter (ya se usa en otras partes
  del proyecto para `_schedule_render`), no un thread ni polling externo.
