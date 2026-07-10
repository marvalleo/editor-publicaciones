# Fase 4 (cierre) — Bloques de texto extra ("free") — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar el alcance de Fase 4 agregando bloques de texto libres,
independientes de título/subtítulo, con la misma tipografía rica
(fuente/bold/italic/underline/interlineado/tracking/stroke/rotación) ya
construida en la sub-fase de texto rico, más color propio configurable
(a diferencia de título/subtítulo, que tienen colores de marca fijos).

**Architecture:** `TextLayer` ya soporta `role="free"` por default y ya
tiene TODOS los campos de texto rico (son de la clase base, no
específicos de título/subtítulo) — solo le falta un campo `color`. El
render gana una rama `elif kind == "free":` que es un **pipeline único**
(a diferencia de título/subtítulo, acá no hay comportamiento legado que
preservar pixel a pixel porque es una capa nueva, así que no hace falta
el patrón dual-path). Reutiliza directamente `_render_text_lines_to_image`,
`_apply_italic_shear`, `_apply_rotation`, `BOLD_STROKE_FRACTION` y
`TEXT_STROKE_COLOR` de la sub-fase de texto rico. A diferencia de
título/subtítulo (una instancia canónica por lámina, ligada a widgets
fijos del panel izquierdo), los bloques libres son multi-instancia como
CTA/Línea/Puntos: se editan directamente en el panel de propiedades
(texto multilínea + color picker), no en el panel izquierdo.

**Tech Stack:** Python 3, Pillow, tkinter. Sin dependencias nuevas.

## Global Constraints

- Nombres y comentarios en español; código limpio y modular (CLAUDE.md sección 8).
- Sin pseudocódigo ni partes "por completar" dentro de una tarea entregada.
- Cada tarea termina con `python -m unittest discover -s tests -v` en verde antes de commitear.
- Un commit por tarea, mensaje en español, conventional commits.
- El bloque libre usa el rol `"free"` (default de `TextLayer`, sin cambios en el dataclass más allá del campo `color`).
- El render del bloque libre es un pipeline único, sin rama legado — no aplica el patrón dual-path de título/subtítulo porque no hay comportamiento previo que preservar.
- El bloque libre NO lleva sombra fija ni línea decorativa (esas son elementos de marca de título/subtítulo, no de un bloque de texto genérico).
- `_build_text_style_section` (panel de propiedades) ya es genérico — se reutiliza sin cambios para `kind == "free"`.
- No se toca `LAYER_STYLE_FIELDS` (copiar estilo entre láminas) — ni `line`/`dots` tienen entrada ahí tampoco; fuera de alcance de esta tarea, igual que en la sub-fase anterior.

---

### Task 1: Modelo — campo `color` en `TextLayer`

**Files:**
- Modify: `dcpub/models.py` (clase `TextLayer`)
- Modify: `tests/test_models_layer.py`

**Interfaces:**
- Produces: `TextLayer.color: list` (rgba, default blanco opaco). Usado por Task 2 (render) y Task 5 (panel de propiedades).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_models_layer.py`, dentro de `TestLayerSubclasses` (después de `test_text_layer_rich_text_defaults`):

```python
    def test_text_layer_free_block_has_configurable_color(self):
        t = TextLayer(text="Hola", role="free")
        self.assertEqual(t.color, [247, 241, 232, 255])
```

(`[247, 241, 232, 255]` es `BLANCO` de `dcpub/constants.py` + alpha 255 — mismo blanco crema de marca que usa el título.)

Y en `TestLayerFromDict::test_round_trip_each_subclass`, agregar un `TextLayer` de rol `"free"` con `color` no-default a la lista `layers`:

```python
            TextLayer(text="Bloque libre", role="free", color=[10, 20, 30, 200],
                      font_family="dancing", rotation=5.0),
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_models_layer -v`
Expected: FAIL — `AttributeError: 'TextLayer' object has no attribute 'color'`

- [ ] **Step 3: Implementar**

En `dcpub/models.py`, la clase `TextLayer` actual es:

```python
@dataclass
class TextLayer(Layer):
    type: str = "text"
    text: str = ""
    role: str = "free"
    size: float = 0.05
    font_family: str = ""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    line_spacing: float = 0.0
    letter_spacing: float = 0.0
    stroke_on: bool = False
    stroke_width: float = 0.0
```

Reemplazarla por:

```python
@dataclass
class TextLayer(Layer):
    type: str = "text"
    text: str = ""
    role: str = "free"
    size: float = 0.05
    font_family: str = ""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    line_spacing: float = 0.0
    letter_spacing: float = 0.0
    stroke_on: bool = False
    stroke_width: float = 0.0
    color: list = field(default_factory=lambda: list(BLANCO) + [255])
```

Confirmar que `BLANCO` ya está importado/definido en `dcpub/models.py` (se usa en `BoxLayer.text_color` y `CTALayer.text_color` con el mismo patrón `list(BLANCO) + [255]`) — si ya está, no hace falta agregar el import.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_models_layer -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/models.py tests/test_models_layer.py
git commit -m "feat: agregar color configurable a TextLayer para bloques de texto libres"
```

---

### Task 2: Render — rama `"free"` en `compose()`

**Files:**
- Modify: `dcpub/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `_render_text_lines_to_image`, `_apply_italic_shear`, `_apply_rotation`, `BOLD_STROKE_FRACTION`, `TEXT_STROKE_COLOR`, `wrap_text` (ya existentes).
- Produces: `compose()` acepta capas `{"type": "free", ...}` con los mismos campos que `"title"` más `"color"`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`:

```python
class TestFreeTextLayerRender(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "free", "key": "libre", "text": "Bloque de prueba",
                "x": 0.1, "y": 0.4, "size": 0.05, "opacity": 1.0,
                "color": [255, 0, 0, 255]}
        base.update(overrides)
        return base

    def test_defaults_produce_a_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        self.assertIn("libre", bboxes)

    def test_uses_own_color_not_brand_colors(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img, bboxes = compose([self._layer(color=[255, 0, 0, 255])], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["libre"]
        mid_x, mid_y = (x0 + x1) // 2, (y0 + y1) // 2
        pixel = img.getpixel((mid_x, mid_y))
        self.assertEqual(pixel[:3], (255, 0, 0))

    def test_no_forced_shadow_behind_text(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img, bboxes = compose(
            [self._layer(x=0.3, y=0.3, color=[255, 255, 255, 255])], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["libre"]
        # 3px a la derecha/abajo del bbox (offset de sombra de titulo/sub)
        # debe seguir transparente: un bloque libre no lleva sombra forzada.
        self.assertEqual(img.getpixel((x1 + 3, y1 + 3))[3], 0)

    def test_bold_italic_stroke_rotation_change_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_plain, _ = compose([self._layer()], (1000, 1000), fm)
        img_styled, _ = compose(
            [self._layer(bold=True, italic=True, stroke_on=True,
                         stroke_width=0.03, rotation=12.0)], (1000, 1000), fm)
        self.assertNotEqual(list(img_plain.getdata()), list(img_styled.getdata()))

    def test_font_family_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(font_family="")], (1000, 1000), fm)
        img_playfair, _ = compose([self._layer(font_family="playfair")], (1000, 1000), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_playfair.getdata()))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestFreeTextLayerRender -v`
Expected: FAIL — `KeyError: 'libre'` (no hay rama `"free"`, la capa se ignora)

- [ ] **Step 3: Implementar**

En `dcpub/render.py`, agregar la nueva rama inmediatamente antes de `elif kind == "desc":` (después de la rama `"dots"`, que termina con `bboxes[bbox_key] = (px, py, px + total_w, py + total_h)`):

```python
        elif kind == "free":
            text = layer["text"]
            if text.strip():
                tsz = max(8, int(W * layer.get("size", 0.05)))
                font_f = font_manager.load("body", tsz, family=layer.get("font_family", ""))
                tx = int(layer["x"] * W)
                ty = int(layer["y"] * H)
                max_w = W - tx - margin
                lines = []
                for part in text.split("\n"):
                    part = part.strip()
                    if part:
                        lines += wrap_text(part, font_f, max_w, draw)
                line_spacing = layer.get("line_spacing", 0) or 1.22
                lh = int(tsz * line_spacing)
                letter_spacing_px = int(tsz * layer.get("letter_spacing", 0))
                bold = layer.get("bold", False)
                stroke_on = layer.get("stroke_on", False)
                border_px = int(tsz * layer.get("stroke_width", 0)) if stroke_on else 0
                bold_px = int(tsz * BOLD_STROKE_FRACTION) if bold else 0
                stroke_width_total = border_px + bold_px

                text_color_value = layer.get("color", BLANCO + (255,))
                text_color = _apply_opacity(text_color_value, opacity)
                stroke_fill = (_apply_opacity(TEXT_STROKE_COLOR, opacity)
                               if stroke_on else text_color)

                block, pad = _render_text_lines_to_image(
                    lines, font_f, fill=text_color, line_height=lh,
                    letter_spacing_px=letter_spacing_px,
                    stroke_width=stroke_width_total, stroke_fill=stroke_fill,
                    underline=layer.get("underline", False), align="left")

                pre_w, pre_h = block.size
                center_x = (tx - pad) + pre_w / 2
                center_y = (ty - pad) + pre_h / 2

                if layer.get("italic", False):
                    block = _apply_italic_shear(block)
                rotation = layer.get("rotation", 0.0)
                if rotation:
                    block = _apply_rotation(block, rotation)

                paste_x = int(center_x - block.width / 2)
                paste_y = int(center_y - block.height / 2)
                canvas.alpha_composite(block, (paste_x, paste_y))
                draw = ImageDraw.Draw(canvas)

                widest = pre_w - 2 * pad
                bboxes[bbox_key] = (tx, ty, tx + max(widest, 10), ty + max(pre_h - 2 * pad, 1))

        elif kind == "desc":
```

Notar que `layer.get("color", BLANCO + (255,))` recibe una lista `[r,g,b,a]` desde el adaptador (Task 3) igual que `fill`/`text_color` en las ramas `"desc"`/`"cta"` — `_apply_opacity` ya acepta listas o tuplas indistintamente (ver su uso en esas ramas).

No se pasa `shadow_offset`/`shadow_fill` a `_render_text_lines_to_image` (quedan en su default `None`) — un bloque libre no lleva la sombra de marca fija que sí llevan título/subtítulo.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestFreeTextLayerRender -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: renderizar bloques de texto libre con pipeline de texto rico"
```

---

### Task 3: Adaptadores UI↔render — `_build_layers_for` y `Exporter._layers_from_slide`

**Files:**
- Modify: `dcpub/app.py` (`_build_layers_for`)
- Modify: `dcpub/exporter.py` (`_layers_from_slide`)
- Test: `tests/test_app_slides.py`, `tests/test_exporter.py`

**Interfaces:**
- Consumes: `TextLayer.color` (Task 1).
- Produces: preview y export pasan las capas `role == "free"` a `compose()` como `{"type": "free", ...}`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_slides.py` (nueva clase, después de `TestBuildLayersForDotsLayer` o similar):

```python
class TestBuildLayersForFreeText(unittest.TestCase):
    def test_build_layers_for_includes_free_text_block(self):
        from dcpub.models import TextLayer
        app = _make_app_with_two_slides()
        libre = TextLayer(name="Texto libre", role="free", text="Hola mundo",
                          x=0.2, y=0.6, size=0.04, color=[1, 2, 3, 200],
                          font_family="lato", bold=True, rotation=7.0)
        app.slide.layers.append(libre)

        layers = App._build_layers_for(app, app.slide)

        libre_capa = next(c for c in layers if c["type"] == "free")
        self.assertEqual(libre_capa["text"], "Hola mundo")
        self.assertEqual(libre_capa["color"], [1, 2, 3, 200])
        self.assertEqual(libre_capa["font_family"], "lato")
        self.assertTrue(libre_capa["bold"])
        self.assertEqual(libre_capa["rotation"], 7.0)
```

Agregar a `tests/test_exporter.py` (nueva clase):

```python
class TestLayersFromSlideFreeText(unittest.TestCase):
    def test_free_text_block_included_with_color(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto, TextLayer
        slide = crear_slide_por_defecto("foto.jpg")
        libre = TextLayer(name="Texto libre", role="free", text="Extra",
                          color=[9, 8, 7, 180], italic=True)
        slide.layers.append(libre)

        capas = _layers_from_slide(slide)

        libre_capa = next(c for c in capas if c["type"] == "free")
        self.assertEqual(libre_capa["text"], "Extra")
        self.assertEqual(libre_capa["color"], [9, 8, 7, 180])
        self.assertTrue(libre_capa["italic"])
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides.TestBuildLayersForFreeText tests.test_exporter.TestLayersFromSlideFreeText -v`
Expected: FAIL — `StopIteration` (no hay capa `"free"` en la lista devuelta)

- [ ] **Step 3: Implementar en `dcpub/app.py`**

En `_build_layers_for`, agregar un `elif` nuevo inmediatamente después de la rama `elif layer.type == "text" and layer.role == "subtitle":` (que termina con `"stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width})`) y antes de `elif layer.type == "box":`:

```python
            elif layer.type == "text" and layer.role == "free":
                layers.append({"type": "free", "key": layer.id, "text": layer.text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity, "rotation": layer.rotation,
                                "font_family": layer.font_family, "bold": layer.bold,
                                "italic": layer.italic, "underline": layer.underline,
                                "line_spacing": layer.line_spacing,
                                "letter_spacing": layer.letter_spacing,
                                "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width,
                                "color": layer.color})
```

- [ ] **Step 4: Implementar en `dcpub/exporter.py`**

En `_layers_from_slide`, agregar un `elif` nuevo inmediatamente después de la rama `elif layer.type == "text" and layer.role == "subtitle":` (que termina con `"stroke_width": layer.stroke_width,\n            })`) y antes de `elif layer.type == "box":`:

```python
        elif layer.type == "text" and layer.role == "free":
            layers.append({
                "type": "free",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "size": layer.size,
                "opacity": layer.opacity,
                "rotation": layer.rotation,
                "font_family": layer.font_family,
                "bold": layer.bold,
                "italic": layer.italic,
                "underline": layer.underline,
                "line_spacing": layer.line_spacing,
                "letter_spacing": layer.letter_spacing,
                "stroke_on": layer.stroke_on,
                "stroke_width": layer.stroke_width,
                "color": layer.color,
            })
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides.TestBuildLayersForFreeText tests.test_exporter.TestLayersFromSlideFreeText -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add dcpub/app.py dcpub/exporter.py tests/test_app_slides.py tests/test_exporter.py
git commit -m "feat: propagar bloques de texto libre en los adaptadores de render"
```

---

### Task 4: Panel de capas — botón "+ Agregar texto"

**Files:**
- Modify: `dcpub/app.py`
- Test: `tests/test_app_slides.py`

**Interfaces:**
- Produces: `App._add_text_layer()`. Botón en el panel izquierdo, mismo patrón que `_add_cta_layer`/`_add_line_layer`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_slides.py` (nueva clase):

```python
class TestAddTextLayer(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.calls = []
        self.app._build_property_panel = lambda: self.calls.append("props")
        self.app._refresh_layers_list = lambda: self.calls.append("layers")
        self.app._schedule_render = lambda: self.calls.append("render")

    def test_add_text_layer_appends_free_text_and_selects_it(self):
        App._add_text_layer(self.app)

        libre = self.app.slide.layers[-1]
        self.assertEqual(libre.type, "text")
        self.assertEqual(libre.role, "free")
        self.assertEqual(libre.name, "Texto")
        self.assertIs(self.app._selected, libre)
        self.assertEqual(self.calls, ["props", "layers", "render"])
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides.TestAddTextLayer -v`
Expected: FAIL — `AttributeError: type object 'App' has no attribute '_add_text_layer'`

- [ ] **Step 3: Implementar el método**

Agregar en `dcpub/app.py`, inmediatamente después de `_add_dots_layer` (que termina con `self._schedule_render()`):

```python
    def _add_text_layer(self):
        from .models import TextLayer
        from .commands import AddLayerCommand
        new_z = max((l.z for l in self.slide.layers), default=0) + 1
        new_layer = TextLayer(name="Texto", role="free", z=new_z,
                               text="Texto libre", x=0.10, y=0.50, size=0.04)
        index = len(self.slide.layers)
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._selected = new_layer
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()
```

- [ ] **Step 4: Agregar el botón**

En `dcpub/app.py`, el bloque actual de botones es:

```python
        tk.Button(left, text="+ Agregar CTA", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_cta_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar línea", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_line_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar puntos", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_dots_layer).pack(
            fill=tk.X, pady=(0, 10), **pad)
```

Reemplazarlo por:

```python
        tk.Button(left, text="+ Agregar CTA", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_cta_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar línea", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_line_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar puntos", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_dots_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar texto", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_text_layer).pack(
            fill=tk.X, pady=(0, 10), **pad)
```

(Nota: el `pady` de "Agregar puntos" pasa de `(0, 10)` a `(0, 4)` porque deja de ser el último botón del grupo; "Agregar texto" hereda el `(0, 10)` de cierre de grupo.)

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides.TestAddTextLayer -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add dcpub/app.py tests/test_app_slides.py
git commit -m "feat: agregar boton para crear bloques de texto libre"
```

---

### Task 5: Panel de propiedades — reconocer `"free"`, texto multilínea + color

**Files:**
- Modify: `dcpub/app.py` (`_kind_of`, `SIZE_RANGE`, `LABELS`, `_build_property_panel`, nuevo método `_on_free_text_commit`)
- Test: `tests/test_app_property_panel.py`

**Interfaces:**
- Consumes: `_build_text_style_section` (ya genérico, sub-fase de texto rico), `_color_picker` (ya genérico, sub-fase CTA+caja).
- Produces: seleccionar un bloque libre muestra campo de texto multilínea, color, fuente/bold/italic/underline/stroke, interlineado/tracking/rotación, tamaño y opacidad.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_property_panel.py`:

```python
class TestKindOfFreeText(unittest.TestCase):
    def test_kind_of_free_text_layer_is_free(self):
        from dcpub.models import TextLayer
        app = App.__new__(App)

        self.assertEqual(App._kind_of(app, TextLayer(role="free")), "free")


class TestSizeRangeAndLabelsIncludeFreeText(unittest.TestCase):
    def test_free_has_size_range(self):
        from dcpub.app import SIZE_RANGE
        self.assertIn("free", SIZE_RANGE)

    def test_free_has_label(self):
        from dcpub.app import LABELS
        self.assertEqual(LABELS["free"], "Texto")


class TestFreeTextCommit(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack
        from dcpub.models import TextLayer
        self.app = App.__new__(App)
        self.app.commands = CommandStack()
        self.app._schedule_render = lambda: None
        self.layer = TextLayer(role="free", text="Original")

    def test_commit_changes_text_and_is_undoable(self):
        App._on_cta_text_commit(self.app, self.layer, "Original", "Nuevo texto")
        self.assertEqual(self.layer.text, "Nuevo texto")
        self.app.commands.undo()
        self.assertEqual(self.layer.text, "Original")
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_property_panel.TestKindOfFreeText tests.test_app_property_panel.TestSizeRangeAndLabelsIncludeFreeText -v`
Expected: FAIL — `_kind_of` devuelve `None` para `TextLayer(role="free")`; `SIZE_RANGE`/`LABELS` no tienen clave `"free"`

(`TestFreeTextCommit` ya debería pasar sin cambios porque reutiliza `_on_cta_text_commit`, que es genérico — sirve como confirmación de que no hace falta un método nuevo para el commit de texto.)

- [ ] **Step 3: `_kind_of` reconoce `"free"`**

En `dcpub/app.py`, el bloque actual de `_kind_of` es:

```python
        if layer.type == "dots":
            return "dots"
        return None
```

Reemplazarlo por:

```python
        if layer.type == "dots":
            return "dots"
        if layer.type == "text" and layer.role == "free":
            return "free"
        return None
```

- [ ] **Step 4: `SIZE_RANGE` y `LABELS`**

El bloque actual es:

```python
SIZE_RANGE = {
    "logo":  (0.08, 0.40),
    "title": (0.03, 0.16),
    "sub":   (0.02, 0.10),
    "desc":  (0.015, 0.07),
    "cta":   (0.015, 0.07),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción",
          "cta": "CTA", "line": "Línea", "dots": "Puntos"}
```

Reemplazarlo por:

```python
SIZE_RANGE = {
    "logo":  (0.08, 0.40),
    "title": (0.03, 0.16),
    "sub":   (0.02, 0.10),
    "desc":  (0.015, 0.07),
    "cta":   (0.015, 0.07),
    "free":  (0.02, 0.12),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción",
          "cta": "CTA", "line": "Línea", "dots": "Puntos", "free": "Texto"}
```

- [ ] **Step 5: Sección de UI en `_build_property_panel`**

El bloque actual (tras la Tarea 4 de líneas/puntos) es:

```python
        if kind == "cta":
            tk.Label(card, text="Texto del CTA", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
            cta_text_var = tk.StringVar(value=layer.text)
            cta_entry = tk.Entry(card, textvariable=cta_text_var, bg=FIELD, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=2,
                                  font=("Segoe UI", 9),
                                  state=tk.DISABLED if disabled else tk.NORMAL)
            cta_entry.pack(fill=tk.X)
            cta_entry.bind(
                "<Return>",
                lambda e, l=layer, old=layer.text, v=cta_text_var:
                    self._on_cta_text_commit(l, old, v.get()))
            cta_entry.bind(
                "<FocusOut>",
                lambda e, l=layer, old=layer.text, v=cta_text_var:
                    self._on_cta_text_commit(l, old, v.get()))
        if kind in ("title", "sub"):
            self._build_text_style_section(card, layer, token, disabled)
        if kind not in ("line", "dots"):
            self._slider(card, token, "size", size_label, smin, smax, disabled=disabled)
```

Reemplazarlo por:

```python
        if kind == "cta":
            tk.Label(card, text="Texto del CTA", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
            cta_text_var = tk.StringVar(value=layer.text)
            cta_entry = tk.Entry(card, textvariable=cta_text_var, bg=FIELD, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=2,
                                  font=("Segoe UI", 9),
                                  state=tk.DISABLED if disabled else tk.NORMAL)
            cta_entry.pack(fill=tk.X)
            cta_entry.bind(
                "<Return>",
                lambda e, l=layer, old=layer.text, v=cta_text_var:
                    self._on_cta_text_commit(l, old, v.get()))
            cta_entry.bind(
                "<FocusOut>",
                lambda e, l=layer, old=layer.text, v=cta_text_var:
                    self._on_cta_text_commit(l, old, v.get()))
        if kind == "free":
            tk.Label(card, text="Texto", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
            free_text = tk.Text(card, height=3, bg=FIELD, fg=TEXT,
                                 insertbackground=TEXT, relief="flat", bd=2,
                                 font=("Segoe UI", 9),
                                 state=tk.DISABLED if disabled else tk.NORMAL)
            free_text.insert("1.0", layer.text)
            free_text.pack(fill=tk.X, pady=(2, 6))
            free_text.bind(
                "<FocusOut>",
                lambda e, l=layer, old=layer.text, w=free_text:
                    self._on_cta_text_commit(l, old, w.get("1.0", "end-1c")))
            self._color_picker(card, layer, "color", "Color del texto", disabled=disabled)
        if kind in ("title", "sub", "free"):
            self._build_text_style_section(card, layer, token, disabled)
        if kind not in ("line", "dots"):
            self._slider(card, token, "size", size_label, smin, smax, disabled=disabled)
```

`_on_cta_text_commit` es genérico (recibe `layer`, `old_value`, `new_value`, empuja un `PropertyChangeCommand` sobre `"text"`) — no hace falta un método nuevo pese al nombre, ya se reutiliza igual que para CTA.

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_property_panel -v`
Expected: PASS

- [ ] **Step 7: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK — prestar atención a que los tests existentes de `_build_property_panel` con mocks no rompan por el nuevo `tk.Text` (mismo patrón de widgets que el resto del panel).

- [ ] **Step 8: Commit**

```bash
git add dcpub/app.py tests/test_app_property_panel.py
git commit -m "feat: reconocer bloques de texto libre en el panel de propiedades"
```

---

### Task 6: Verificación headless de cierre de esta sub-fase

**Files:**
- Create: `verificaciones/fase4_texto_libre_verificacion.py`

**Interfaces:**
- Consumes: todo lo anterior (Tasks 1-5).
- Produces: carpeta `verificaciones/fase4_texto_libre_control/` con imágenes de control y `HEADLESS_OK`.

- [ ] **Step 1: Escribir el script**

Crear `verificaciones/fase4_texto_libre_verificacion.py`, siguiendo el
patrón de `verificaciones/fase4_lineas_puntos_verificacion.py`:

```python
"""Verificación headless de Fase 4 (cierre): bloques de texto libre.
No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.fonts import FontManager
from dcpub.models import crear_proyecto_por_defecto, TextLayer
from dcpub.project_io import save_project, load_project
from dcpub.render import compose
from dcpub.exporter import _layers_from_slide

OUT_DIR = Path(__file__).resolve().parent / "fase4_texto_libre_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    slide = project.slides[0]
    canvas_size = (slide.format["w"], slide.format["h"])
    font_manager = FontManager()

    libre = TextLayer(name="Texto libre", role="free", z=50,
                       text="Bloque libre\nsegunda linea", x=0.10, y=0.15,
                       size=0.045, color=[255, 210, 0, 255],
                       font_family="dancing", bold=True, italic=True,
                       stroke_on=True, stroke_width=0.02, rotation=-6.0)
    slide.layers.append(libre)
    libre.id = "s01_free_01"

    layers = _layers_from_slide(slide)
    render, bboxes = compose(layers, canvas_size, font_manager, palette=project.palette)
    render.save(OUT_DIR / "texto_libre.png")

    assert libre.id in bboxes, "el bloque de texto libre debe producir bbox"

    neutral_layers = [l for l in layers if l["type"] != "free"]
    neutral, _ = compose(neutral_layers, canvas_size, font_manager, palette=project.palette)
    diff = ImageChops.difference(neutral.convert("RGB"), render.convert("RGB"))
    assert diff.getbbox() is not None, "el bloque libre debe cambiar el render"

    project_path = OUT_DIR / "fase4_texto_libre.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    roles = [l.role for l in reloaded.slides[0].layers if l.type == "text"]
    assert "free" in roles

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el script**

Run: `python verificaciones/fase4_texto_libre_verificacion.py`
Expected: imprime `HEADLESS_OK` y la ruta de salida, sin `AssertionError` ni excepciones

- [ ] **Step 3: Revisar visualmente**

Abrir `texto_libre.png` en `verificaciones/fase4_texto_libre_control/` y
confirmar que se ve un bloque de texto amarillo, en cursiva/negrita, con
contorno y rotado, distinto del título/subtítulo de marca.

- [ ] **Step 4: Correr toda la suite una vez más**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 5: Actualizar la bitácora de progreso**

Agregar al final de `.superpowers/sdd/progress.md` una sección
`# Progreso — Fase 4 (cierre): bloques de texto libre` listando las 6
tareas como `complete`, y un `Veredicto: pendiente de revision final de
rama completa.` — seguir el mismo formato usado en las secciones
anteriores de este archivo (no duplicar encabezados existentes).

- [ ] **Step 6: Commit**

```bash
git add verificaciones/fase4_texto_libre_verificacion.py verificaciones/fase4_texto_libre_control .superpowers/sdd/progress.md
git commit -m "test: agregar verificacion headless de cierre de bloques de texto libre"
```

---

## Revisión final de rama (después de la Task 6)

Antes de mergear a `main`, correr una revisión de código completa,
prestando especial atención a:

- Que el bloque libre reutilice de verdad el pipeline de texto rico
  (mismos helpers que título/subtítulo) sin duplicar lógica.
- Que el color configurable no rompa nada de título/subtítulo (que
  siguen con colores fijos, sin campo `color` en su propio flujo — el
  campo nuevo es de `TextLayer` en general pero título/subtítulo lo
  ignoran en su rama de render).
- Consistencia entre preview y export para bloques libres con texto
  rico activo (mismos campos, mismo resultado).
- Que agregar múltiples bloques libres en la misma lámina funcione bien
  (selección independiente por `layer.id`, sin colisión con el patrón
  de instancia canónica de título/subtítulo).
