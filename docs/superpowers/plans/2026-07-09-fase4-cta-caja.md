# Fase 4 (sub-fase 1) — CTA + caja de descripción configurable — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar `CTALayer` (nueva capa de llamado a la acción) y hacer que `BoxLayer` (recuadro de descripción) tenga ancho/alto/color de caja/color de texto configurables, en vez de los valores fijos actuales (`box_w = int(W * 0.90)`, `BOX_COLOR`, `BLANCO`).

**Architecture:** El modelo gana campos nuevos (`fill`, `text_color` en `BoxLayer`; clase `CTALayer` completa). El motor de render (`compose()`) lee esos campos con fallback al comportamiento legado para no romper proyectos guardados. Los dos adaptadores UI↔render (`App._build_layers_for` y `Exporter._layers_from_slide`) y el importador por lotes se actualizan en paralelo. La UI suma: sliders de w/h, un control de color reutilizable (nuevo patrón, primera vez que se usa `colorchooser` en el proyecto), un campo de texto para CTA en el propio panel de propiedades (no hay widget dedicado en el panel izquierdo, a diferencia de título/subtítulo/descripción), y un botón "+ Agregar CTA".

**Tech Stack:** Python 3, tkinter (incluye `tkinter.colorchooser`, no usado hasta ahora en el proyecto), Pillow. Sin dependencias nuevas.

## Global Constraints

- Nombres y comentarios en español; código limpio y modular (CLAUDE.md sección 8).
- Sin pseudocódigo ni partes "por completar" dentro de una tarea entregada.
- Cada tarea termina con `python -m unittest discover -s tests -v` en verde antes de commitear.
- Un commit por tarea, mensaje en español, conventional commits.
- `CTALayer` es una clase separada de `BoxLayer` (decisión explícita del usuario, no generalizar pese a la superposición de campos).
- El texto que no entra en el alto configurado de la caja se dibuja igual, sin recortar ni achicar la fuente (overflow visible).
- `fill`/`text_color` son listas `[r,g,b,a]` con su propio alpha, independientes de `opacity` (que sigue aplicando encima, vía `_apply_opacity`).
- Los proyectos `.dcpub.json` viejos (con `BoxLayer.w=0, h=0`) deben seguir abriendo y viéndose igual que antes — migración automática y silenciosa al cargar.
- `CTALayer` no lleva ícono.

---

### Task 1: Modelo de datos — `BoxLayer.fill`/`text_color` + `CTALayer` nueva

**Files:**
- Modify: `dcpub/models.py` (clase `BoxLayer`, `LAYER_CLASSES`, `LAYER_STYLE_FIELDS`, `crear_slide_por_defecto`)
- Modify: `tests/test_models_layer.py` (ya existe, con `TestLayerSubclasses` y `TestLayerFromDict`; se le agregan tests de los campos nuevos)

**Interfaces:**
- Produces: `BoxLayer.fill: list`, `BoxLayer.text_color: list`; nueva clase `CTALayer(Layer)` con `type="cta"`, `text`, `size`, `fill`, `text_color`; `LAYER_CLASSES["cta"] = CTALayer`; `LAYER_STYLE_FIELDS[("box", None)]` y `LAYER_STYLE_FIELDS[("cta", None)]` actualizadas. Usado por todas las tareas siguientes.

- [ ] **Step 1: Actualizar el import y escribir los tests que fallan**

En `tests/test_models_layer.py`, la línea de import (línea 5-7) es:

```python
from dcpub.models import (
    Layer, PhotoLayer, LogoLayer, TextLayer, BoxLayer, layer_from_dict,
)
```

Reemplazarla por:

```python
from dcpub.models import (
    Layer, PhotoLayer, LogoLayer, TextLayer, BoxLayer, CTALayer, layer_from_dict,
)
```

Agregar estos tests dentro de la clase `TestLayerSubclasses` ya existente, después de `test_box_layer_defaults` (línea 47-50):

```python
    def test_box_layer_fill_and_text_color_defaults(self):
        from dcpub.constants import BOX_COLOR, BLANCO
        b = BoxLayer()
        self.assertEqual(b.fill, list(BOX_COLOR))
        self.assertEqual(b.text_color, list(BLANCO) + [255])

    def test_cta_layer_defaults(self):
        from dcpub.constants import BOX_COLOR, BLANCO
        c = CTALayer()
        self.assertEqual(c.type, "cta")
        self.assertEqual(c.text, "")
        self.assertEqual(c.fill, list(BOX_COLOR))
        self.assertEqual(c.text_color, list(BLANCO) + [255])
```

Y agregar `CTALayer(text="Reservá ahora")` a la lista de `test_round_trip_each_subclass`
(dentro de `TestLayerFromDict`, línea 84-94), cuyo cuerpo actual es:

```python
    def test_round_trip_each_subclass(self):
        layers = [
            PhotoLayer(src="a.jpg"),
            LogoLayer(src="logo.png"),
            TextLayer(text="T", role="subtitle"),
            BoxLayer(text="D", icon="corazón"),
        ]
        for layer in layers:
            restored = layer_from_dict(layer.to_dict())
            self.assertIs(type(restored), type(layer))
            self.assertEqual(restored.to_dict(), layer.to_dict())
```

Reemplazarlo por:

```python
    def test_round_trip_each_subclass(self):
        layers = [
            PhotoLayer(src="a.jpg"),
            LogoLayer(src="logo.png"),
            TextLayer(text="T", role="subtitle"),
            BoxLayer(text="D", icon="corazón", fill=[1, 2, 3, 100],
                     text_color=[4, 5, 6, 200]),
            CTALayer(text="Reservá ahora", fill=[9, 9, 9, 200]),
        ]
        for layer in layers:
            restored = layer_from_dict(layer.to_dict())
            self.assertIs(type(restored), type(layer))
            self.assertEqual(restored.to_dict(), layer.to_dict())
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_models_layer -v`
Expected: FAIL — `ImportError: cannot import name 'CTALayer'`

- [ ] **Step 3: Implementar — `BoxLayer` gana `fill`/`text_color`**

En `dcpub/models.py`, la clase actual es:

```python
@dataclass
class BoxLayer(Layer):
    type: str = "box"
    text: str = ""
    icon: str = "ninguno"
    size: float = 0.033
```

Reemplazarla por:

```python
@dataclass
class BoxLayer(Layer):
    type: str = "box"
    text: str = ""
    icon: str = "ninguno"
    size: float = 0.033
    fill: list = field(default_factory=lambda: list(BOX_COLOR))
    text_color: list = field(default_factory=lambda: list(BLANCO) + [255])
```

(`BOX_COLOR` y `BLANCO` ya están importados al inicio del archivo, línea 7: `from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE`.)

- [ ] **Step 4: Implementar — nueva clase `CTALayer`**

Inmediatamente después de la clase `BoxLayer` (antes de `LAYER_CLASSES = {`), agregar:

```python
@dataclass
class CTALayer(Layer):
    type: str = "cta"
    text: str = ""
    size: float = 0.033
    fill: list = field(default_factory=lambda: list(BOX_COLOR))
    text_color: list = field(default_factory=lambda: list(BLANCO) + [255])
```

- [ ] **Step 5: Registrar en `LAYER_CLASSES`**

Reemplazar:

```python
LAYER_CLASSES = {
    "photo": PhotoLayer,
    "logo": LogoLayer,
    "text": TextLayer,
    "box": BoxLayer,
}
```

por:

```python
LAYER_CLASSES = {
    "photo": PhotoLayer,
    "logo": LogoLayer,
    "text": TextLayer,
    "box": BoxLayer,
    "cta": CTALayer,
}
```

- [ ] **Step 6: Actualizar `LAYER_STYLE_FIELDS`**

Reemplazar:

```python
LAYER_STYLE_FIELDS = {
    ("photo", None): ("x", "y", "w", "h", "rotation", "opacity",
                       "fit", "zoom", "offset_x", "offset_y", "adjust", "overlay"),
    ("logo", None): ("x", "y", "w", "h", "rotation", "opacity", "keep_ratio"),
    ("text", "title"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("text", "subtitle"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("box", None): ("x", "y", "w", "h", "rotation", "opacity", "size", "icon"),
}
```

por:

```python
LAYER_STYLE_FIELDS = {
    ("photo", None): ("x", "y", "w", "h", "rotation", "opacity",
                       "fit", "zoom", "offset_x", "offset_y", "adjust", "overlay"),
    ("logo", None): ("x", "y", "w", "h", "rotation", "opacity", "keep_ratio"),
    ("text", "title"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("text", "subtitle"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("box", None): ("x", "y", "w", "h", "rotation", "opacity", "size", "icon",
                     "fill", "text_color"),
    ("cta", None): ("x", "y", "w", "h", "rotation", "opacity", "size",
                     "fill", "text_color"),
}
```

- [ ] **Step 7: Fijar `w`/`h` explícitos en el `BoxLayer` por defecto**

En `crear_slide_por_defecto`, la línea actual es:

```python
        BoxLayer(name="Descripción", z=4, x=0.05, y=0.808,
                 size=0.033, text=descripcion, icon="planta"),
```

Reemplazarla por:

```python
        BoxLayer(name="Descripción", z=4, x=0.05, y=0.808, w=0.90, h=0.12,
                 size=0.033, text=descripcion, icon="planta"),
```

- [ ] **Step 8: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_models_layer -v`
Expected: PASS

- [ ] **Step 9: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK (puede haber tests preexistentes de `crear_slide_por_defecto` que verifiquen `BoxLayer.w`/`h`; si alguno falla por asumir `0.0`, es una actualización legítima de ese test para reflejar el nuevo default — ajustarlo, no revertir el Step 7)

- [ ] **Step 10: Commit**

```bash
git add dcpub/models.py tests/test_models_layer.py
git commit -m "feat: agregar fill/text_color a BoxLayer y nueva clase CTALayer"
```

---

### Task 2: Render — `BoxLayer` usa `w`/`h`/`fill`/`text_color` con fallback legado

**Files:**
- Modify: `dcpub/render.py` (rama `elif kind == "desc":`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: nada nuevo de tareas anteriores (cambio autocontenido en `render.py`).
- Produces: `compose()` acepta `w`, `h`, `fill`, `text_color` opcionales en el dict de capa `"desc"`; si vienen en `0`/ausentes, usa el comportamiento legado exacto de hoy.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`:

```python
class TestDescBoxConfigurable(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "desc", "key": "desc", "text": "Una descripción de prueba",
                "icon": "ninguno", "x": 0.1, "y": 0.1, "size": 0.03, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_custom_width_changes_box_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, bboxes_default = compose([self._layer(w=0.90)], (1000, 1000), fm)
        img_narrow, bboxes_narrow = compose([self._layer(w=0.30)], (1000, 1000), fm)
        self.assertNotEqual(bboxes_default["desc"][2], bboxes_narrow["desc"][2])

    def test_zero_width_falls_back_to_legacy_90_percent(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer(w=0.0)], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["desc"]
        self.assertEqual(x1 - x0, int(1000 * 0.90))

    def test_custom_height_changes_box_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes_tall = compose([self._layer(w=0.90, h=0.30)], (1000, 1000), fm)
        _, bboxes_default = compose([self._layer(w=0.90, h=0.0)], (1000, 1000), fm)
        x0a, y0a, x1a, y1a = bboxes_tall["desc"]
        x0b, y0b, x1b, y1b = bboxes_default["desc"]
        self.assertGreater(y1a - y0a, y1b - y0b)

    def test_custom_fill_changes_box_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(w=0.90, h=0.15, fill=[40, 25, 15, 215])],
                                  (400, 400), fm)
        img_custom, _ = compose([self._layer(w=0.90, h=0.15, fill=[0, 200, 0, 255])],
                                 (400, 400), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_custom.getdata()))

    def test_custom_text_color_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_white, _ = compose(
            [self._layer(w=0.90, h=0.15, text_color=[255, 255, 255, 255])], (400, 400), fm)
        img_red, _ = compose(
            [self._layer(w=0.90, h=0.15, text_color=[255, 0, 0, 255])], (400, 400), fm)
        self.assertNotEqual(list(img_white.getdata()), list(img_red.getdata()))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestDescBoxConfigurable -v`
Expected: la mayoría FAIL (bbox/pixels no cambian porque `render.py` todavía ignora `w`/`h`/`fill`/`text_color`)

- [ ] **Step 3: Implementar**

En `dcpub/render.py`, la rama actual (línea 436 en adelante) empieza así:

```python
        elif kind == "desc":
            description = layer["text"]
            if description.strip():
                bsz = max(8, int(W * layer["size"]))
                font_b = font_manager.load("body", bsz)
                box_w = int(W * 0.90)
                bx = int(layer["x"] * W)
                by = int(layer["y"] * H)
                bx = max(0, min(bx, W - box_w))
                corner_r = int(W * 0.033)
                pad = int(W * 0.04)

                icon = layer["icon"]
                icon_sz = max(24, int(W * 0.065))
                if icon != "ninguno":
                    text_x = bx + pad + icon_sz + pad
                else:
                    text_x = bx + pad * 2
                text_w = (bx + box_w) - text_x - pad
                dlines = wrap_text(description, font_b, max(10, text_w), draw)
                dlh = int(bsz * 1.48)
                text_h = len(dlines) * dlh
                box_h = max(text_h + pad, icon_sz + pad) + int(H * 0.010)

                box_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bd = ImageDraw.Draw(box_layer)
                box_fill = _apply_opacity(BOX_COLOR, opacity)
                bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                                     radius=corner_r, fill=box_fill)
                canvas = Image.alpha_composite(canvas, box_layer)
                draw = ImageDraw.Draw(canvas)

                icon_color = _apply_opacity(VERDE, opacity)
                text_color = _apply_opacity(BLANCO + (255,), opacity)
                if icon != "ninguno":
                    iy = by + (box_h - icon_sz) // 2
                    icon_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    icon_draw = ImageDraw.Draw(icon_layer)
                    draw_icon(icon_draw, bx + pad, iy, icon_sz, icon, icon_color)
                    canvas = Image.alpha_composite(canvas, icon_layer)
                    draw = ImageDraw.Draw(canvas)

                dy = by + (box_h - text_h) // 2
                text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                for i, l in enumerate(dlines):
                    text_draw.text((text_x, dy + i * dlh), l, font=font_b, fill=text_color)
                canvas = Image.alpha_composite(canvas, text_layer)
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)
```

Reemplazarla por:

```python
        elif kind == "desc":
            description = layer["text"]
            if description.strip():
                bsz = max(8, int(W * layer["size"]))
                font_b = font_manager.load("body", bsz)
                box_w = int(W * layer.get("w", 0)) or int(W * 0.90)
                bx = int(layer["x"] * W)
                by = int(layer["y"] * H)
                bx = max(0, min(bx, W - box_w))
                corner_r = int(W * 0.033)
                pad = int(W * 0.04)

                icon = layer["icon"]
                icon_sz = max(24, int(W * 0.065))
                if icon != "ninguno":
                    text_x = bx + pad + icon_sz + pad
                else:
                    text_x = bx + pad * 2
                text_w = (bx + box_w) - text_x - pad
                dlines = wrap_text(description, font_b, max(10, text_w), draw)
                dlh = int(bsz * 1.48)
                text_h = len(dlines) * dlh
                auto_box_h = max(text_h + pad, icon_sz + pad) + int(H * 0.010)
                box_h = int(H * layer.get("h", 0)) or auto_box_h

                box_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bd = ImageDraw.Draw(box_layer)
                fill_color = layer.get("fill", BOX_COLOR)
                box_fill = _apply_opacity(fill_color, opacity)
                bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                                     radius=corner_r, fill=box_fill)
                canvas = Image.alpha_composite(canvas, box_layer)
                draw = ImageDraw.Draw(canvas)

                icon_color = _apply_opacity(VERDE, opacity)
                text_color_value = layer.get("text_color", BLANCO + (255,))
                text_color = _apply_opacity(text_color_value, opacity)
                if icon != "ninguno":
                    iy = by + (box_h - icon_sz) // 2
                    icon_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    icon_draw = ImageDraw.Draw(icon_layer)
                    draw_icon(icon_draw, bx + pad, iy, icon_sz, icon, icon_color)
                    canvas = Image.alpha_composite(canvas, icon_layer)
                    draw = ImageDraw.Draw(canvas)

                dy = by + (box_h - text_h) // 2
                text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                for i, l in enumerate(dlines):
                    text_draw.text((text_x, dy + i * dlh), l, font=font_b, fill=text_color)
                canvas = Image.alpha_composite(canvas, text_layer)
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)
```

Nota: `dy` puede quedar negativo (o `dy + i*dlh` puede caer fuera de `[by, by+box_h]`) si `box_h` configurado es menor que `text_h` — es el overflow visible aceptado por diseño; PIL dibuja igual fuera del rectángulo sin error.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestDescBoxConfigurable -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK (los tests existentes de `"desc"` en `tests/test_render.py` no pasan `w`/`h`/`fill`/`text_color`, así que deben seguir usando el fallback legado sin cambios de comportamiento)

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: hacer configurable ancho/alto/color de la caja de descripcion"
```

---

### Task 3: Render — nueva rama `"cta"` en `compose()`

**Files:**
- Modify: `dcpub/render.py` (agregar rama `elif kind == "cta":` después de la rama `"desc"`, actualizar docstring de `compose()`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: nada de tareas anteriores directamente (capa nueva, autocontenida).
- Produces: `compose()` acepta capas `{"type": "cta", "text", "x", "y", "w", "h", "size", "fill", "text_color", "opacity"}` y las dibuja como un rectángulo redondeado con texto centrado, sin ícono.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`:

```python
class TestCTABox(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "cta", "key": "cta", "text": "Reservá ahora",
                "x": 0.3, "y": 0.8, "w": 0.4, "h": 0.08, "size": 0.03,
                "fill": [40, 25, 15, 215], "text_color": [255, 255, 255, 255],
                "opacity": 1.0}
        base.update(overrides)
        return base

    def test_cta_produces_bbox_matching_w_h(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["cta"]
        self.assertEqual(x1 - x0, int(1000 * 0.4))
        self.assertEqual(y1 - y0, int(1000 * 0.08))

    def test_cta_empty_text_produces_no_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer(text="")], (1000, 1000), fm)
        self.assertNotIn("cta", bboxes)

    def test_cta_fill_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_a, _ = compose([self._layer(fill=[40, 25, 15, 215])], (400, 400), fm)
        img_b, _ = compose([self._layer(fill=[0, 100, 200, 255])], (400, 400), fm)
        self.assertNotEqual(list(img_a.getdata()), list(img_b.getdata()))

    def test_cta_does_not_draw_icon(self):
        # No debe lanzar excepción ni requerir clave "icon" en absoluto.
        from dcpub.render import compose
        fm = self._font_manager()
        layer = self._layer()
        self.assertNotIn("icon", layer)
        img, bboxes = compose([layer], (1000, 1000), fm)
        self.assertIn("cta", bboxes)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestCTABox -v`
Expected: FAIL — `bboxes` no tiene clave `"cta"` porque `compose()` no reconoce ese `kind` (no lanza excepción, simplemente no dibuja nada; el test de bbox falla con `KeyError`)

- [ ] **Step 3: Implementar**

En `dcpub/render.py`, ubicar el cierre de la rama `"desc"` (termina con `bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)`, justo antes de `return canvas, bboxes`). Agregar inmediatamente después, todavía dentro del `for layer in layers:` (mismo nivel de indentación que `elif kind == "desc":`):

```python
        elif kind == "cta":
            cta_text = layer["text"]
            if cta_text.strip():
                bsz = max(8, int(W * layer["size"]))
                font_b = font_manager.load("body", bsz)
                box_w = max(1, int(W * layer.get("w", 0.30)))
                box_h = max(1, int(H * layer.get("h", 0.08)))
                bx = int(layer["x"] * W)
                by = int(layer["y"] * H)
                corner_r = int(W * 0.033)
                pad = int(W * 0.04)

                box_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bd = ImageDraw.Draw(box_layer)
                fill_color = layer.get("fill", BOX_COLOR)
                box_fill = _apply_opacity(fill_color, opacity)
                bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                                     radius=corner_r, fill=box_fill)
                canvas = Image.alpha_composite(canvas, box_layer)
                draw = ImageDraw.Draw(canvas)

                text_color_value = layer.get("text_color", BLANCO + (255,))
                text_color = _apply_opacity(text_color_value, opacity)
                max_text_w = max(10, box_w - pad * 2)
                dlines = wrap_text(cta_text, font_b, max_text_w, draw)
                dlh = int(bsz * 1.48)
                text_h = len(dlines) * dlh
                dy = by + (box_h - text_h) // 2

                text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                for i, l in enumerate(dlines):
                    lbbox = text_draw.textbbox((0, 0), l, font=font_b)
                    lw = lbbox[2] - lbbox[0]
                    lx = bx + max(pad, (box_w - lw) // 2)
                    text_draw.text((lx, dy + i * dlh), l, font=font_b, fill=text_color)
                canvas = Image.alpha_composite(canvas, text_layer)
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)
```

Actualizar también el docstring de `compose()` (línea ~303), agregando una línea después de la entrada de `desc`:

```
             - desc  : text, icon, x,y (esquina sup-izq del recuadro, frac), size (fuente, frac)
             - cta   : text, x,y (esquina sup-izq, frac), w,h (frac), size (fuente, frac),
                       fill (rgba), text_color (rgba) — sin ícono, texto centrado
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestCTABox -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: agregar rama de render para capas CTA"
```

---

### Task 4: Adaptadores UI↔render — `_build_layers_for` y `Exporter._layers_from_slide`

**Files:**
- Modify: `dcpub/app.py` (`_build_layers_for`, rama `layer.type == "box"`, y nueva rama `layer.type == "cta"`)
- Modify: `dcpub/exporter.py` (`_layers_from_slide`, rama `layer.type == "box"`, y nueva rama `layer.type == "cta"`)
- Test: `tests/test_app_slides.py` (clase `TestBuildLayersFor`), `tests/test_exporter.py`

**Interfaces:**
- Consumes: `BoxLayer.fill/text_color/w/h` (Task 1), rama de render `"cta"` (Task 3).
- Produces: preview y export producen resultados idénticos para las mismas capas (ambos caminos pasan los mismos campos).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_slides.py`, dentro de `TestBuildLayersFor`:

```python
    def test_build_layers_for_includes_box_fill_text_color_w_h(self):
        app = _make_app_with_two_slides()
        desc = App._layer_by_kind(app, "desc", app.slide)
        desc.fill = [1, 2, 3, 100]
        desc.text_color = [4, 5, 6, 200]
        desc.w = 0.5
        desc.h = 0.2

        capas = App._build_layers_for(app, app.slide)

        desc_capa = next(c for c in capas if c["type"] == "desc")
        self.assertEqual(desc_capa["fill"], [1, 2, 3, 100])
        self.assertEqual(desc_capa["text_color"], [4, 5, 6, 200])
        self.assertEqual(desc_capa["w"], 0.5)
        self.assertEqual(desc_capa["h"], 0.2)

    def test_build_layers_for_includes_cta_layer(self):
        from dcpub.models import CTALayer
        app = _make_app_with_two_slides()
        cta = CTALayer(name="CTA", z=10, text="Reservá ahora", x=0.1, y=0.9,
                        w=0.3, h=0.08, fill=[9, 9, 9, 200], text_color=[255, 255, 255, 255])
        app.slide.layers.append(cta)

        capas = App._build_layers_for(app, app.slide)

        cta_capa = next(c for c in capas if c["type"] == "cta")
        self.assertEqual(cta_capa["text"], "Reservá ahora")
        self.assertEqual(cta_capa["fill"], [9, 9, 9, 200])
        self.assertEqual(cta_capa["w"], 0.3)
        self.assertEqual(cta_capa["h"], 0.08)
```

Agregar a `tests/test_exporter.py` (revisar primero su estructura con `grep -n "class Test" tests/test_exporter.py` para ubicar dónde insertar de forma consistente):

```python
class TestLayersFromSlideBoxAndCTA(unittest.TestCase):
    def test_box_layer_includes_fill_text_color_w_h(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto
        slide = crear_slide_por_defecto("foto.jpg", descripcion="Texto")
        desc = next(l for l in slide.layers if l.type == "box")
        desc.fill = [1, 2, 3, 100]
        desc.text_color = [4, 5, 6, 200]

        capas = _layers_from_slide(slide)

        desc_capa = next(c for c in capas if c["type"] == "desc")
        self.assertEqual(desc_capa["fill"], [1, 2, 3, 100])
        self.assertEqual(desc_capa["text_color"], [4, 5, 6, 200])
        self.assertEqual(desc_capa["w"], desc.w)
        self.assertEqual(desc_capa["h"], desc.h)

    def test_cta_layer_included(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto, CTALayer
        slide = crear_slide_por_defecto("foto.jpg")
        slide.layers.append(CTALayer(name="CTA", z=10, text="Reservá",
                                      x=0.1, y=0.9, w=0.3, h=0.08))

        capas = _layers_from_slide(slide)

        cta_capa = next(c for c in capas if c["type"] == "cta")
        self.assertEqual(cta_capa["text"], "Reservá")
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides.TestBuildLayersFor -v tests.test_exporter -v`
Expected: FAIL (faltan claves `fill`/`text_color`/`w`/`h` y no hay entrada `"cta"`)

- [ ] **Step 3: Implementar en `dcpub/app.py`**

Dentro de `_build_layers_for`, la rama `box` actual (después del fix de Task 1 de la Fase 3 que ya agregó `adjust`/`overlay` a `photo`) es:

```python
            elif layer.type == "box":
```

Leer el bloque completo de esa rama con `grep -n "layer.type == \"box\"" -A 15 dcpub/app.py` y reemplazar el dict que arma (mismo patrón que las tareas anteriores: agregar `"w": layer.w, "h": layer.h, "fill": layer.fill, "text_color": layer.text_color` a las claves existentes `type/key/text/icon/x/y/size/opacity`).

Inmediatamente después de esa rama `box` (incluyendo su `elif` original de descripción, que ya tenía lógica especial para sincronizar con `self.txt_desc` cuando es la activa — **no tocar esa lógica de sincronización de texto**, solo sumar las claves nuevas al dict), agregar una rama nueva:

```python
            elif layer.type == "cta":
                layers.append({"type": "cta", "key": layer.id, "text": layer.text,
                                "x": layer.x, "y": layer.y, "w": layer.w, "h": layer.h,
                                "size": layer.size, "fill": layer.fill,
                                "text_color": layer.text_color, "opacity": layer.opacity})
```

(La capa CTA no tiene contraparte de widget en el panel izquierdo — a diferencia de foto/logo/título/subtítulo/descripción, siempre lee `layer.text` directo, sin el patrón `es_activa and layer is self._layer_by_kind(...)`.)

- [ ] **Step 4: Implementar en `dcpub/exporter.py`**

La rama actual en `_layers_from_slide`:

```python
        elif layer.type == "box":
            layers.append({
                "type": "desc",
                "key": layer.id,
                "text": layer.text,
                "icon": layer.icon,
                "x": layer.x,
                "y": layer.y,
                "size": layer.size,
                "opacity": layer.opacity,
            })
    return layers
```

Reemplazarla por:

```python
        elif layer.type == "box":
            layers.append({
                "type": "desc",
                "key": layer.id,
                "text": layer.text,
                "icon": layer.icon,
                "x": layer.x,
                "y": layer.y,
                "w": layer.w,
                "h": layer.h,
                "size": layer.size,
                "fill": layer.fill,
                "text_color": layer.text_color,
                "opacity": layer.opacity,
            })
        elif layer.type == "cta":
            layers.append({
                "type": "cta",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "w": layer.w,
                "h": layer.h,
                "size": layer.size,
                "fill": layer.fill,
                "text_color": layer.text_color,
                "opacity": layer.opacity,
            })
    return layers
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides.TestBuildLayersFor -v tests.test_exporter -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add dcpub/app.py dcpub/exporter.py tests/test_app_slides.py tests/test_exporter.py
git commit -m "feat: propagar fill/text_color/w/h y capas cta en los adaptadores de render"
```

---

### Task 5: Migración automática de proyectos viejos (`project_io.py`)

**Files:**
- Modify: `dcpub/project_io.py` (`load_project`)
- Test: `tests/test_project_io.py`

**Interfaces:**
- Consumes: `BoxLayer` (Task 1).
- Produces: `load_project(path)` deja cualquier `BoxLayer` con `w<=0` o `h<=0` en memoria con `w=0.90, h=0.12` (los mismos defaults del Task 1, Step 8), sin reescribir el archivo en disco.

- [ ] **Step 1: Escribir el test que falla**

Revisar primero `tests/test_project_io.py` con `grep -n "class Test\|def setUp" tests/test_project_io.py` para reusar su patrón de proyecto temporal (`tempfile`/`tmp_path`-style) y agregar:

```python
class TestLoadProjectMigratesLegacyBoxSize(unittest.TestCase):
    def test_zero_w_h_box_layer_gets_new_defaults_on_load(self):
        import json
        import tempfile
        from pathlib import Path
        from dcpub.models import crear_proyecto_por_defecto
        from dcpub.project_io import save_project, load_project

        project = crear_proyecto_por_defecto("foto.jpg")
        desc = next(l for l in project.slides[0].layers if l.type == "box")
        desc.w = 0.0
        desc.h = 0.0

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proyecto.dcpub.json"
            save_project(project, path)

            # Confirmar que el archivo en disco efectivamente quedo en 0,0
            # (proyecto "legado" simulado), antes de cargarlo.
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw_box = next(l for l in raw["slides"][0]["layers"] if l["type"] == "box")
            self.assertEqual((raw_box["w"], raw_box["h"]), (0.0, 0.0))

            reloaded = load_project(path)

        reloaded_desc = next(l for l in reloaded.slides[0].layers if l.type == "box")
        self.assertEqual(reloaded_desc.w, 0.90)
        self.assertEqual(reloaded_desc.h, 0.12)

    def test_nonzero_w_h_box_layer_is_left_untouched_on_load(self):
        import tempfile
        from pathlib import Path
        from dcpub.models import crear_proyecto_por_defecto
        from dcpub.project_io import save_project, load_project

        project = crear_proyecto_por_defecto("foto.jpg")
        desc = next(l for l in project.slides[0].layers if l.type == "box")
        desc.w = 0.5
        desc.h = 0.25

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proyecto.dcpub.json"
            save_project(project, path)
            reloaded = load_project(path)

        reloaded_desc = next(l for l in reloaded.slides[0].layers if l.type == "box")
        self.assertEqual(reloaded_desc.w, 0.5)
        self.assertEqual(reloaded_desc.h, 0.25)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m unittest tests.test_project_io.TestLoadProjectMigratesLegacyBoxSize -v`
Expected: FAIL en el primer test (`reloaded_desc.w` sigue en `0.0`)

- [ ] **Step 3: Implementar**

En `dcpub/project_io.py`, la función actual es:

```python
def load_project(path: Path) -> Project:
    """Carga un Project desde el JSON en `path`, resolviendo las rutas de imagen
    relativas contra la carpeta de `path`."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    project_dir = path.parent
    for slide_data in data["slides"]:
        for layer_data in slide_data["layers"]:
            if layer_data.get("type") in ("photo", "logo") and layer_data.get("src"):
                layer_data["src"] = _resolve_src_from_relative(layer_data["src"], project_dir)
    return Project.from_dict(data)
```

Reemplazarla por:

```python
_LEGACY_BOX_DEFAULT_W = 0.90
_LEGACY_BOX_DEFAULT_H = 0.12


def load_project(path: Path) -> Project:
    """Carga un Project desde el JSON en `path`, resolviendo las rutas de imagen
    relativas contra la carpeta de `path`. Migra en memoria (sin reescribir el
    archivo) las capas BoxLayer guardadas antes de que w/h fueran configurables
    (w=0 o h=0), completándolas con los defaults nuevos."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    project_dir = path.parent
    for slide_data in data["slides"]:
        for layer_data in slide_data["layers"]:
            if layer_data.get("type") in ("photo", "logo") and layer_data.get("src"):
                layer_data["src"] = _resolve_src_from_relative(layer_data["src"], project_dir)
            if layer_data.get("type") == "box":
                if not layer_data.get("w"):
                    layer_data["w"] = _LEGACY_BOX_DEFAULT_W
                if not layer_data.get("h"):
                    layer_data["h"] = _LEGACY_BOX_DEFAULT_H
    return Project.from_dict(data)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m unittest tests.test_project_io.TestLoadProjectMigratesLegacyBoxSize -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/project_io.py tests/test_project_io.py
git commit -m "fix: migrar automaticamente BoxLayer legado (w=0,h=0) al cargar un proyecto"
```

---

### Task 6: Importador por lotes crea `CTALayer` real

**Files:**
- Modify: `dcpub/batch_import.py` (`importar_carrusel_por_lotes`)
- Modify: `tests/test_batch_import.py` (actualizar un test existente que queda obsoleto + agregar tests nuevos)

**Interfaces:**
- Consumes: `CTALayer` (Task 1).
- Produces: cuando el JSON importado trae `"cta"` no vacío, `slide.layers` incluye una `CTALayer` real además de que `slide.extra["cta"]` se sigue llenando igual que hoy (no se rompe compatibilidad con lo ya guardado en `extra`).

- [ ] **Step 1: Actualizar el test existente que queda obsoleto**

`tests/test_batch_import.py` ya tiene, en la clase `TestImportarCarruselPorLotes`
(que usa `self.carpeta` de un `tempfile.TemporaryDirectory()` creado en su
`setUp`, y los helpers de módulo `_crear_imagen`, `_guardar_json`,
`_capa_por_tipo`, `_capa_texto_por_rol` — ya existentes, no hay que
reinventarlos), el test (líneas 133-152):

```python
    def test_cta_se_preserva_sin_renderizarse_como_capa(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {
                "imagen": "01.jpg",
                "titulo": "Titulo",
                "subtitulo": "Subtitulo",
                "beneficios": ["Beneficio"],
                "cta": "Reserva ahora",
            }
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual(project.slides[0].extra["cta"], "Reserva ahora")
        textos_renderizables = [
            getattr(layer, "text", "")
            for layer in project.slides[0].layers
        ]
        self.assertNotIn("Reserva ahora", textos_renderizables)
```

Este test afirma el comportamiento viejo (CTA nunca se vuelve capa) y va a
quedar falso después de este task. Reemplazarlo por:

```python
    def test_cta_se_preserva_en_extra_y_se_crea_como_capa_real(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {
                "imagen": "01.jpg",
                "titulo": "Titulo",
                "subtitulo": "Subtitulo",
                "beneficios": ["Beneficio"],
                "cta": "Reserva ahora",
            }
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual(project.slides[0].extra["cta"], "Reserva ahora")
        cta_layers = [l for l in project.slides[0].layers if l.type == "cta"]
        self.assertEqual(len(cta_layers), 1)
        self.assertEqual(cta_layers[0].text, "Reserva ahora")

    def test_cta_vacio_no_crea_capa(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {"imagen": "01.jpg", "titulo": "", "subtitulo": "", "beneficios": [], "cta": ""}
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        cta_layers = [l for l in project.slides[0].layers if l.type == "cta"]
        self.assertEqual(cta_layers, [])
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_batch_import -v`
Expected: `test_cta_se_preserva_en_extra_y_se_crea_como_capa_real` y
`test_cta_vacio_no_crea_capa` FALLAN (`AssertionError: 0 != 1` — todavía no
existe ninguna `CTALayer` porque `batch_import.py` no la crea)

- [ ] **Step 3: Implementar**

En `dcpub/batch_import.py`, la línea actual es:

```python
        slide.extra["cta"] = str(entrada.get("cta", ""))
        project.slides.append(slide)
```

Reemplazarla por:

```python
        cta_texto = str(entrada.get("cta", ""))
        slide.extra["cta"] = cta_texto
        if cta_texto.strip():
            from .models import CTALayer
            cta_layer = CTALayer(name="CTA", z=max((l.z for l in slide.layers), default=0) + 1,
                                  text=cta_texto, x=0.10, y=0.90, w=0.35, h=0.08)
            slide.layers.append(cta_layer)
        project.slides.append(slide)
```

Actualizar también el docstring de `importar_carrusel_por_lotes` (líneas 36-37), que hoy dice:

```
    El CTA se preserva por lámina en ``slide.extra["cta"]``. No se convierte en
    capa visual porque todavía no existe CTALayer en el modelo/render.
```

por:

```
    El CTA se preserva por lámina en ``slide.extra["cta"]`` y además se crea
    como ``CTALayer`` real en ``slide.layers`` cuando el texto no está vacío.
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_batch_import -v`
Expected: PASS (8 tests: los 6 preexistentes que no cambian, más los 2
nuevos del Step 1 que reemplazan al test obsoleto)

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/batch_import.py tests/test_batch_import.py
git commit -m "feat: crear CTALayer real al importar carruseles por lotes con cta"
```

---

### Task 7: Panel de propiedades — sliders de w/h + `_kind_of`/`SIZE_RANGE`/`LABELS` para `cta`

**Files:**
- Modify: `dcpub/app.py` (`SIZE_RANGE`, `LABELS`, `_kind_of`, `_build_property_panel`)
- Test: `tests/test_app_property_panel.py`

**Interfaces:**
- Consumes: `CTALayer` (Task 1).
- Produces: seleccionar una capa `cta` en el canvas la reconoce el panel de propiedades (`_kind_of` devuelve `"cta"`); el bloque genérico de propiedades (x/y/size/opacidad) suma sliders de `w`/`h` para `kind in ("desc", "cta")`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_property_panel.py` (reusar el patrón headless `App.__new__(App)` ya usado en ese archivo, ver Task 4/5 de la Fase 3 anterior para el estilo):

```python
class TestKindOfCTA(unittest.TestCase):
    def test_kind_of_cta_layer_is_cta(self):
        from dcpub.models import CTALayer
        app = App.__new__(App)
        layer = CTALayer()
        self.assertEqual(App._kind_of(app, layer), "cta")


class TestSizeRangeAndLabelsIncludeCTA(unittest.TestCase):
    def test_cta_has_size_range(self):
        from dcpub.app import SIZE_RANGE
        self.assertIn("cta", SIZE_RANGE)

    def test_cta_has_label(self):
        from dcpub.app import LABELS
        self.assertIn("cta", LABELS)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_property_panel.TestKindOfCTA tests.test_app_property_panel.TestSizeRangeAndLabelsIncludeCTA -v`
Expected: FAIL (`_kind_of` devuelve `None`; `SIZE_RANGE`/`LABELS` no tienen `"cta"`)

- [ ] **Step 3: Implementar — `SIZE_RANGE`/`LABELS`**

Reemplazar:

```python
SIZE_RANGE = {
    "logo":  (0.08, 0.40),
    "title": (0.03, 0.16),
    "sub":   (0.02, 0.10),
    "desc":  (0.015, 0.07),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción"}
```

por:

```python
SIZE_RANGE = {
    "logo":  (0.08, 0.40),
    "title": (0.03, 0.16),
    "sub":   (0.02, 0.10),
    "desc":  (0.015, 0.07),
    "cta":   (0.015, 0.07),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción",
          "cta": "CTA"}
```

- [ ] **Step 4: Implementar — `_kind_of`**

Reemplazar:

```python
    def _kind_of(self, layer):
        """Dado un Layer, devuelve su tipo visual para render/propiedades."""
        if layer is None:
            return None
        if layer.type == "photo":
            return "photo"
        if layer.type == "logo":
            return "logo"
        if layer.type == "text" and layer.role == "title":
            return "title"
        if layer.type == "text" and layer.role == "subtitle":
            return "sub"
        if layer.type == "box":
            return "desc"
        return None
```

por:

```python
    def _kind_of(self, layer):
        """Dado un Layer, devuelve su tipo visual para render/propiedades."""
        if layer is None:
            return None
        if layer.type == "photo":
            return "photo"
        if layer.type == "logo":
            return "logo"
        if layer.type == "text" and layer.role == "title":
            return "title"
        if layer.type == "text" and layer.role == "subtitle":
            return "sub"
        if layer.type == "box":
            return "desc"
        if layer.type == "cta":
            return "cta"
        return None
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_property_panel.TestKindOfCTA tests.test_app_property_panel.TestSizeRangeAndLabelsIncludeCTA -v`
Expected: PASS

- [ ] **Step 6: Agregar sliders de w/h al bloque genérico de propiedades**

En `dcpub/app.py`, dentro de `_build_property_panel`, el bloque genérico (para todo `kind` que no sea `"photo"`) es:

```python
        smin, smax = SIZE_RANGE[kind]
        size_label = "Tamaño del logo" if kind == "logo" else "Tamaño de fuente"
        self._slider(card, token, "x", "Posición X", 0.0, 1.0, disabled=disabled)
        self._slider(card, token, "y", "Posición Y", 0.0, 1.0, disabled=disabled)
        self._slider(card, token, "size", size_label, smin, smax, disabled=disabled)
        self._slider(card, token, "opacity", "Opacidad", 0.0, 1.0,
                     disabled=disabled, as_percent=True)
```

Reemplazarlo por:

```python
        smin, smax = SIZE_RANGE[kind]
        size_label = "Tamaño del logo" if kind == "logo" else "Tamaño de fuente"
        self._slider(card, token, "x", "Posición X", 0.0, 1.0, disabled=disabled)
        self._slider(card, token, "y", "Posición Y", 0.0, 1.0, disabled=disabled)
        if kind in ("desc", "cta"):
            self._slider(card, token, "w", "Ancho de la caja", 0.10, 0.95, disabled=disabled)
            self._slider(card, token, "h", "Alto de la caja", 0.03, 0.50, disabled=disabled)
        self._slider(card, token, "size", size_label, smin, smax, disabled=disabled)
        self._slider(card, token, "opacity", "Opacidad", 0.0, 1.0,
                     disabled=disabled, as_percent=True)
```

- [ ] **Step 7: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 8: Commit**

```bash
git add dcpub/app.py tests/test_app_property_panel.py
git commit -m "feat: reconocer capas cta en el panel de propiedades con sliders de ancho/alto"
```

---

### Task 8: Selector de color reutilizable (`fill`/`text_color`) en el panel de propiedades

**Files:**
- Modify: `dcpub/app.py` (`__init__`, `_build_property_panel`, nuevos métodos `_color_picker`, `_pick_color`, `_on_color_alpha_press`, `_on_color_alpha_change`, `_on_color_alpha_release`, helper `_rgba_to_hex`)
- Test: `tests/test_app_property_panel.py`

**Interfaces:**
- Consumes: `BoxLayer.fill/text_color`, `CTALayer.fill/text_color` (Task 1).
- Produces: `App._rgba_to_hex(rgba) -> str`, y un control de color completo (swatch + botón "Elegir color…" + slider de alpha) reusable para `fill` y `text_color` en `kind in ("desc", "cta")`.

Esta es la primera vez que el proyecto usa `tkinter.colorchooser` — no hay patrón previo que seguir, así que el propio test de este task fija el contrato.

- [ ] **Step 1: Escribir los tests que fallan (parte pura: `_rgba_to_hex`)**

Agregar a `tests/test_app_property_panel.py`:

```python
class TestRgbaToHex(unittest.TestCase):
    def test_converts_rgb_ignoring_alpha(self):
        from dcpub.app import _rgba_to_hex
        self.assertEqual(_rgba_to_hex([255, 0, 128, 200]), "#ff0080")

    def test_handles_three_channel_input(self):
        from dcpub.app import _rgba_to_hex
        self.assertEqual(_rgba_to_hex([0, 0, 0]), "#000000")


class TestColorAlphaCommit(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack
        from dcpub.models import CTALayer
        self.app = App.__new__(App)
        self.app.commands = CommandStack()
        self.app._color_alpha_start = None
        self.app._schedule_render = lambda: None
        self.layer = CTALayer(fill=[10, 20, 30, 100])

    def test_alpha_press_then_release_pushes_one_command(self):
        App._on_color_alpha_press(self.app, self.layer, "fill")
        self.layer.fill = [10, 20, 30, 250]
        App._on_color_alpha_release(self.app, self.layer, "fill")

        self.assertEqual(len(self.app.commands._undo_stack), 1)
        self.app.commands.undo()
        self.assertEqual(self.layer.fill, [10, 20, 30, 100])

    def test_release_without_press_does_nothing(self):
        App._on_color_alpha_release(self.app, self.layer, "fill")
        self.assertEqual(len(self.app.commands._undo_stack), 0)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_property_panel.TestRgbaToHex tests.test_app_property_panel.TestColorAlphaCommit -v`
Expected: FAIL — `ImportError`/`AttributeError` (nada de esto existe todavía)

- [ ] **Step 3: Implementar `_rgba_to_hex` (función de módulo)**

En `dcpub/app.py`, agregar cerca de `_snap_position`/`_offset_delta_for_drag` (funciones puras de módulo):

```python
def _rgba_to_hex(rgba):
    r, g, b = rgba[0], rgba[1], rgba[2]
    return f"#{r:02x}{g:02x}{b:02x}"
```

- [ ] **Step 4: Agregar estado en `__init__`**

Después de `self._wheel_zoom_job = None` (agregado en la Fase 3), agregar:

```python
        self._color_alpha_start = None  # valor [r,g,b,a] al iniciar el arrastre del alpha
```

- [ ] **Step 5: Implementar `_on_color_alpha_press`/`_on_color_alpha_release`**

Agregar, cerca de `_on_slider_press`/`_on_slider_release`:

```python
    def _on_color_alpha_press(self, layer, attr):
        self._color_alpha_start = list(getattr(layer, attr))

    def _on_color_alpha_release(self, layer, attr):
        if self._color_alpha_start is None:
            return
        old_value = self._color_alpha_start
        self._color_alpha_start = None
        new_value = list(getattr(layer, attr))
        if old_value != new_value:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, attr, old_value, new_value))
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_property_panel.TestRgbaToHex tests.test_app_property_panel.TestColorAlphaCommit -v`
Expected: PASS

- [ ] **Step 7: Implementar el control de UI completo (`_color_picker`, `_pick_color`, `_on_color_alpha_change`)**

Agregar estos tres métodos junto a los anteriores:

```python
    def _on_color_alpha_change(self, layer, attr, alpha_var, swatch):
        value = list(getattr(layer, attr))
        while len(value) < 4:
            value.append(255)
        value[3] = int(alpha_var.get())
        setattr(layer, attr, value)
        swatch.config(bg=_rgba_to_hex(value))
        self._schedule_render()

    def _pick_color(self, layer, attr, swatch):
        from tkinter import colorchooser
        from .commands import PropertyChangeCommand
        old_value = list(getattr(layer, attr))
        _, hex_color = colorchooser.askcolor(color=_rgba_to_hex(old_value),
                                              title="Elegir color")
        if hex_color is None:
            return
        rgb16 = self.winfo_rgb(hex_color)
        r, g, b = rgb16[0] // 256, rgb16[1] // 256, rgb16[2] // 256
        alpha = old_value[3] if len(old_value) > 3 else 255
        new_value = [r, g, b, alpha]
        if new_value != old_value:
            self.commands.push(PropertyChangeCommand(layer, attr, old_value, new_value))
            swatch.config(bg=_rgba_to_hex(new_value))
            self._schedule_render()

    def _color_picker(self, parent, layer, attr, label, disabled=False):
        tk.Label(parent, text=label, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X)

        rgba = list(getattr(layer, attr))
        swatch = tk.Label(row, bg=_rgba_to_hex(rgba), width=3, relief="flat")
        swatch.pack(side=tk.LEFT, padx=(0, 6))

        state = tk.DISABLED if disabled else tk.NORMAL
        tk.Button(row, text="Elegir color…", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), state=state,
                  command=lambda: self._pick_color(layer, attr, swatch)).pack(side=tk.LEFT)

        alpha_value = rgba[3] if len(rgba) > 3 else 255
        alpha_var = tk.IntVar(value=alpha_value)
        alpha_scale = ttk.Scale(
            row, from_=0, to=255, variable=alpha_var, orient=tk.HORIZONTAL,
            style="Brand.Horizontal.TScale", state=state,
            command=lambda _v, l=layer, a=attr, v=alpha_var, s=swatch:
                self._on_color_alpha_change(l, a, v, s))
        alpha_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        alpha_scale.bind("<ButtonPress-1>",
                          lambda e, l=layer, a=attr: self._on_color_alpha_press(l, a))
        alpha_scale.bind("<ButtonRelease-1>",
                          lambda e, l=layer, a=attr: self._on_color_alpha_release(l, a))
```

- [ ] **Step 8: Cablear el control en `_build_property_panel`**

Extender el bloque agregado en la Task 7:

```python
        if kind in ("desc", "cta"):
            self._slider(card, token, "w", "Ancho de la caja", 0.10, 0.95, disabled=disabled)
            self._slider(card, token, "h", "Alto de la caja", 0.03, 0.50, disabled=disabled)
```

por:

```python
        if kind in ("desc", "cta"):
            self._slider(card, token, "w", "Ancho de la caja", 0.10, 0.95, disabled=disabled)
            self._slider(card, token, "h", "Alto de la caja", 0.03, 0.50, disabled=disabled)
            self._color_picker(card, layer, "fill", "Color de la caja", disabled=disabled)
            self._color_picker(card, layer, "text_color", "Color del texto", disabled=disabled)
```

- [ ] **Step 9: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 10: Commit**

```bash
git add dcpub/app.py tests/test_app_property_panel.py
git commit -m "feat: agregar selector de color (fill/text_color) al panel de propiedades"
```

---

### Task 9: Campo de texto para CTA en el panel de propiedades + botón "Agregar CTA"

**Files:**
- Modify: `dcpub/app.py` (`_build_left`, `_build_property_panel`, nuevos métodos `_add_cta_layer`, `_on_cta_text_commit`)
- Test: `tests/test_app_property_panel.py`

**Interfaces:**
- Consumes: `CTALayer` (Task 1), `AddLayerCommand` (ya existe en `dcpub/commands.py`, usado hoy por `_duplicate_layer`).
- Produces: botón "+ Agregar CTA" en el panel de capas; el panel de propiedades de una capa `cta` incluye un campo de texto propio (a diferencia de título/subtítulo/descripción, que se editan desde el panel izquierdo).

- [ ] **Step 1: Escribir el test que falla — `_add_cta_layer`**

Agregar a `tests/test_app_property_panel.py`:

```python
class TestAddCTALayer(unittest.TestCase):
    def test_add_cta_layer_appends_layer_and_selects_it(self):
        from dcpub.commands import CommandStack
        from dcpub.models import crear_proyecto_por_defecto
        app = App.__new__(App)
        app.project = crear_proyecto_por_defecto("foto.jpg")
        app.slide = app.project.slides[0]
        app.commands = CommandStack()
        app._selected = None
        app._refresh_layers_list = lambda: None
        app._schedule_render = lambda: None
        app._build_property_panel = lambda: None

        cantidad_antes = len(app.slide.layers)
        App._add_cta_layer(app)

        self.assertEqual(len(app.slide.layers), cantidad_antes + 1)
        nueva = app.slide.layers[-1]
        self.assertEqual(nueva.type, "cta")
        self.assertIs(app._selected, nueva)

    def test_add_cta_layer_is_undoable(self):
        from dcpub.commands import CommandStack
        from dcpub.models import crear_proyecto_por_defecto
        app = App.__new__(App)
        app.project = crear_proyecto_por_defecto("foto.jpg")
        app.slide = app.project.slides[0]
        app.commands = CommandStack()
        app._selected = None
        app._refresh_layers_list = lambda: None
        app._schedule_render = lambda: None
        app._build_property_panel = lambda: None

        cantidad_antes = len(app.slide.layers)
        App._add_cta_layer(app)
        app.commands.undo()

        self.assertEqual(len(app.slide.layers), cantidad_antes)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m unittest tests.test_app_property_panel.TestAddCTALayer -v`
Expected: FAIL — `AttributeError: type object 'App' has no attribute '_add_cta_layer'`

- [ ] **Step 3: Implementar `_add_cta_layer`**

En `dcpub/app.py`, agregar cerca de `_duplicate_layer`:

```python
    def _add_cta_layer(self):
        from .models import CTALayer
        from .commands import AddLayerCommand
        new_z = max((l.z for l in self.slide.layers), default=0) + 1
        new_layer = CTALayer(name="CTA", z=new_z, text="Reservá ahora",
                              x=0.10, y=0.90, w=0.35, h=0.08)
        index = len(self.slide.layers)
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._set_selected(new_layer)
        self._refresh_layers_list()
        self._schedule_render()
```

(`CTALayer.id` se autogenera vía `field(default_factory=_short_id)` heredado de `Layer`, igual que cualquier capa nueva — no hace falta pasarlo a mano.)

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m unittest tests.test_app_property_panel.TestAddCTALayer -v`
Expected: PASS

- [ ] **Step 5: Agregar el botón "+ Agregar CTA" al panel de capas**

En `dcpub/app.py`, dentro de `_build_left`, la línea actual es:

```python
        self._layers_list_frame = tk.Frame(left, bg=PANEL)
        self._layers_list_frame.pack(fill=tk.X, pady=(0, 10), **pad)
        self._refresh_layers_list()
```

Reemplazarla por:

```python
        self._layers_list_frame = tk.Frame(left, bg=PANEL)
        self._layers_list_frame.pack(fill=tk.X, pady=(0, 10), **pad)
        self._refresh_layers_list()

        tk.Button(left, text="+ Agregar CTA", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_cta_layer).pack(
            fill=tk.X, pady=(0, 10), **pad)
```

- [ ] **Step 6: Escribir el test que falla — campo de texto de CTA en el panel de propiedades**

```python
class TestCTATextFieldCommit(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack
        from dcpub.models import CTALayer
        self.app = App.__new__(App)
        self.app.commands = CommandStack()
        self.app._schedule_render = lambda: None
        self.layer = CTALayer(text="Texto original")

    def test_commit_pushes_property_change_command(self):
        old_value = self.layer.text
        self.layer.text = "Texto nuevo"

        App._on_cta_text_commit(self.app, self.layer, old_value, "Texto nuevo")

        self.assertEqual(len(self.app.commands._undo_stack), 1)
        self.app.commands.undo()
        self.assertEqual(self.layer.text, "Texto original")

    def test_commit_with_same_value_pushes_nothing(self):
        App._on_cta_text_commit(self.app, self.layer, "Texto original", "Texto original")
        self.assertEqual(len(self.app.commands._undo_stack), 0)
```

- [ ] **Step 7: Correr el test y verificar que falla**

Run: `python -m unittest tests.test_app_property_panel.TestCTATextFieldCommit -v`
Expected: FAIL — `AttributeError: type object 'App' has no attribute '_on_cta_text_commit'`

- [ ] **Step 8: Implementar `_on_cta_text_commit` y el widget en el panel**

Agregar el método cerca de `_on_entry_commit`:

```python
    def _on_cta_text_commit(self, layer, old_value, new_value):
        if old_value != new_value:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, "text", old_value, new_value))
        self._schedule_render()
```

En `_build_property_panel`, extender una vez más el bloque de la Task 8:

```python
        if kind in ("desc", "cta"):
            self._slider(card, token, "w", "Ancho de la caja", 0.10, 0.95, disabled=disabled)
            self._slider(card, token, "h", "Alto de la caja", 0.03, 0.50, disabled=disabled)
            self._color_picker(card, layer, "fill", "Color de la caja", disabled=disabled)
            self._color_picker(card, layer, "text_color", "Color del texto", disabled=disabled)
```

por:

```python
        if kind in ("desc", "cta"):
            self._slider(card, token, "w", "Ancho de la caja", 0.10, 0.95, disabled=disabled)
            self._slider(card, token, "h", "Alto de la caja", 0.03, 0.50, disabled=disabled)
            self._color_picker(card, layer, "fill", "Color de la caja", disabled=disabled)
            self._color_picker(card, layer, "text_color", "Color del texto", disabled=disabled)
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
```

- [ ] **Step 9: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_property_panel.TestCTATextFieldCommit -v`
Expected: PASS

- [ ] **Step 10: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 11: Commit**

```bash
git add dcpub/app.py tests/test_app_property_panel.py
git commit -m "feat: agregar boton para crear CTA y campo de texto propio en el panel de propiedades"
```

---

### Task 10: Verificación headless de cierre de esta sub-fase

**Files:**
- Create: `verificaciones/fase4_cta_caja_verificacion.py`

**Interfaces:**
- Consumes: todo lo anterior (Tasks 1-9).
- Produces: carpeta `verificaciones/fase4_cta_caja_control/` con imágenes de control y `HEADLESS_OK`.

- [ ] **Step 1: Escribir el script**

Crear `verificaciones/fase4_cta_caja_verificacion.py`, siguiendo el mismo patrón que `verificaciones/fase3_verificacion.py` (sys.path insert, imagen sintética, `FontManager` real, `HEADLESS_OK` al final):

```python
"""Verificación headless de Fase 4 (sub-fase 1): CTA + caja de descripción
configurable, migración de proyectos legado. No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.models import crear_proyecto_por_defecto, CTALayer
from dcpub.render import compose
from dcpub.project_io import save_project, load_project
from dcpub.batch_import import importar_carrusel_por_lotes
from dcpub.fonts import FontManager

OUT_DIR = Path(__file__).resolve().parent / "fase4_cta_caja_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def _layer_dict_box(layer):
    return {"type": "desc", "key": layer.id, "text": layer.text, "icon": layer.icon,
            "x": layer.x, "y": layer.y, "w": layer.w, "h": layer.h, "size": layer.size,
            "fill": layer.fill, "text_color": layer.text_color, "opacity": layer.opacity}


def _layer_dict_cta(layer):
    return {"type": "cta", "key": layer.id, "text": layer.text, "x": layer.x, "y": layer.y,
            "w": layer.w, "h": layer.h, "size": layer.size, "fill": layer.fill,
            "text_color": layer.text_color, "opacity": layer.opacity}


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    font_manager = FontManager()
    canvas_size = (project.slides[0].format["w"], project.slides[0].format["h"])
    desc = next(l for l in project.slides[0].layers if l.type == "box")
    desc.text = "Descripción de prueba"

    # Render con la caja de descripcion default (w=0.90,h=0.12 fijados en el
    # modelo) vs. con colores/tamaño no default.
    render_default, _ = compose([_layer_dict_box(desc)], canvas_size, font_manager)
    render_default.save(OUT_DIR / "caja_default.png")

    desc.w = 0.5
    desc.h = 0.25
    desc.fill = [10, 80, 40, 220]
    desc.text_color = [255, 220, 0, 255]
    render_custom, _ = compose([_layer_dict_box(desc)], canvas_size, font_manager)
    render_custom.save(OUT_DIR / "caja_custom.png")

    diff = ImageChops.difference(render_default.convert("RGB"), render_custom.convert("RGB"))
    assert diff.getbbox() is not None, "la caja personalizada debe diferir de la default"

    # Capa CTA nueva, agregada a mano (equivalente al boton "+ Agregar CTA").
    cta = CTALayer(name="CTA", z=10, text="Reservá ahora", x=0.10, y=0.85, w=0.35, h=0.08)
    project.slides[0].layers.append(cta)
    render_con_cta, bboxes_con_cta = compose(
        [_layer_dict_box(desc), _layer_dict_cta(cta)], canvas_size, font_manager)
    render_con_cta.save(OUT_DIR / "con_cta.png")
    assert "cta" in bboxes_con_cta

    # Guardar y recargar: el proyecto con capa CTA debe sobrevivir el ciclo.
    project_path = OUT_DIR / "fase4_control.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    reloaded_cta = [l for l in reloaded.slides[0].layers if l.type == "cta"]
    assert len(reloaded_cta) == 1
    assert reloaded_cta[0].text == "Reservá ahora"

    # Migracion de proyectos legado: BoxLayer con w=0,h=0 en disco vuelve con
    # los defaults nuevos en memoria tras cargar.
    legacy_project = crear_proyecto_por_defecto(foto_path)
    legacy_desc = next(l for l in legacy_project.slides[0].layers if l.type == "box")
    legacy_desc.w = 0.0
    legacy_desc.h = 0.0
    legacy_path = OUT_DIR / "fase4_legacy.dcpub.json"
    save_project(legacy_project, legacy_path)
    reloaded_legacy = load_project(legacy_path)
    reloaded_legacy_desc = next(l for l in reloaded_legacy.slides[0].layers if l.type == "box")
    assert reloaded_legacy_desc.w == 0.90
    assert reloaded_legacy_desc.h == 0.12

    # Importador por lotes crea CTALayer real.
    import_dir = OUT_DIR / "importar"
    import_dir.mkdir(exist_ok=True)
    _foto_sintetica(str(import_dir / "una.jpg"))
    import json as _json
    (import_dir / "entradas.json").write_text(_json.dumps([
        {"imagen": "una.jpg", "titulo": "T", "subtitulo": "S",
         "beneficios": ["Uno", "Dos"], "cta": "Escribinos"}
    ], ensure_ascii=False), encoding="utf-8")
    imported_project, _warnings = importar_carrusel_por_lotes(
        import_dir, project.slides[0].format)
    imported_cta = [l for l in imported_project.slides[0].layers if l.type == "cta"]
    assert len(imported_cta) == 1
    assert imported_cta[0].text == "Escribinos"

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el script**

Run: `python verificaciones/fase4_cta_caja_verificacion.py`
Expected: imprime `HEADLESS_OK` y la ruta de salida, sin `AssertionError` ni excepciones

- [ ] **Step 3: Revisar visualmente**

Abrir `caja_default.png`, `caja_custom.png` y `con_cta.png` en
`verificaciones/fase4_cta_caja_control/` y confirmar a simple vista que la
caja personalizada se ve distinta (tamaño y colores) y que el CTA aparece
como un rectángulo redondeado con texto centrado, sin ícono.

- [ ] **Step 4: Correr toda la suite una vez más**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 5: Actualizar la bitácora de progreso**

Agregar al final de `.superpowers/sdd/progress.md`:

```
# Progreso — Fase 4 sub-fase 1 (CTA + caja de descripcion configurable)

Plan: docs/superpowers/plans/2026-07-09-fase4-cta-caja.md

- Tarea 1 (modelo: BoxLayer.fill/text_color + CTALayer): complete
- Tarea 2 (render: desc configurable con fallback legado): complete
- Tarea 3 (render: rama cta nueva): complete
- Tarea 4 (adaptadores _build_layers_for / Exporter): complete
- Tarea 5 (migracion automatica de proyectos legado): complete
- Tarea 6 (batch_import crea CTALayer real): complete
- Tarea 7 (panel de propiedades reconoce cta + sliders w/h): complete
- Tarea 8 (selector de color fill/text_color): complete
- Tarea 9 (boton Agregar CTA + campo de texto propio): complete
- Tarea 10 (verificacion headless de cierre): complete, HEADLESS_OK

Veredicto: pendiente de revision final de rama completa.
```

- [ ] **Step 6: Commit**

```bash
git add verificaciones/fase4_cta_caja_verificacion.py verificaciones/fase4_cta_caja_control .superpowers/sdd/progress.md
git commit -m "test: agregar verificacion headless de cierre de Fase 4 sub-fase 1"
```

---

## Revisión final de rama (después de la Task 10)

Antes de mergear a `main`, correr una revisión de código completa sobre
todos los cambios de esta sub-fase, prestando especial atención a:

- Que la migración de `project_io.py` (Task 5) no pise proyectos que
  legítimamente quieran `w`/`h` muy chicos mayores a 0 pero cercanos —
  solo debe disparar en `w<=0`/`h<=0` exacto, nunca en valores positivos
  chicos.
- Que `_build_layers_for` (Task 4) no rompa la sincronización de texto en
  vivo que ya existe para `desc` (widget `txt_desc` del panel izquierdo) —
  la capa CTA no tiene ese patrón y no debe intentar usarlo.
- Que el selector de color (Task 8) no deje huérfano un `_color_alpha_start`
  si el usuario suelta el mouse fuera del slider (comportamiento aceptado
  de los demás sliders del proyecto, confirmar que es igual acá).
- Consistencia visual entre preview y export para capas CTA (mismo tamaño
  de fuente, mismo centrado) — comparar salida de
  `verificaciones/fase4_cta_caja_verificacion.py` contra una exportación
  real si es posible.
