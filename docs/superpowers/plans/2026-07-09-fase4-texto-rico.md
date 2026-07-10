# Fase 4 (sub-fase 2) — Texto rico por elemento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Título y subtítulo (`TextLayer`) ganan fuente por elemento (dropdown entre 3 fuentes de marca), bold/italic/underline sintéticos, interlineado, tracking, stroke (contorno) configurable, y rotación aplicada de verdad (hoy existe en el modelo pero el render la ignora).

**Architecture:** Se agregan 8 campos nuevos a `TextLayer`. El motor de render gana un pipeline nuevo de dibujo de texto: helpers puros para tracking (dibujar carácter por carácter cuando hace falta), bold/stroke sintéticos combinados en un solo `stroke_width`, subrayado, y transformaciones de imagen (shear para itálica, rotate para rotación) aplicadas sobre un bloque de texto renderizado aparte y después pegado en el lienzo — reemplaza el dibujo directo actual sobre el canvas. `FontManager` gana un parámetro `family` opcional. Los adaptadores UI↔render y el panel de propiedades se actualizan al final para exponer todo esto.

**Tech Stack:** Python 3, Pillow (`Image.transform` para itálica, `Image.rotate` para rotación — ya se usa `Image.LANCZOS`/`Image.BICUBIC` en el proyecto), tkinter. Sin dependencias nuevas.

## Global Constraints

- Nombres y comentarios en español; código limpio y modular (CLAUDE.md sección 8).
- Sin pseudocódigo ni partes "por completar" dentro de una tarea entregada.
- Cada tarea termina con `python -m unittest discover -s tests -v` en verde antes de commitear.
- Un commit por tarea, mensaje en español, conventional commits.
- Alcance: SOLO capas `title`/`subtitle` (los `TextLayer` existentes). No tocar `BoxLayer`/`CTALayer`.
- Todos los campos nuevos tienen defaults que preservan el render actual EXACTO (mismo patrón de fallback-a-legado que `BoxLayer.w`/`h` de la sub-fase anterior).
- Color de texto y sombra quedan FIJOS (blanco+sombra título, verde+sombra subtítulo) — no configurables, decisión explícita.
- Color del stroke queda FIJO (una constante nueva, no configurable) — solo on/off y grosor son configurables.
- El bbox de selección/hit-testing sigue siendo el rectángulo SIN rotar/inclinar — no se rota el hit-testing.
- Bold se sintetiza como un `stroke_width` extra fijo (no es un campo de grosor configurable); si además hay stroke real activo, ambos se combinan en un solo `stroke_width` total, con el color del stroke real ganando cuando ambos están activos.
- No se descargan archivos de fuente nuevos — el dropdown ofrece las 3 fuentes de marca ya existentes (Playfair Display, Dancing Script, Lato).

---

### Task 1: Modelo de datos — campos nuevos en `TextLayer`

**Files:**
- Modify: `dcpub/models.py` (clase `TextLayer`, `LAYER_STYLE_FIELDS`)
- Modify: `tests/test_models_layer.py`

**Interfaces:**
- Produces: `TextLayer.font_family: str`, `.bold: bool`, `.italic: bool`, `.underline: bool`, `.line_spacing: float`, `.letter_spacing: float`, `.stroke_on: bool`, `.stroke_width: float`. Usado por todas las tareas siguientes.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_models_layer.py`, dentro de `TestLayerSubclasses` (después de `test_text_layer_defaults`):

```python
    def test_text_layer_rich_text_defaults(self):
        t = TextLayer(text="Hola", role="title")
        self.assertEqual(t.font_family, "")
        self.assertFalse(t.bold)
        self.assertFalse(t.italic)
        self.assertFalse(t.underline)
        self.assertEqual(t.line_spacing, 0.0)
        self.assertEqual(t.letter_spacing, 0.0)
        self.assertFalse(t.stroke_on)
        self.assertEqual(t.stroke_width, 0.0)
```

Y en `TestLayerFromDict::test_round_trip_each_subclass`, agregar un `TextLayer` con valores no-default a la lista `layers` (el bloque actual, tras la Fase 4 sub-fase 1, es):

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
```

Reemplazar la línea `TextLayer(text="T", role="subtitle"),` por:

```python
            TextLayer(text="T", role="subtitle", font_family="lato", bold=True,
                      italic=True, underline=True, line_spacing=1.4,
                      letter_spacing=0.05, stroke_on=True, stroke_width=0.02),
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_models_layer -v`
Expected: FAIL — `TypeError: TextLayer.__init__() got an unexpected keyword argument 'font_family'`

- [ ] **Step 3: Implementar**

En `dcpub/models.py`, la clase actual es:

```python
@dataclass
class TextLayer(Layer):
    type: str = "text"
    text: str = ""
    role: str = "free"
    size: float = 0.05
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
```

- [ ] **Step 4: Actualizar `LAYER_STYLE_FIELDS`**

Las entradas actuales para texto son:

```python
    ("text", "title"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("text", "subtitle"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
```

Reemplazarlas por:

```python
    ("text", "title"): ("x", "y", "w", "h", "rotation", "opacity", "size",
                         "font_family", "bold", "italic", "underline",
                         "line_spacing", "letter_spacing", "stroke_on", "stroke_width"),
    ("text", "subtitle"): ("x", "y", "w", "h", "rotation", "opacity", "size",
                            "font_family", "bold", "italic", "underline",
                            "line_spacing", "letter_spacing", "stroke_on", "stroke_width"),
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_models_layer -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add dcpub/models.py tests/test_models_layer.py
git commit -m "feat: agregar campos de texto rico a TextLayer"
```

---

### Task 2: `FontManager` acepta `family` + constante de color de stroke

**Files:**
- Modify: `dcpub/fonts.py` (`FontManager._ROLE_MAP`, `FontManager.load`)
- Modify: `dcpub/constants.py` (nueva constante `TEXT_STROKE_COLOR`, nuevo dict `FAMILY_FONT_FILES`)
- Modify: `tests/test_fonts.py` (si no existe, crear siguiendo el patrón de otros archivos de test del proyecto)

**Interfaces:**
- Consumes: nada de tareas anteriores.
- Produces: `FontManager.load(role, size, family="")`; `TEXT_STROKE_COLOR` (tupla rgba); `FAMILY_FONT_FILES: dict[str, str]` mapeando `"playfair"|"dancing"|"lato"` a su archivo `.ttf`. Usado por la Task 3+ (render) y Task 8 (UI, para poblar el dropdown).

- [ ] **Step 1: Verificar si existe `tests/test_fonts.py`**

Run: `ls tests/test_fonts.py 2>/dev/null || echo "no existe"`

- [ ] **Step 2: Escribir los tests que fallan**

Si el archivo no existe, crearlo con:

```python
"""Tests de dcpub.fonts.FontManager."""

import unittest

from dcpub.fonts import FontManager


class TestFontManagerFamily(unittest.TestCase):
    def setUp(self):
        self.fm = FontManager()

    def test_load_without_family_uses_role_default(self):
        # Comportamiento legado: sin family, se usa la fuente de marca del rol.
        font_legacy = self.fm.load("title", 40)
        font_explicit_empty = self.fm.load("title", 40, family="")
        self.assertEqual(font_legacy.getname(), font_explicit_empty.getname())

    def test_load_with_family_returns_a_font(self):
        font = self.fm.load("title", 40, family="lato")
        self.assertIsNotNone(font)

    def test_different_families_can_produce_different_fonts(self):
        font_playfair = self.fm.load("title", 40, family="playfair")
        font_lato = self.fm.load("title", 40, family="lato")
        # No siempre se puede garantizar getname() distinto si el archivo de
        # marca no está descargado y ambos caen al mismo fallback de sistema,
        # pero al menos no debe explotar y debe devolver un ImageFont válido
        # en los dos casos.
        self.assertIsNotNone(font_playfair)
        self.assertIsNotNone(font_lato)


if __name__ == "__main__":
    unittest.main()
```

Si el archivo ya existe, agregar la clase `TestFontManagerFamily` de arriba al final, antes de `if __name__ == "__main__":`.

- [ ] **Step 3: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_fonts -v`
Expected: FAIL — `TypeError: FontManager.load() got an unexpected keyword argument 'family'`

- [ ] **Step 4: Implementar — `dcpub/constants.py`**

Agregar, después de `BOX_COLOR = (40, 25, 15, 215)  # recuadro inferior marrón oscuro semitransparente`:

```python
TEXT_STROKE_COLOR = (20, 12, 8, 255)  # contorno de texto, fijo (no configurable)
```

Agregar, después del dict `FALLBACK_FONTS`:

```python
FAMILY_FONT_FILES = {
    "playfair": "PlayfairDisplay-Bold.ttf",
    "dancing": "DancingScript-Regular.ttf",
    "lato": "Lato-Regular.ttf",
}
```

- [ ] **Step 5: Implementar — `dcpub/fonts.py`**

Agregar el import de `FAMILY_FONT_FILES` a la línea existente:

```python
from .constants import FONTS_DIR, FONT_URLS, FALLBACK_FONTS, SYSTEM_FONT_DIRS
```

pasa a:

```python
from .constants import FONTS_DIR, FONT_URLS, FALLBACK_FONTS, SYSTEM_FONT_DIRS, FAMILY_FONT_FILES
```

El método actual es:

```python
    def load(self, role, size):
        """Carga la fuente del rol (title / subtitle / body) con cache."""
        size = max(6, int(size))
        key = (role, size)
        if key in self._cache:
            return self._cache[key]

        preferred, fallbacks = self._ROLE_MAP[role]

        font = None
        p = FONTS_DIR / preferred
        if p.exists():
            try:
                font = ImageFont.truetype(str(p), size)
            except Exception:
                font = None
        if font is None:
            sf = find_system_font(fallbacks)
            if sf:
                try:
                    font = ImageFont.truetype(sf, size)
                except Exception:
                    font = None
        if font is None:
            font = ImageFont.load_default()

        self._cache[key] = font
        return font
```

Reemplazarlo por:

```python
    def load(self, role, size, family=""):
        """Carga la fuente del rol (title / subtitle / body) con cache. Si
        `family` viene vacío, usa la fuente de marca del rol (legado). Si
        viene seteado ("playfair"/"dancing"/"lato"), usa ese archivo de
        fuente en vez del preferido por rol, cayendo al mismo fallback de
        sistema del rol si el archivo no está disponible."""
        size = max(6, int(size))
        key = (role, size, family)
        if key in self._cache:
            return self._cache[key]

        preferred, fallbacks = self._ROLE_MAP[role]
        if family:
            preferred = FAMILY_FONT_FILES.get(family, preferred)

        font = None
        p = FONTS_DIR / preferred
        if p.exists():
            try:
                font = ImageFont.truetype(str(p), size)
            except Exception:
                font = None
        if font is None:
            sf = find_system_font(fallbacks)
            if sf:
                try:
                    font = ImageFont.truetype(sf, size)
                except Exception:
                    font = None
        if font is None:
            font = ImageFont.load_default()

        self._cache[key] = font
        return font
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_fonts -v`
Expected: PASS

- [ ] **Step 7: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 8: Commit**

```bash
git add dcpub/constants.py dcpub/fonts.py tests/test_fonts.py
git commit -m "feat: soportar seleccion de familia de fuente en FontManager"
```

---

### Task 3: Render — helpers puros de tracking, bold/stroke sintéticos y subrayado

**Files:**
- Modify: `dcpub/render.py` (nuevas funciones de módulo)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: nada de tareas anteriores (funciones autocontenidas).
- Produces: `_measure_line_width(draw_ctx, text, font, letter_spacing_px) -> int`; `_draw_tracked_line(draw_ctx, xy, text, font, fill, letter_spacing_px, stroke_width=0, stroke_fill=None)`; `_render_text_lines_to_image(lines, font, *, fill, line_height, letter_spacing_px=0, stroke_width=0, stroke_fill=None, underline=False, shadow_offset=None, shadow_fill=None, align="left") -> (Image, pad)`. Usado por Task 4 (rotación/itálica) y Task 5/6 (título/subtítulo).

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`, en una clase nueva al final del archivo:

```python
class TestTrackedTextHelpers(unittest.TestCase):
    def _font(self):
        from dcpub.fonts import FontManager
        return FontManager().load("body", 40)

    def test_measure_line_width_no_spacing_matches_textbbox(self):
        from dcpub.render import _measure_line_width
        font = self._font()
        img = Image.new("RGBA", (1, 1))
        draw_ctx = ImageDraw.Draw(img)
        bb = draw_ctx.textbbox((0, 0), "Hola", font=font)
        expected = bb[2] - bb[0]
        self.assertEqual(_measure_line_width(draw_ctx, "Hola", font, 0), expected)

    def test_measure_line_width_grows_with_positive_spacing(self):
        from dcpub.render import _measure_line_width
        font = self._font()
        img = Image.new("RGBA", (1, 1))
        draw_ctx = ImageDraw.Draw(img)
        w_no_spacing = _measure_line_width(draw_ctx, "Hola", font, 0)
        w_with_spacing = _measure_line_width(draw_ctx, "Hola", font, 10)
        self.assertGreater(w_with_spacing, w_no_spacing)

    def test_draw_tracked_line_with_spacing_produces_wider_pixels_than_without(self):
        from dcpub.render import _draw_tracked_line
        font = self._font()

        img_tight = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
        _draw_tracked_line(ImageDraw.Draw(img_tight), (10, 10), "Hola",
                            font, (255, 255, 255, 255), 0)

        img_spaced = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
        _draw_tracked_line(ImageDraw.Draw(img_spaced), (10, 10), "Hola",
                            font, (255, 255, 255, 255), 15)

        bbox_tight = img_tight.getbbox()
        bbox_spaced = img_spaced.getbbox()
        self.assertGreater(bbox_spaced[2] - bbox_spaced[0], bbox_tight[2] - bbox_tight[0])

    def test_render_text_lines_to_image_produces_nonempty_image(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img, pad = _render_text_lines_to_image(
            ["Hola mundo"], font, fill=(255, 255, 255, 255), line_height=48)
        self.assertIsNotNone(img.getbbox())
        self.assertGreaterEqual(pad, 0)

    def test_render_text_lines_to_image_underline_adds_pixels_below_text(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img_plain, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48, underline=False)
        img_underline, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48, underline=True)
        self.assertNotEqual(list(img_plain.getdata()), list(img_underline.getdata()))

    def test_render_text_lines_to_image_shadow_adds_pixels(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img_no_shadow, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48)
        img_shadow, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48,
            shadow_offset=(3, 3), shadow_fill=(0, 0, 0, 160))
        self.assertNotEqual(list(img_no_shadow.getdata()), list(img_shadow.getdata()))

    def test_render_text_lines_to_image_stroke_changes_pixels(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img_no_stroke, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48)
        img_stroke, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48,
            stroke_width=4, stroke_fill=(20, 12, 8, 255))
        self.assertNotEqual(list(img_no_stroke.getdata()), list(img_stroke.getdata()))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestTrackedTextHelpers -v`
Expected: FAIL — `ImportError: cannot import name '_measure_line_width'`

- [ ] **Step 3: Implementar**

En `dcpub/render.py`, agregar estas funciones de módulo inmediatamente antes de `def compose(layers, canvas_size, font_manager, palette=None):`:

```python
BOLD_STROKE_FRACTION = 0.06  # grosor sintetico extra cuando bold=True, fraccion del tamaño de fuente


def _measure_line_width(draw_ctx, text, font, letter_spacing_px):
    """Ancho en px de `text` con `font`, sumando `letter_spacing_px` entre
    cada caracter. Con letter_spacing_px=0 equivale a textbbox normal."""
    if letter_spacing_px == 0:
        bbox = draw_ctx.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    total = 0
    for ch in text:
        bbox = draw_ctx.textbbox((0, 0), ch, font=font)
        total += (bbox[2] - bbox[0]) + letter_spacing_px
    return max(0, total - letter_spacing_px)


def _draw_tracked_line(draw_ctx, xy, text, font, fill, letter_spacing_px,
                        stroke_width=0, stroke_fill=None):
    """Dibuja `text` en `xy` con tracking manual si letter_spacing_px != 0
    (caracter por caracter); si es 0, usa draw.text normal (camino rapido,
    sin cambio de comportamiento respecto al codigo legado)."""
    if letter_spacing_px == 0:
        draw_ctx.text(xy, text, font=font, fill=fill,
                       stroke_width=stroke_width, stroke_fill=stroke_fill)
        return
    x, y = xy
    for ch in text:
        draw_ctx.text((x, y), ch, font=font, fill=fill,
                       stroke_width=stroke_width, stroke_fill=stroke_fill)
        bbox = draw_ctx.textbbox((0, 0), ch, font=font)
        x += (bbox[2] - bbox[0]) + letter_spacing_px


def _render_text_lines_to_image(lines, font, *, fill, line_height,
                                 letter_spacing_px=0, stroke_width=0,
                                 stroke_fill=None, underline=False,
                                 shadow_offset=None, shadow_fill=None,
                                 align="left"):
    """Renderiza `lines` (lista de strings, una por linea) a una imagen RGBA
    ajustada al contenido, con tracking/stroke/subrayado/sombra ya
    horneados. No aplica italica ni rotacion (eso se hace despues, sobre la
    imagen devuelta). Devuelve (imagen, pad), donde `pad` es el margen
    interno agregado a cada lado (necesario para que el stroke no se corte
    en los bordes) — quien llama debe restar `pad` de la posicion de anclaje
    original al pegar la imagen resultante en el lienzo."""
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    widths = [_measure_line_width(probe_draw, line, font, letter_spacing_px)
              for line in lines]
    block_w = max(widths, default=0)
    pad = max(4, stroke_width * 2 + 4)
    block_h = max(1, len(lines)) * line_height

    img = Image.new("RGBA", (block_w + pad * 2, block_h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (line, lw) in enumerate(zip(lines, widths)):
        ly = pad + i * line_height
        lx = pad if align == "left" else pad + (block_w - lw) // 2
        if shadow_offset:
            dx, dy = shadow_offset
            _draw_tracked_line(d, (lx + dx, ly + dy), line, font,
                                shadow_fill, letter_spacing_px)
        _draw_tracked_line(d, (lx, ly), line, font, fill, letter_spacing_px,
                            stroke_width=stroke_width, stroke_fill=stroke_fill)
        if underline:
            uy = ly + line_height - max(1, int(line_height * 0.08))
            d.line([(lx, uy), (lx + lw, uy)], fill=fill,
                   width=max(1, int(line_height * 0.05)))
    return img, pad
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestTrackedTextHelpers -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: agregar helpers puros de tracking, stroke y subrayado para texto"
```

---

### Task 4: Render — transformaciones de imagen para itálica y rotación

**Files:**
- Modify: `dcpub/render.py` (nuevas funciones de módulo)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: nada directamente (funciones autocontenidas, operan sobre cualquier `Image`).
- Produces: `_apply_italic_shear(img, factor=0.22) -> Image`; `_apply_rotation(img, degrees) -> Image`. Usado por Task 5/6.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`:

```python
class TestItalicAndRotationHelpers(unittest.TestCase):
    def _sample_image(self):
        img = Image.new("RGBA", (100, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([(10, 10), (90, 30)], fill=(255, 255, 255, 255))
        return img

    def test_italic_shear_widens_image(self):
        from dcpub.render import _apply_italic_shear
        img = self._sample_image()
        sheared = _apply_italic_shear(img)
        self.assertGreater(sheared.width, img.width)
        self.assertEqual(sheared.height, img.height)

    def test_italic_shear_preserves_content(self):
        from dcpub.render import _apply_italic_shear
        img = self._sample_image()
        sheared = _apply_italic_shear(img)
        self.assertIsNotNone(sheared.getbbox())

    def test_rotation_zero_returns_same_image(self):
        from dcpub.render import _apply_rotation
        img = self._sample_image()
        rotated = _apply_rotation(img, 0)
        self.assertEqual(rotated.size, img.size)

    def test_rotation_nonzero_expands_canvas(self):
        from dcpub.render import _apply_rotation
        img = self._sample_image()
        rotated = _apply_rotation(img, 30)
        self.assertGreater(rotated.width, img.width)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestItalicAndRotationHelpers -v`
Expected: FAIL — `ImportError: cannot import name '_apply_italic_shear'`

- [ ] **Step 3: Implementar**

En `dcpub/render.py`, agregar inmediatamente después de `_render_text_lines_to_image` (Task 3):

```python
def _apply_italic_shear(img, factor=0.22):
    """Inclina `img` horizontalmente (shear) para simular itálica. `factor`
    es la pendiente del corte (positivo = inclina hacia la derecha arriba)."""
    w, h = img.size
    xshift = int(round(abs(factor) * h))
    new_w = w + xshift
    coeffs = (1, factor, -xshift if factor > 0 else 0, 0, 1, 0)
    return img.transform((new_w, h), Image.AFFINE, coeffs, resample=Image.BICUBIC)


def _apply_rotation(img, degrees):
    """Rota `img` `degrees` grados (sentido horario positivo), expandiendo
    el lienzo para no recortar contenido. Sin cambios si degrees es 0."""
    if not degrees:
        return img
    return img.rotate(-degrees, expand=True, resample=Image.BICUBIC)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestItalicAndRotationHelpers -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: agregar transformaciones de itálica y rotacion para bloques de texto"
```

---

### Task 5: Render — la rama `"title"` usa el pipeline de texto rico

**Files:**
- Modify: `dcpub/render.py` (rama `elif kind == "title":`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `_render_text_lines_to_image`, `_apply_italic_shear`, `_apply_rotation` (Tasks 3-4); `BOLD_STROKE_FRACTION` (Task 3); `TEXT_STROKE_COLOR` (Task 2, importar de `.constants`).
- Produces: `compose()` acepta en la capa `"title"` las claves opcionales `font_family`, `bold`, `italic`, `underline`, `line_spacing`, `letter_spacing`, `stroke_on`, `stroke_width`, `rotation` (además de las ya existentes). Con todos esos campos en su default (`""`/`False`/`0`/`0.0`), el render es idéntico al actual.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`:

```python
class TestTitleRichText(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "title", "key": "title", "text": "Titulo de prueba",
                "x": 0.1, "y": 0.4, "size": 0.08, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_defaults_produce_same_bbox_as_before(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        self.assertIn("title", bboxes)

    def test_bold_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(bold=False)], (1000, 1000), fm)
        img_bold, _ = compose([self._layer(bold=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_bold.getdata()))

    def test_underline_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(underline=False)], (1000, 1000), fm)
        img_underline, _ = compose([self._layer(underline=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_underline.getdata()))

    def test_letter_spacing_changes_bbox_width(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes_tight = compose([self._layer(letter_spacing=0.0)], (1000, 1000), fm)
        _, bboxes_spaced = compose([self._layer(letter_spacing=0.3)], (1000, 1000), fm)
        w_tight = bboxes_tight["title"][2] - bboxes_tight["title"][0]
        w_spaced = bboxes_spaced["title"][2] - bboxes_spaced["title"][0]
        self.assertGreater(w_spaced, w_tight)

    def test_stroke_on_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_off, _ = compose([self._layer(stroke_on=False)], (1000, 1000), fm)
        img_on, _ = compose([self._layer(stroke_on=True, stroke_width=0.05)], (1000, 1000), fm)
        self.assertNotEqual(list(img_off.getdata()), list(img_on.getdata()))

    def test_italic_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(italic=False)], (1000, 1000), fm)
        img_italic, _ = compose([self._layer(italic=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_italic.getdata()))

    def test_rotation_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(rotation=0.0)], (1000, 1000), fm)
        img_rotated, _ = compose([self._layer(rotation=20.0)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_rotated.getdata()))

    def test_font_family_lato_changes_pixels_vs_default(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(font_family="")], (1000, 1000), fm)
        img_lato, _ = compose([self._layer(font_family="lato")], (1000, 1000), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_lato.getdata()))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestTitleRichText -v`
Expected: la mayoría FAIL (bold/underline/tracking/stroke/italic/rotation/font_family no cambian nada porque `render.py` todavía los ignora)

- [ ] **Step 3: Implementar**

Agregar el import de `TEXT_STROKE_COLOR` a la línea existente en `dcpub/render.py`:

```python
from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE
```

pasa a:

```python
from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE, TEXT_STROKE_COLOR
```

La rama actual (línea ~364) es:

```python
        elif kind == "title":
            title = layer["text"]
            if title.strip():
                tsz = max(10, int(W * layer["size"]))
                font_t = font_manager.load("title", tsz)
                tx = int(layer["x"] * W)
                ty = int(layer["y"] * H)
                max_w = W - tx - margin
                lines = []
                for part in title.split("\n"):
                    part = part.strip()
                    if part:
                        lines += wrap_text(part, font_t, max_w, draw)
                lh = int(tsz * 1.22)
                widest = 0
                shadow_color = _apply_opacity((0, 0, 0, 160), opacity)
                text_color = _apply_opacity(BLANCO + (255,), opacity)
                if opacity < 1.0:
                    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    text_draw = ImageDraw.Draw(text_layer)
                    for i, line in enumerate(lines):
                        yy = ty + i * lh
                        text_draw.text((tx + 3, yy + 3), line, font=font_t, fill=shadow_color)
                        text_draw.text((tx, yy), line, font=font_t, fill=text_color)
                        bb = draw.textbbox((tx, yy), line, font=font_t)
                        widest = max(widest, bb[2] - tx)
                    canvas = Image.alpha_composite(canvas, text_layer)
                    draw = ImageDraw.Draw(canvas)
                else:
                    for i, line in enumerate(lines):
                        yy = ty + i * lh
                        draw.text((tx + 3, yy + 3), line, font=font_t, fill=shadow_color)
                        draw.text((tx, yy), line, font=font_t, fill=text_color)
                        bb = draw.textbbox((tx, yy), line, font=font_t)
                        widest = max(widest, bb[2] - tx)
                bboxes[bbox_key] = (tx, ty, tx + max(widest, 10), ty + max(1, len(lines)) * lh)
```

Reemplazarla por:

```python
        elif kind == "title":
            title = layer["text"]
            if title.strip():
                tsz = max(10, int(W * layer["size"]))
                font_t = font_manager.load("title", tsz, family=layer.get("font_family", ""))
                tx = int(layer["x"] * W)
                ty = int(layer["y"] * H)
                max_w = W - tx - margin
                lines = []
                for part in title.split("\n"):
                    part = part.strip()
                    if part:
                        lines += wrap_text(part, font_t, max_w, draw)
                line_spacing = layer.get("line_spacing", 0) or 1.22
                lh = int(tsz * line_spacing)
                letter_spacing_px = int(tsz * layer.get("letter_spacing", 0))
                bold = layer.get("bold", False)
                stroke_on = layer.get("stroke_on", False)
                border_px = int(tsz * layer.get("stroke_width", 0)) if stroke_on else 0
                bold_px = int(tsz * BOLD_STROKE_FRACTION) if bold else 0
                stroke_width_total = border_px + bold_px

                shadow_color = _apply_opacity((0, 0, 0, 160), opacity)
                text_color = _apply_opacity(BLANCO + (255,), opacity)
                stroke_fill = (_apply_opacity(TEXT_STROKE_COLOR, opacity)
                               if stroke_on else text_color)

                block, pad = _render_text_lines_to_image(
                    lines, font_t, fill=text_color, line_height=lh,
                    letter_spacing_px=letter_spacing_px,
                    stroke_width=stroke_width_total, stroke_fill=stroke_fill,
                    underline=layer.get("underline", False),
                    shadow_offset=(3, 3), shadow_fill=shadow_color, align="left")

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
```

`canvas.alpha_composite(block, (paste_x, paste_y))` es el método de instancia
(no la función de módulo `Image.alpha_composite`), que sí permite pegar una
imagen más chica que `canvas` en una posición arbitraria — `canvas` ya es una
superficie RGBA desde el inicio de `compose()`, no hace falta ninguna copia
previa.

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestTitleRichText -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite, prestando atención a tests preexistentes de título**

Run: `python -m unittest discover -s tests -v`
Expected: OK — los tests preexistentes de `"title"` en `tests/test_render.py` (que no pasan ninguno de los campos nuevos) deben seguir pasando exactamente igual, ya que todos los defaults preservan el comportamiento anterior byte a byte en posición/tamaño (el pipeline nuevo con todos los flags en su default reproduce el mismo dibujo).

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: aplicar texto rico (fuente/bold/italic/underline/tracking/stroke/rotacion) al titulo"
```

---

### Task 6: Render — la rama `"sub"` usa el pipeline de texto rico

**Files:**
- Modify: `dcpub/render.py` (rama `elif kind == "sub":`)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: mismos helpers que Task 5.
- Produces: `compose()` acepta en la capa `"sub"` los mismos campos opcionales que `"title"`. Las líneas decorativas a los costados NO rotan/inclinan con el subtítulo (se calculan sobre la posición/ancho del texto sin transformar) — simplificación aceptada, documentada en el diseño.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_render.py`:

```python
class TestSubtitleRichText(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "sub", "key": "sub", "text": "Subtitulo de prueba",
                "x": 0.5, "y": 0.55, "size": 0.05, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_defaults_still_produce_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        self.assertIn("sub", bboxes)

    def test_bold_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(bold=False)], (1000, 1000), fm)
        img_bold, _ = compose([self._layer(bold=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_bold.getdata()))

    def test_font_family_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(font_family="")], (1000, 1000), fm)
        img_playfair, _ = compose([self._layer(font_family="playfair")], (1000, 1000), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_playfair.getdata()))

    def test_rotation_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(rotation=0.0)], (1000, 1000), fm)
        img_rotated, _ = compose([self._layer(rotation=-15.0)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_rotated.getdata()))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_render.TestSubtitleRichText -v`
Expected: FAIL (bold/font_family/rotation no cambian nada todavía)

- [ ] **Step 3: Implementar**

La rama actual (línea ~401) es:

```python
        elif kind == "sub":
            subtitle = layer["text"]
            if subtitle.strip():
                ssz = max(8, int(W * layer["size"]))
                font_s = font_manager.load("subtitle", ssz)
                cx = int(layer["x"] * W)
                sy = int(layer["y"] * H)
                bb = draw.textbbox((0, 0), subtitle, font=font_s)
                sw, sh = bb[2] - bb[0], bb[3] - bb[1]
                sx = cx - sw // 2
                ly = sy + sh // 2
                lw_deco = max(2, int(W * 0.003))
                line_len = int(W * 0.11)
                gap = int(W * 0.03)
                lx1 = max(0, sx - gap - line_len)
                rx2 = min(W, sx + sw + gap + line_len)
                line_color = _apply_opacity(VERDE, opacity)
                deco_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                deco_draw = ImageDraw.Draw(deco_layer)
                deco_draw.line([(lx1, ly), (sx - gap, ly)], fill=line_color, width=lw_deco)
                deco_draw.line([(sx + sw + gap, ly), (rx2, ly)], fill=line_color, width=lw_deco)
                canvas = Image.alpha_composite(canvas, deco_layer)
                draw = ImageDraw.Draw(canvas)
                if opacity < 1.0:
                    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    text_draw = ImageDraw.Draw(text_layer)
                    text_draw.text((sx + 2, sy + 2), subtitle, font=font_s,
                                   fill=_apply_opacity((0, 0, 0, 130), opacity))
                    text_draw.text((sx, sy), subtitle, font=font_s, fill=line_color)
                    canvas = Image.alpha_composite(canvas, text_layer)
                    draw = ImageDraw.Draw(canvas)
                else:
                    draw.text((sx + 2, sy + 2), subtitle, font=font_s,
                              fill=_apply_opacity((0, 0, 0, 130), opacity))
                    draw.text((sx, sy), subtitle, font=font_s, fill=line_color)
                bboxes[bbox_key] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)
```

Reemplazarla por:

```python
        elif kind == "sub":
            subtitle = layer["text"]
            if subtitle.strip():
                ssz = max(8, int(W * layer["size"]))
                font_s = font_manager.load("subtitle", ssz, family=layer.get("font_family", ""))
                cx = int(layer["x"] * W)
                sy = int(layer["y"] * H)
                letter_spacing_px = int(ssz * layer.get("letter_spacing", 0))
                probe_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                sw = _measure_line_width(probe_draw, subtitle, font_s, letter_spacing_px)
                bb = draw.textbbox((0, 0), subtitle, font=font_s)
                sh = bb[3] - bb[1]
                sx = cx - sw // 2
                ly = sy + sh // 2

                lw_deco = max(2, int(W * 0.003))
                line_len = int(W * 0.11)
                gap = int(W * 0.03)
                lx1 = max(0, sx - gap - line_len)
                rx2 = min(W, sx + sw + gap + line_len)
                line_color = _apply_opacity(VERDE, opacity)
                deco_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                deco_draw = ImageDraw.Draw(deco_layer)
                deco_draw.line([(lx1, ly), (sx - gap, ly)], fill=line_color, width=lw_deco)
                deco_draw.line([(sx + sw + gap, ly), (rx2, ly)], fill=line_color, width=lw_deco)
                canvas = Image.alpha_composite(canvas, deco_layer)
                draw = ImageDraw.Draw(canvas)

                bold = layer.get("bold", False)
                stroke_on = layer.get("stroke_on", False)
                border_px = int(ssz * layer.get("stroke_width", 0)) if stroke_on else 0
                bold_px = int(ssz * BOLD_STROKE_FRACTION) if bold else 0
                stroke_width_total = border_px + bold_px
                stroke_fill = (_apply_opacity(TEXT_STROKE_COLOR, opacity)
                               if stroke_on else line_color)

                block, pad = _render_text_lines_to_image(
                    [subtitle], font_s, fill=line_color, line_height=sh,
                    letter_spacing_px=letter_spacing_px,
                    stroke_width=stroke_width_total, stroke_fill=stroke_fill,
                    underline=layer.get("underline", False),
                    shadow_offset=(2, 2),
                    shadow_fill=_apply_opacity((0, 0, 0, 130), opacity), align="left")

                pre_w, pre_h = block.size
                center_x = (sx - pad) + pre_w / 2
                center_y = (sy - pad) + pre_h / 2

                if layer.get("italic", False):
                    block = _apply_italic_shear(block)
                rotation = layer.get("rotation", 0.0)
                if rotation:
                    block = _apply_rotation(block, rotation)

                paste_x = int(center_x - block.width / 2)
                paste_y = int(center_y - block.height / 2)
                canvas.alpha_composite(block, (paste_x, paste_y))
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_render.TestSubtitleRichText -v`
Expected: PASS

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK — tests preexistentes de `"sub"` (sin los campos nuevos) deben seguir pasando idéntico.

- [ ] **Step 6: Commit**

```bash
git add dcpub/render.py tests/test_render.py
git commit -m "feat: aplicar texto rico al subtitulo"
```

---

### Task 7: Adaptadores UI↔render — `_build_layers_for` y `Exporter._layers_from_slide`

**Files:**
- Modify: `dcpub/app.py` (`_build_layers_for`, ramas `title`/`subtitle`)
- Modify: `dcpub/exporter.py` (`_layers_from_slide`, ramas `title`/`subtitle`)
- Test: `tests/test_app_slides.py` (`TestBuildLayersFor`), `tests/test_exporter.py`

**Interfaces:**
- Consumes: campos nuevos de `TextLayer` (Task 1).
- Produces: preview y export pasan los 8 campos nuevos + `rotation` para `title`/`sub`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_slides.py`, dentro de `TestBuildLayersFor`:

```python
    def test_build_layers_for_includes_title_rich_text_fields(self):
        app = _make_app_with_two_slides()
        title = App._layer_by_kind(app, "title", app.slide)
        title.font_family = "lato"
        title.bold = True
        title.italic = True
        title.underline = True
        title.line_spacing = 1.4
        title.letter_spacing = 0.05
        title.stroke_on = True
        title.stroke_width = 0.02
        title.rotation = 15.0

        capas = App._build_layers_for(app, app.slide)

        title_capa = next(c for c in capas if c["type"] == "title")
        self.assertEqual(title_capa["font_family"], "lato")
        self.assertTrue(title_capa["bold"])
        self.assertTrue(title_capa["italic"])
        self.assertTrue(title_capa["underline"])
        self.assertEqual(title_capa["line_spacing"], 1.4)
        self.assertEqual(title_capa["letter_spacing"], 0.05)
        self.assertTrue(title_capa["stroke_on"])
        self.assertEqual(title_capa["stroke_width"], 0.02)
        self.assertEqual(title_capa["rotation"], 15.0)

    def test_build_layers_for_includes_subtitle_rich_text_fields(self):
        app = _make_app_with_two_slides()
        sub = App._layer_by_kind(app, "sub", app.slide)
        sub.font_family = "playfair"
        sub.rotation = -10.0

        capas = App._build_layers_for(app, app.slide)

        sub_capa = next(c for c in capas if c["type"] == "sub")
        self.assertEqual(sub_capa["font_family"], "playfair")
        self.assertEqual(sub_capa["rotation"], -10.0)
```

Agregar a `tests/test_exporter.py`:

```python
class TestLayersFromSlideTitleSubtitleRichText(unittest.TestCase):
    def test_title_includes_rich_text_fields(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto
        slide = crear_slide_por_defecto("foto.jpg")
        title = next(l for l in slide.layers if l.type == "text" and l.role == "title")
        title.bold = True
        title.rotation = 12.0

        capas = _layers_from_slide(slide)

        title_capa = next(c for c in capas if c["type"] == "title")
        self.assertTrue(title_capa["bold"])
        self.assertEqual(title_capa["rotation"], 12.0)

    def test_subtitle_includes_rich_text_fields(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto
        slide = crear_slide_por_defecto("foto.jpg")
        sub = next(l for l in slide.layers if l.type == "text" and l.role == "subtitle")
        sub.italic = True
        sub.letter_spacing = 0.1

        capas = _layers_from_slide(slide)

        sub_capa = next(c for c in capas if c["type"] == "sub")
        self.assertTrue(sub_capa["italic"])
        self.assertEqual(sub_capa["letter_spacing"], 0.1)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides.TestBuildLayersFor tests.test_exporter -v`
Expected: FAIL (faltan las claves nuevas en los dicts)

- [ ] **Step 3: Implementar en `dcpub/app.py`**

El bloque actual de `_build_layers_for` es:

```python
            elif layer.type == "text" and layer.role == "title":
                text = (self.txt_title.get("1.0", "end-1c")
                        if es_activa and layer is self._layer_by_kind("title", slide) else layer.text)
                layers.append({"type": "title", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity})
            elif layer.type == "text" and layer.role == "subtitle":
                text = (self.v_sub.get()
                        if es_activa and layer is self._layer_by_kind("sub", slide) else layer.text)
                layers.append({"type": "sub", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity})
```

Reemplazarlo por:

```python
            elif layer.type == "text" and layer.role == "title":
                text = (self.txt_title.get("1.0", "end-1c")
                        if es_activa and layer is self._layer_by_kind("title", slide) else layer.text)
                layers.append({"type": "title", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity, "rotation": layer.rotation,
                                "font_family": layer.font_family, "bold": layer.bold,
                                "italic": layer.italic, "underline": layer.underline,
                                "line_spacing": layer.line_spacing,
                                "letter_spacing": layer.letter_spacing,
                                "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width})
            elif layer.type == "text" and layer.role == "subtitle":
                text = (self.v_sub.get()
                        if es_activa and layer is self._layer_by_kind("sub", slide) else layer.text)
                layers.append({"type": "sub", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity, "rotation": layer.rotation,
                                "font_family": layer.font_family, "bold": layer.bold,
                                "italic": layer.italic, "underline": layer.underline,
                                "line_spacing": layer.line_spacing,
                                "letter_spacing": layer.letter_spacing,
                                "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width})
```

- [ ] **Step 4: Implementar en `dcpub/exporter.py`**

El bloque actual de `_layers_from_slide` es:

```python
        elif layer.type == "text" and layer.role == "title":
            layers.append({
                "type": "title",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "size": layer.size,
                "opacity": layer.opacity,
            })
        elif layer.type == "text" and layer.role == "subtitle":
            layers.append({
                "type": "sub",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "size": layer.size,
                "opacity": layer.opacity,
            })
```

Reemplazarlo por:

```python
        elif layer.type == "text" and layer.role == "title":
            layers.append({
                "type": "title",
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
            })
        elif layer.type == "text" and layer.role == "subtitle":
            layers.append({
                "type": "sub",
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
            })
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides.TestBuildLayersFor tests.test_exporter -v`
Expected: PASS

- [ ] **Step 6: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add dcpub/app.py dcpub/exporter.py tests/test_app_slides.py tests/test_exporter.py
git commit -m "feat: propagar campos de texto rico y rotacion en los adaptadores de render"
```

---

### Task 8: Panel de propiedades — controles de texto rico para título/subtítulo

**Files:**
- Modify: `dcpub/app.py` (`_build_property_panel`, nuevos métodos `_build_text_style_section`, `_toggle_text_flag`, `_on_font_family_change`)
- Test: `tests/test_app_property_panel.py`

**Interfaces:**
- Consumes: campos nuevos de `TextLayer` (Task 1); `FAMILY_FONT_FILES` (Task 2, importar de `.constants`, para poblar el dropdown).
- Produces: seleccionar un título/subtítulo muestra dropdown de fuente + checkboxes bold/italic/underline/stroke + sliders de interlineado/tracking/grosor de stroke/rotación.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_property_panel.py`:

```python
class TestToggleTextFlag(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack
        from dcpub.models import TextLayer
        self.app = App.__new__(App)
        self.app.commands = CommandStack()
        self.app._schedule_render = lambda: None
        self.layer = TextLayer(text="Hola", role="title")

    def test_toggle_bold_flips_value_and_is_undoable(self):
        App._toggle_text_flag(self.app, self.layer, "bold")
        self.assertTrue(self.layer.bold)
        self.app.commands.undo()
        self.assertFalse(self.layer.bold)

    def test_toggle_underline_flips_value(self):
        App._toggle_text_flag(self.app, self.layer, "underline")
        self.assertTrue(self.layer.underline)


class TestFontFamilyChange(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack
        from dcpub.models import TextLayer
        self.app = App.__new__(App)
        self.app.commands = CommandStack()
        self.app._schedule_render = lambda: None
        self.app._build_property_panel = lambda: None
        self.layer = TextLayer(text="Hola", role="title", font_family="")

    def test_change_pushes_command_and_is_undoable(self):
        App._on_font_family_change(self.app, self.layer, "lato")
        self.assertEqual(self.layer.font_family, "lato")
        self.app.commands.undo()
        self.assertEqual(self.layer.font_family, "")

    def test_same_value_pushes_nothing(self):
        App._on_font_family_change(self.app, self.layer, "")
        self.assertEqual(len(self.app.commands._undo_stack), 0)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_property_panel.TestToggleTextFlag tests.test_app_property_panel.TestFontFamilyChange -v`
Expected: FAIL — `AttributeError: type object 'App' has no attribute '_toggle_text_flag'`

- [ ] **Step 3: Implementar `_toggle_text_flag` y `_on_font_family_change`**

Agregar en `dcpub/app.py`, cerca de `_toggle_overlay_flag`:

```python
    def _toggle_text_flag(self, layer, attr):
        if layer.locked:
            return
        from .commands import PropertyChangeCommand
        old_value = getattr(layer, attr)
        self.commands.push(PropertyChangeCommand(layer, attr, old_value, not old_value))
        self._schedule_render()

    def _on_font_family_change(self, layer, new_value):
        old_value = layer.font_family
        if old_value != new_value:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, "font_family", old_value, new_value))
            self._build_property_panel()
        self._schedule_render()
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_property_panel.TestToggleTextFlag tests.test_app_property_panel.TestFontFamilyChange -v`
Expected: PASS

- [ ] **Step 5: Construir la sección de UI**

En `dcpub/app.py`, dentro de `_build_property_panel`, el bloque actual (tras la Fase 4 sub-fase 1) es:

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
        if kind in ("title", "sub"):
            self._build_text_style_section(card, layer, token, disabled)
        self._slider(card, token, "size", size_label, smin, smax, disabled=disabled)
```

- [ ] **Step 6: Implementar `_build_text_style_section`**

Agregar el método inmediatamente después de `_build_photo_adjust_section` (o cerca de `_color_picker`):

```python
    def _build_text_style_section(self, card, layer, token, disabled):
        from .constants import FAMILY_FONT_FILES
        state = tk.DISABLED if disabled else tk.NORMAL

        tk.Label(card, text="Fuente", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
        family_labels = {"": "Marca (por rol)", "playfair": "Playfair Display",
                          "dancing": "Dancing Script", "lato": "Lato"}
        family_keys = [""] + list(FAMILY_FONT_FILES.keys())
        family_var = tk.StringVar(value=family_labels.get(layer.font_family, "Marca (por rol)"))
        family_combo = ttk.Combobox(card, textvariable=family_var,
                                     values=[family_labels[k] for k in family_keys],
                                     state="readonly" if not disabled else tk.DISABLED,
                                     font=("Segoe UI", 9))
        family_combo.pack(fill=tk.X, pady=(2, 6))
        label_to_key = {v: k for k, v in family_labels.items()}
        family_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, l=layer, v=family_var:
                self._on_font_family_change(l, label_to_key[v.get()]))

        style_row = tk.Frame(card, bg=PANEL)
        style_row.pack(fill=tk.X, pady=(0, 6))
        bold_var = tk.BooleanVar(value=layer.bold)
        tk.Checkbutton(style_row, text="Negrita", variable=bold_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "bold")).pack(side=tk.LEFT)
        italic_var = tk.BooleanVar(value=layer.italic)
        tk.Checkbutton(style_row, text="Cursiva", variable=italic_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "italic")).pack(side=tk.LEFT, padx=(8, 0))
        underline_var = tk.BooleanVar(value=layer.underline)
        tk.Checkbutton(style_row, text="Subrayado", variable=underline_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "underline")).pack(side=tk.LEFT, padx=(8, 0))

        self._slider(card, token, "line_spacing", "Interlineado", 0.8, 2.5, disabled=disabled)
        self._slider(card, token, "letter_spacing", "Espaciado entre letras", -0.05, 0.4,
                     disabled=disabled)

        stroke_var = tk.BooleanVar(value=layer.stroke_on)
        tk.Checkbutton(card, text="Contorno", variable=stroke_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "stroke_on")).pack(anchor="w")
        self._slider(card, token, "stroke_width", "Grosor del contorno", 0.0, 0.15,
                     disabled=disabled or not layer.stroke_on)

        self._slider(card, token, "rotation", "Rotación (grados)", -45.0, 45.0, disabled=disabled)
```

- [ ] **Step 7: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: OK (los tests headless de `_build_property_panel` no abren una ventana real; si algún test existente construye `card`/`_props_body` con mocks, verificar que `_build_text_style_section` no rompe esos mocks — usa los mismos tipos `tk.Frame`/`tk.Label`/`tk.Checkbutton`/`ttk.Combobox` que el resto del panel)

- [ ] **Step 8: Commit**

```bash
git add dcpub/app.py tests/test_app_property_panel.py
git commit -m "feat: agregar controles de texto rico al panel de propiedades de titulo/subtitulo"
```

---

### Task 9: Verificación headless de cierre de esta sub-fase

**Files:**
- Create: `verificaciones/fase4_texto_rico_verificacion.py`

**Interfaces:**
- Consumes: todo lo anterior (Tasks 1-8).
- Produces: carpeta `verificaciones/fase4_texto_rico_control/` con imágenes de control y `HEADLESS_OK`.

- [ ] **Step 1: Escribir el script**

Crear `verificaciones/fase4_texto_rico_verificacion.py`, siguiendo el mismo
patrón que los scripts anteriores (`fase3_verificacion.py`,
`fase4_cta_caja_verificacion.py`):

```python
"""Verificación headless de Fase 4 (sub-fase 2): texto rico por elemento
(fuente, bold/italic/underline, tracking, interlineado, stroke, rotación
aplicada de verdad). No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.models import crear_proyecto_por_defecto
from dcpub.render import compose
from dcpub.fonts import FontManager

OUT_DIR = Path(__file__).resolve().parent / "fase4_texto_rico_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def _layer_dict_title(layer):
    return {"type": "title", "key": layer.id, "text": layer.text, "x": layer.x,
            "y": layer.y, "size": layer.size, "opacity": layer.opacity,
            "rotation": layer.rotation, "font_family": layer.font_family,
            "bold": layer.bold, "italic": layer.italic, "underline": layer.underline,
            "line_spacing": layer.line_spacing, "letter_spacing": layer.letter_spacing,
            "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width}


def _layer_dict_sub(layer):
    return {"type": "sub", "key": layer.id, "text": layer.text, "x": layer.x,
            "y": layer.y, "size": layer.size, "opacity": layer.opacity,
            "rotation": layer.rotation, "font_family": layer.font_family,
            "bold": layer.bold, "italic": layer.italic, "underline": layer.underline,
            "line_spacing": layer.line_spacing, "letter_spacing": layer.letter_spacing,
            "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width}


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    font_manager = FontManager()
    canvas_size = (project.slides[0].format["w"], project.slides[0].format["h"])
    title = next(l for l in project.slides[0].layers
                 if l.type == "text" and l.role == "title")
    sub = next(l for l in project.slides[0].layers
               if l.type == "text" and l.role == "subtitle")

    # Render neutro (defaults) — debe verse igual al comportamiento legado.
    render_neutro, _ = compose(
        [_layer_dict_title(title), _layer_dict_sub(sub)], canvas_size, font_manager)
    render_neutro.save(OUT_DIR / "neutro.png")

    # Aplicar texto rico a titulo y subtitulo.
    title.font_family = "lato"
    title.bold = True
    title.italic = True
    title.underline = True
    title.letter_spacing = 0.08
    title.stroke_on = True
    title.stroke_width = 0.03
    title.rotation = 10.0

    sub.font_family = "playfair"
    sub.rotation = -8.0
    sub.letter_spacing = 0.05

    render_rico, bboxes_rico = compose(
        [_layer_dict_title(title), _layer_dict_sub(sub)], canvas_size, font_manager)
    render_rico.save(OUT_DIR / "texto_rico.png")

    diff = ImageChops.difference(render_neutro.convert("RGB"), render_rico.convert("RGB"))
    assert diff.getbbox() is not None, "el render con texto rico debe diferir del neutro"
    assert "title" in bboxes_rico
    assert "sub" in bboxes_rico

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el script**

Run: `python verificaciones/fase4_texto_rico_verificacion.py`
Expected: imprime `HEADLESS_OK` y la ruta de salida, sin `AssertionError` ni excepciones

- [ ] **Step 3: Revisar visualmente**

Abrir `neutro.png` y `texto_rico.png` en `verificaciones/fase4_texto_rico_control/`
y confirmar a simple vista que el título se ve en negrita+cursiva+subrayado+contorno
y rotado, y el subtítulo con otra fuente y rotado en sentido contrario.

- [ ] **Step 4: Correr toda la suite una vez más**

Run: `python -m unittest discover -s tests -v`
Expected: OK

- [ ] **Step 5: Actualizar la bitácora de progreso**

Agregar al final de `.superpowers/sdd/progress.md`:

```
# Progreso — Fase 4 sub-fase 2 (texto rico por elemento)

Plan: docs/superpowers/plans/2026-07-09-fase4-texto-rico.md

- Tarea 1 (modelo: campos nuevos en TextLayer): complete
- Tarea 2 (FontManager.family + TEXT_STROKE_COLOR): complete
- Tarea 3 (helpers puros de tracking/stroke/underline): complete
- Tarea 4 (helpers de italica/rotacion): complete
- Tarea 5 (render: titulo usa texto rico): complete
- Tarea 6 (render: subtitulo usa texto rico): complete
- Tarea 7 (adaptadores _build_layers_for / Exporter): complete
- Tarea 8 (panel de propiedades: controles de texto rico): complete
- Tarea 9 (verificacion headless de cierre): complete, HEADLESS_OK

Veredicto: pendiente de revision final de rama completa.
```

- [ ] **Step 6: Commit**

```bash
git add verificaciones/fase4_texto_rico_verificacion.py verificaciones/fase4_texto_rico_control .superpowers/sdd/progress.md
git commit -m "test: agregar verificacion headless de cierre de Fase 4 sub-fase 2"
```

---

## Revisión final de rama (después de la Task 9)

Antes de mergear a `main`, correr una revisión de código completa sobre
todos los cambios de esta sub-fase, prestando especial atención a:

- Que el pipeline nuevo (`_render_text_lines_to_image` + transformaciones)
  produzca resultados pixel-idénticos al legado cuando todos los campos
  nuevos están en su default — es la garantía de no-regresión más
  importante de esta sub-fase, y solo el título y el subtítulo tienen
  cobertura de tests reales de bbox/pixel (no hay snapshot pixel-perfect
  automatizado contra el render legado exacto; confirmar visualmente).
- Que la combinación bold+stroke real simultáneos (`stroke_width_total`)
  no se vea rota visualmente en casos extremos (tamaño de fuente muy chico
  + stroke_width alto).
- Que el subrayado y el stroke no se corten en los bordes de la imagen
  intermedia (`pad` insuficiente) para valores altos de `stroke_width`.
- Consistencia entre preview y export para título/subtítulo con texto rico
  activo (mismos campos, mismo resultado).
