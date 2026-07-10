# Fase 5 — Layouts A-E aplicables — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir aplicar, a la lámina activa, uno de 5 layouts predefinidos (A-E) que reposicionan logo/título/subtítulo/caja sin tocar su contenido ni la foto de fondo.

**Architecture:** Datos puros (`dcpub/presets/layouts.py`) + una función pura que arma un plan de cambios (`plan_aplicar_layout` en `dcpub/models.py`, calcada de `plan_copia_estilo` ya existente) + un método de UI (`App._apply_layout`, calcado de `App._copy_style_to_slide`) que convierte ese plan en una `CompositeCommand` de `PropertyChangeCommand` (undo/redo gratis) + 5 botones en el panel izquierdo.

**Tech Stack:** Python 3, dataclasses (`dcpub/models.py`), tkinter (`dcpub/app.py`), unittest.

## Global Constraints

- Un layout reposiciona ÚNICAMENTE campos que ya existen en el modelo: `x`, `y`, `size` en capas de texto (título/subtítulo); `x`, `y`, `w`, `h` en logo; `x`, `y`, `w` en caja de descripción. No se toca `h` de la caja (se deja en `0.0` = auto-altura).
- No se agrega el campo `align` ni ningún campo nuevo al modelo. No se toca `render.py`.
- La foto de fondo (`PhotoLayer`) nunca es tocada por ningún layout.
- Se aplica solo a la lámina activa (no hay "aplicar a todas" en esta sub-fase).
- El matcheo de capas usa la misma clave `(tipo, rol)` que ya usa `_estilo_key` en `dcpub/models.py:269`. Un layout que no encuentra una capa con esa clave en la lámina simplemente no genera cambio para esa clave (no es error).
- Valores exactos de los 5 layouts están fijados en la spec `docs/superpowers/specs/2026-07-10-fase5-layouts-design.md` — se copian verbatim en el Task 1, no se reinventan.

---

### Task 1: Datos de los 5 layouts

**Files:**
- Create: `dcpub/presets/layouts.py`
- Test: `tests/test_layouts_data.py`

**Interfaces:**
- Produces: `LAYOUTS: dict[str, dict]` — clave = `"A".."E"`, valor = `{"nombre": str, "campos": dict[tuple[str, str | None], dict[str, float]]}`. Las claves de `campos` son `("logo", None)`, `("text", "title")`, `("text", "subtitle")`, `("box", None)`. Tasks 2 y 3 consumen `LAYOUTS` importándolo de `dcpub.presets.layouts`.

- [ ] **Step 1: Write the failing test**

Crear `tests/test_layouts_data.py`:

```python
"""Tests de dcpub.presets.layouts (datos puros de los layouts A-E)."""

import unittest

from dcpub.presets.layouts import LAYOUTS


class TestLayoutsData(unittest.TestCase):
    def test_contiene_los_5_layouts_esperados(self):
        self.assertEqual(set(LAYOUTS.keys()), {"A", "B", "C", "D", "E"})

    def test_cada_layout_tiene_nombre_y_campos(self):
        for layout_id, layout in LAYOUTS.items():
            self.assertIn("nombre", layout, f"{layout_id} sin nombre")
            self.assertIsInstance(layout["nombre"], str)
            self.assertIn("campos", layout, f"{layout_id} sin campos")

    def test_campos_usan_solo_claves_tipo_rol_permitidas(self):
        claves_permitidas = {
            ("logo", None), ("text", "title"), ("text", "subtitle"), ("box", None),
        }
        for layout_id, layout in LAYOUTS.items():
            for clave in layout["campos"]:
                self.assertIn(clave, claves_permitidas,
                              f"{layout_id} usa clave no permitida: {clave}")

    def test_campos_de_texto_no_incluyen_w_ni_h(self):
        for layout_id, layout in LAYOUTS.items():
            for clave in [("text", "title"), ("text", "subtitle")]:
                campos = layout["campos"].get(clave, {})
                self.assertNotIn("w", campos, f"{layout_id}/{clave} no debe tener w")
                self.assertNotIn("h", campos, f"{layout_id}/{clave} no debe tener h")

    def test_campos_de_caja_no_incluyen_h(self):
        for layout_id, layout in LAYOUTS.items():
            campos = layout["campos"].get(("box", None), {})
            self.assertNotIn("h", campos, f"{layout_id}/box no debe tener h")

    def test_layout_a_coincide_con_valores_por_defecto(self):
        campos = LAYOUTS["A"]["campos"]
        self.assertEqual(campos[("logo", None)],
                          {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20})
        self.assertEqual(campos[("text", "title")], {"x": 0.055, "y": 0.42, "size": 0.087})
        self.assertEqual(campos[("text", "subtitle")], {"x": 0.50, "y": 0.55, "size": 0.050})
        self.assertEqual(campos[("box", None)], {"x": 0.05, "y": 0.808, "w": 0.90})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_layouts_data.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dcpub.presets.layouts'`

- [ ] **Step 3: Write the implementation**

Crear `dcpub/presets/layouts.py`:

```python
"""Layouts de marca predefinidos (A-E): reposicionan logo/título/subtítulo/
caja de una lámina sin tocar su contenido ni la foto de fondo. Ver
docs/superpowers/specs/2026-07-10-fase5-layouts-design.md para el diseño."""

LAYOUTS = {
    "A": {
        "nombre": "Actual",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.055, "y": 0.42, "size": 0.087},
            ("text", "subtitle"): {"x": 0.50, "y": 0.55, "size": 0.050},
            ("box", None): {"x": 0.05, "y": 0.808, "w": 0.90},
        },
    },
    "B": {
        "nombre": "Centrado",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.12, "y": 0.44, "size": 0.080},
            ("text", "subtitle"): {"x": 0.12, "y": 0.535, "size": 0.045},
            ("box", None): {"x": 0.12, "y": 0.80, "w": 0.76},
        },
    },
    "C": {
        "nombre": "Superior",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.055, "y": 0.26, "size": 0.075},
            ("text", "subtitle"): {"x": 0.055, "y": 0.335, "size": 0.045},
            ("box", None): {"x": 0.05, "y": 0.60, "w": 0.90},
        },
    },
    "D": {
        "nombre": "Minimalista",
        "campos": {
            ("logo", None): {"x": 0.42, "y": 0.022, "w": 0.16, "h": 0.16},
            ("text", "title"): {"x": 0.06, "y": 0.82, "size": 0.055},
            ("text", "subtitle"): {"x": 0.06, "y": 0.885, "size": 0.032},
            ("box", None): {"x": 0.06, "y": 0.925, "w": 0.55},
        },
    },
    "E": {
        "nombre": "Banda ancha",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.055, "y": 0.74, "size": 0.078},
            ("text", "subtitle"): {"x": 0.055, "y": 0.815, "size": 0.048},
            ("box", None): {"x": 0.05, "y": 0.58, "w": 0.90},
        },
    },
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_layouts_data.py -v`
Expected: PASS (6/6)

- [ ] **Step 5: Commit**

```bash
git add dcpub/presets/layouts.py tests/test_layouts_data.py
git commit -m "feat: agregar datos de los 5 layouts de marca (A-E)"
```

---

### Task 2: `plan_aplicar_layout` en el modelo

**Files:**
- Modify: `dcpub/models.py` (agregar después de `plan_copia_estilo`, alrededor de la línea 291)
- Test: `tests/test_models_layout.py`

**Interfaces:**
- Consumes: `LAYOUTS` de `dcpub.presets.layouts` (Task 1); `_estilo_key(layer)` ya existente en `dcpub/models.py:269`; `Slide`, `crear_slide_por_defecto` ya existentes.
- Produces: `plan_aplicar_layout(slide: Slide, layout_id: str) -> list[tuple[Layer, str, object]]`. Cada tupla es `(capa, atributo, valor_nuevo)`. Task 3 consume esta función tal cual (mismo contrato que `plan_copia_estilo`).

- [ ] **Step 1: Write the failing test**

Crear `tests/test_models_layout.py`:

```python
"""Tests de dcpub.models.plan_aplicar_layout (Fase 5 - Layouts A-E)."""

import unittest

from dcpub.models import crear_slide_por_defecto, plan_aplicar_layout


class TestPlanAplicarLayout(unittest.TestCase):
    def setUp(self):
        self.slide = crear_slide_por_defecto(
            "foto.jpg", titulo="Mi título", subtitulo="Mi subtítulo",
            descripcion="Mi descripción")

    def _aplicar(self, layout_id):
        cambios = plan_aplicar_layout(self.slide, layout_id)
        for capa, attr, valor in cambios:
            setattr(capa, attr, valor)
        return cambios

    def test_layout_b_reposiciona_titulo_subtitulo_y_caja(self):
        self._aplicar("B")
        logo = self.slide.layers[1]
        titulo = self.slide.layers[2]
        subtitulo = self.slide.layers[3]
        caja = self.slide.layers[4]
        self.assertEqual((titulo.x, titulo.y, titulo.size), (0.12, 0.44, 0.080))
        self.assertEqual((subtitulo.x, subtitulo.y, subtitulo.size), (0.12, 0.535, 0.045))
        self.assertEqual((caja.x, caja.y, caja.w), (0.12, 0.80, 0.76))
        self.assertEqual((logo.x, logo.y, logo.w, logo.h), (0.40, 0.022, 0.20, 0.20))

    def test_no_toca_el_contenido_de_las_capas(self):
        self._aplicar("D")
        titulo = self.slide.layers[2]
        subtitulo = self.slide.layers[3]
        caja = self.slide.layers[4]
        self.assertEqual(titulo.text, "Mi título")
        self.assertEqual(subtitulo.text, "Mi subtítulo")
        self.assertEqual(caja.text, "Mi descripción")

    def test_no_toca_la_foto_de_fondo(self):
        foto = self.slide.layers[0]
        x0, y0, w0, h0 = foto.x, foto.y, foto.w, foto.h
        self._aplicar("E")
        self.assertEqual((foto.x, foto.y, foto.w, foto.h), (x0, y0, w0, h0))

    def test_layout_inexistente_devuelve_lista_vacia(self):
        cambios = plan_aplicar_layout(self.slide, "Z")
        self.assertEqual(cambios, [])

    def test_lamina_sin_subtitulo_ignora_esa_clave_sin_error(self):
        del self.slide.layers[3]  # saca la capa de subtítulo
        cambios = plan_aplicar_layout(self.slide, "C")
        claves_afectadas = {(c[0].type, getattr(c[0], "role", None)) for c in cambios}
        self.assertNotIn(("text", "subtitle"), claves_afectadas)

    def test_caja_no_recibe_cambio_de_h(self):
        cambios = plan_aplicar_layout(self.slide, "A")
        caja = self.slide.layers[4]
        atributos_caja = {attr for capa, attr, _ in cambios if capa is caja}
        self.assertNotIn("h", atributos_caja)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models_layout.py -v`
Expected: FAIL con `ImportError: cannot import name 'plan_aplicar_layout'`

- [ ] **Step 3: Write the implementation**

En `dcpub/models.py`, agregar inmediatamente después del final de `plan_copia_estilo` (después de la línea ~291, antes de la siguiente definición de función o clase):

```python
def plan_aplicar_layout(slide: Slide, layout_id: str) -> list:
    """Compara las capas de `slide` con los campos definidos en
    LAYOUTS[layout_id] por tipo/rol y devuelve la lista de cambios a
    aplicar: tuplas (capa, atributo, valor_nuevo). Preserva el contenido
    de cada capa (texto/src) — solo cambia los campos listados en el
    layout. Capas de `slide` sin equivalente por tipo/rol en el layout no
    generan cambios. `layout_id` inexistente devuelve lista vacía."""
    from .presets.layouts import LAYOUTS
    layout = LAYOUTS.get(layout_id)
    if layout is None:
        return []

    cambios = []
    for layer in slide.layers:
        clave = _estilo_key(layer)
        campos = layout["campos"].get(clave)
        if campos is None:
            continue
        for attr, valor in campos.items():
            cambios.append((layer, attr, valor))
    return cambios
```

Nota: el import de `LAYOUTS` va dentro de la función (no al tope del módulo) para evitar un ciclo de import, porque `dcpub/presets/palette.py` ya importa de `dcpub.constants`, y `dcpub/models.py` es importado por módulos que a su vez pueden importar `dcpub.presets` — mismo patrón que ya usan otros imports diferidos en este archivo (ver `duplicar_slide`/otros usos de `from .` dentro de funciones en el resto del código).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models_layout.py -v`
Expected: PASS (6/6)

- [ ] **Step 5: Run the full test suite to confirm no regressions**

Run: `python -m pytest -q`
Expected: todos los tests existentes siguen en verde, más los 6 nuevos.

- [ ] **Step 6: Commit**

```bash
git add dcpub/models.py tests/test_models_layout.py
git commit -m "feat: agregar plan_aplicar_layout para calcular reposiciones de un layout"
```

---

### Task 3: UI — botones de layout y `App._apply_layout`

**Files:**
- Modify: `dcpub/app.py` (agregar método cerca de `_copy_style_to_slide`, línea ~1291; agregar botones en el panel izquierdo, después de la sección "Formato", línea ~260)
- Test: `tests/test_app_slides.py` (agregar clase nueva al final)

**Interfaces:**
- Consumes: `plan_aplicar_layout(slide, layout_id)` de `dcpub.models` (Task 2); `LAYOUTS` de `dcpub.presets.layouts` (Task 1, para los labels de los botones); `PropertyChangeCommand`, `CompositeCommand` de `dcpub.commands` (ya existentes); `self.commands` (`CommandStack`, ya existe en `App`); `self.slide`, `self.project.slides`, `self.current_slide_index` (ya existen); `slide.layout_tag` (campo ya existente en el modelo, hoy sin uso).
- Produces: `App._apply_layout(self, layout_id: str) -> None`. No otros task lo consumen — es el punto final de la cadena.

- [ ] **Step 1: Write the failing test**

Agregar al final de `tests/test_app_slides.py` (reusa `_make_app_with_two_slides` ya definido en ese archivo):

```python
class TestApplyLayout(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._render_now = lambda: None

    def test_repositions_title_of_active_slide(self):
        App._apply_layout(self.app, "B")
        titulo = self.app.slide.layers[2]
        self.assertEqual((titulo.x, titulo.y, titulo.size), (0.12, 0.44, 0.080))

    def test_does_not_touch_text_content(self):
        App._apply_layout(self.app, "D")
        titulo = self.app.slide.layers[2]
        self.assertEqual(titulo.text, "Titulo lamina 1")

    def test_sets_layout_tag_on_the_active_slide(self):
        App._apply_layout(self.app, "E")
        self.assertEqual(self.app.slide.layout_tag, "E")

    def test_does_not_affect_other_slides(self):
        App._apply_layout(self.app, "C")
        otra = self.app.project.slides[1]
        self.assertIsNone(otra.layout_tag)
        self.assertEqual(otra.layers[2].x, 0.055)  # valor A por defecto sin tocar

    def test_undo_reverts_the_layout(self):
        titulo = self.app.slide.layers[2]
        x_original = titulo.x
        App._apply_layout(self.app, "B")
        self.app.commands.undo()
        self.assertEqual(titulo.x, x_original)

    def test_unknown_layout_id_is_a_noop(self):
        titulo = self.app.slide.layers[2]
        x_original = titulo.x
        App._apply_layout(self.app, "Z")
        self.assertEqual(titulo.x, x_original)
        self.assertIsNone(self.app.slide.layout_tag)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_slides.py::TestApplyLayout -v`
Expected: FAIL con `AttributeError: type object 'App' has no attribute '_apply_layout'`

- [ ] **Step 3: Write the implementation — método `_apply_layout`**

En `dcpub/app.py`, agregar inmediatamente después de `_copy_style_to_slide` (después de la línea ~1307, antes de `def _reset`):

```python
    def _apply_layout(self, layout_id):
        """Reposiciona logo/título/subtítulo/caja de la lámina activa según
        el layout elegido (A-E), preservando su contenido. No afecta otras
        láminas ni la foto de fondo."""
        from .models import plan_aplicar_layout
        from .commands import PropertyChangeCommand, CompositeCommand
        cambios = plan_aplicar_layout(self.slide, layout_id)
        if not cambios:
            return
        comandos = [PropertyChangeCommand(layer, attr, getattr(layer, attr), nuevo)
                    for layer, attr, nuevo in cambios]
        comandos.append(PropertyChangeCommand(
            self.slide, "layout_tag", self.slide.layout_tag, layout_id))
        self.commands.push(CompositeCommand(comandos))
        self._render_now()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_app_slides.py::TestApplyLayout -v`
Expected: PASS (6/6)

- [ ] **Step 5: Agregar los 5 botones en el panel izquierdo**

En `dcpub/app.py`, insertar después de la línea `cb_formato.bind("<<ComboboxSelected>>", lambda e: self._on_format_change())` (línea ~260) y antes del comentario `# Capas` (línea ~262):

```python
        # Layout
        tk.Label(left, text="🧩  Layout", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        row_layout = tk.Frame(left, bg=PANEL)
        row_layout.pack(fill=tk.X, pady=(2, 10), **pad)
        from .presets.layouts import LAYOUTS
        for layout_id in ("A", "B", "C", "D", "E"):
            tk.Button(row_layout, text=layout_id, bg="#3d3d3d", fg=TEXT, relief="flat",
                      font=("Segoe UI", 9, "bold"), width=3,
                      command=lambda lid=layout_id: self._apply_layout(lid)).pack(
                side=tk.LEFT, padx=(0, 4))
```

(El `lambda lid=layout_id: ...` captura el valor de cada iteración del `for` por valor, no por referencia — sin ese default-arg los 5 botones terminarían llamando todos con `layout_id="E"`, el valor final del loop.)

- [ ] **Step 6: Run the full test suite to confirm no regressions**

Run: `python -m pytest -q`
Expected: todos los tests existentes siguen en verde, más los 6 nuevos de `TestApplyLayout`.

- [ ] **Step 7: Commit**

```bash
git add dcpub/app.py tests/test_app_slides.py
git commit -m "feat: conectar layouts A-E a la interfaz (botones + App._apply_layout)"
```

---

### Task 4: Verificación headless de cierre

**Files:**
- Create: `verificaciones/fase5_layouts_verificacion.py`

**Interfaces:**
- Consumes: `crear_proyecto_por_defecto` (`dcpub.models`), `plan_aplicar_layout` (`dcpub.models`, Task 2), `LAYOUTS` (`dcpub.presets.layouts`, Task 1), `_layers_from_slide` (`dcpub.exporter`), `compose` (`dcpub.render`), `FontManager` (`dcpub.fonts`) — todos ya existentes o agregados en tasks previos de este plan.
- Produces: script standalone, sin capas nuevas para tasks posteriores (es el último task del plan).

- [ ] **Step 1: Write the script**

Crear `verificaciones/fase5_layouts_verificacion.py`, siguiendo el mismo patrón que `verificaciones/fase4_texto_libre_verificacion.py`:

```python
"""Verificación headless de Fase 5 (Layouts A-E aplicables).
No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from dcpub.fonts import FontManager
from dcpub.models import crear_proyecto_por_defecto, plan_aplicar_layout
from dcpub.presets.layouts import LAYOUTS
from dcpub.render import compose
from dcpub.exporter import _layers_from_slide

OUT_DIR = Path(__file__).resolve().parent / "fase5_layouts_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)
    font_manager = FontManager()

    imagenes = {}
    for layout_id in LAYOUTS:
        project = crear_proyecto_por_defecto(foto_path)
        slide = project.slides[0]
        slide.layers[2].text = "Título de prueba"
        slide.layers[3].text = "Subtítulo de prueba"
        slide.layers[4].text = "Descripción de prueba para el layout"

        cambios = plan_aplicar_layout(slide, layout_id)
        assert cambios, f"layout {layout_id} no generó cambios"
        for capa, attr, valor in cambios:
            setattr(capa, attr, valor)
        slide.layout_tag = layout_id

        canvas_size = (slide.format["w"], slide.format["h"])
        layers = _layers_from_slide(slide)
        render, bboxes = compose(layers, canvas_size, font_manager, palette=project.palette)
        render.save(OUT_DIR / f"layout_{layout_id}.png")
        imagenes[layout_id] = render

    # Los 5 layouts deben producir posiciones de título distintas entre sí
    titulos_bbox = {}
    for layout_id in LAYOUTS:
        project = crear_proyecto_por_defecto(foto_path)
        slide = project.slides[0]
        for capa, attr, valor in plan_aplicar_layout(slide, layout_id):
            setattr(capa, attr, valor)
        titulo_layer = slide.layers[2]
        titulos_bbox[layout_id] = (titulo_layer.x, titulo_layer.y, titulo_layer.size)

    assert len(set(titulos_bbox.values())) == 5, \
        f"se esperaban 5 posiciones de título distintas, hubo repetidas: {titulos_bbox}"

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script**

Run: `python verificaciones/fase5_layouts_verificacion.py`
Expected: imprime `HEADLESS_OK` y la ruta de salida, sin excepciones. Se generan 5 archivos `layout_A.png` .. `layout_E.png` en `verificaciones/fase5_layouts_control/`.

- [ ] **Step 3: Revisión visual manual**

Abrir las 5 imágenes generadas y confirmar que título/subtítulo/caja quedan en posiciones distintas y legibles (sin superponerse entre sí ni salirse del canvas) en cada layout. Si algún valor numérico de `dcpub/presets/layouts.py` se ve mal, ajustarlo directamente en ese archivo y volver a correr el script — no requiere tocar ningún otro archivo.

- [ ] **Step 4: Commit**

```bash
git add verificaciones/fase5_layouts_verificacion.py
git commit -m "test: agregar verificacion headless de Layouts A-E"
```

---

## Cierre de la sub-fase

Con los 4 tasks completos: datos de layouts, función pura de cálculo, conexión a la UI con undo/redo, y verificación visual. Actualizar `.superpowers/sdd/progress.md` con el resultado de cada task y de la revisión final de rama antes de mergear a `main`, siguiendo el mismo protocolo usado en las sub-fases anteriores de Fase 4.
