# Fase 2 — Carruseles (Secciones 1-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el editor de una sola lámina en un editor de carrusel multi-lámina: estado de lámina activa, panel de miniaturas con agregar/duplicar/eliminar/reordenar, copiar estilo entre láminas y logo compartido en todo el carrusel.

**Architecture:** El modelo (`Project.slides`, `Project.shared`) ya soporta multi-lámina desde Fase 1. Se agregan comandos de lista de láminas a `commands.py` (mismo patrón que los comandos de capa existentes), operaciones puras de lámina a `models.py`, estado de lámina activa y métodos de acción a `App` (`app.py`), y un módulo nuevo `dcpub/slides_panel.py` para el panel de miniaturas — es el primer corte de extracción de UI fuera de `app.py` desde que existe el proyecto.

**Tech Stack:** Python 3, Tkinter, Pillow. Sin dependencias nuevas.

## Global Constraints

- Nombres, comentarios y mensajes de UI en español.
- No tocar `dcpub/batch_import.py` ni `dcpub/exporter.py::exportar_todas` — están asignados a otra sesión (Codex) en paralelo.
- Cada paso de código muestra el código completo, no fragmentos parciales.
- Ejecutar `python -m unittest discover -s tests -v` con el runtime `C:\Users\MIPC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe` al final de cada tarea; debe quedar en verde antes de pasar a la siguiente.
- Un commit por tarea cerrada.
- La foto base nunca se deforma (restricción de todo el proyecto, no se toca la lógica de cover/zoom/offset en ninguna tarea de este plan).

---

### Task 1: Comandos de lista de láminas (`commands.py`)

**Files:**
- Modify: `dcpub/commands.py` (agregar clases después de `ReorderLayerCommand`, línea 74)
- Test: `tests/test_commands.py` (agregar al final, antes de `if __name__ == "__main__":`)

**Interfaces:**
- Produces: `AddSlideCommand(slides_list, slide, index)`, `DeleteSlideCommand(slides_list, slide)`, `ReorderSlideCommand(slides_list, index_a, index_b)` — mismo contrato `execute()`/`undo()` que los comandos de capa existentes.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_commands.py`, después de la clase `TestReorderLayerCommand` (línea 79) y antes de `TestCompositeCommand`:

```python
class TestAddSlideCommand(unittest.TestCase):
    def test_execute_inserts_at_index(self):
        slides = [_Dummy(name="a"), _Dummy(name="c")]
        new = _Dummy(name="b")
        cmd = AddSlideCommand(slides, new, 1)
        cmd.execute()
        self.assertEqual([s.name for s in slides], ["a", "b", "c"])

    def test_undo_removes_it(self):
        slides = [_Dummy(name="a"), _Dummy(name="c")]
        new = _Dummy(name="b")
        cmd = AddSlideCommand(slides, new, 1)
        cmd.execute()
        cmd.undo()
        self.assertEqual([s.name for s in slides], ["a", "c"])


class TestDeleteSlideCommand(unittest.TestCase):
    def test_execute_removes_slide(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = DeleteSlideCommand(slides, b)
        cmd.execute()
        self.assertEqual([s.name for s in slides], ["a", "c"])

    def test_undo_reinserts_at_original_index(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = DeleteSlideCommand(slides, b)
        cmd.execute()
        cmd.undo()
        self.assertEqual([s.name for s in slides], ["a", "b", "c"])


class TestReorderSlideCommand(unittest.TestCase):
    def test_execute_swaps_positions(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = ReorderSlideCommand(slides, 0, 2)
        cmd.execute()
        self.assertEqual([s.name for s in slides], ["c", "b", "a"])

    def test_undo_swaps_back(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = ReorderSlideCommand(slides, 0, 2)
        cmd.execute()
        cmd.undo()
        self.assertEqual([s.name for s in slides], ["a", "b", "c"])
```

Actualizar el import al inicio del archivo (línea 5-8) para incluir las clases nuevas:

```python
from dcpub.commands import (
    CommandStack, PropertyChangeCommand, AddLayerCommand, DeleteLayerCommand,
    ReorderLayerCommand, CompositeCommand,
    AddSlideCommand, DeleteSlideCommand, ReorderSlideCommand,
)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_commands -v`
Expected: `ImportError: cannot import name 'AddSlideCommand'` (las clases todavía no existen)

- [ ] **Step 3: Implementar las clases**

En `dcpub/commands.py`, insertar después de `ReorderLayerCommand` (después de la línea 73, antes de `class CompositeCommand:`):

```python
class AddSlideCommand:
    """Inserta `slide` en `slides_list` en la posición `index`."""

    def __init__(self, slides_list, slide, index):
        self.slides_list = slides_list
        self.slide = slide
        self.index = index

    def execute(self):
        self.slides_list.insert(self.index, self.slide)

    def undo(self):
        self.slides_list.remove(self.slide)


class DeleteSlideCommand:
    """Quita `slide` de `slides_list`, recordando su índice original para
    poder reinsertarlo en el mismo lugar al deshacer."""

    def __init__(self, slides_list, slide):
        self.slides_list = slides_list
        self.slide = slide
        self.index = None

    def execute(self):
        self.index = self.slides_list.index(self.slide)
        self.slides_list.remove(self.slide)

    def undo(self):
        self.slides_list.insert(self.index, self.slide)


class ReorderSlideCommand:
    """Intercambia la posición de dos láminas en `slides_list`. El intercambio
    es su propia operación inversa, así que undo() reusa execute()."""

    def __init__(self, slides_list, index_a, index_b):
        self.slides_list = slides_list
        self.index_a = index_a
        self.index_b = index_b

    def execute(self):
        self.slides_list[self.index_a], self.slides_list[self.index_b] = (
            self.slides_list[self.index_b], self.slides_list[self.index_a])

    def undo(self):
        self.execute()
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_commands -v`
Expected: `OK` (todos los tests, incluidos los nuevos)

- [ ] **Step 5: Commit**

```bash
git add dcpub/commands.py tests/test_commands.py
git commit -m "Agregar comandos de lista de laminas (add/delete/reorder)"
```

---

### Task 2: Duplicar lámina y copiar estilo (`models.py`)

**Files:**
- Modify: `dcpub/models.py` (imports línea 3-4, agregar funciones después de `crear_proyecto_por_defecto`, línea 197)
- Test: `tests/test_models_slide_ops.py` (nuevo)

**Interfaces:**
- Consumes: `Slide`, `Layer`, `_short_id()` (ya existen en `models.py`)
- Produces: `duplicar_slide(slide: Slide) -> Slide`, `plan_copia_estilo(origen: Slide, destino: Slide) -> list[tuple[Layer, str, object]]`, constante `LAYER_STYLE_FIELDS: dict`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_models_slide_ops.py`:

```python
"""Tests de duplicar_slide y plan_copia_estilo (dcpub.models)."""

import unittest

from dcpub.models import crear_slide_por_defecto, duplicar_slide, plan_copia_estilo


class TestDuplicarSlide(unittest.TestCase):
    def setUp(self):
        self.original = crear_slide_por_defecto(
            photo_path="foto.jpg", titulo="Titulo", subtitulo="Sub", descripcion="Desc")

    def test_duplicado_tiene_mismo_contenido(self):
        copia = duplicar_slide(self.original)
        self.assertEqual(
            [(l.type, l.text if hasattr(l, "text") else l.src) for l in copia.layers],
            [(l.type, l.text if hasattr(l, "text") else l.src) for l in self.original.layers],
        )

    def test_duplicado_tiene_ids_de_capa_nuevos(self):
        copia = duplicar_slide(self.original)
        ids_originales = {l.id for l in self.original.layers}
        ids_copia = {l.id for l in copia.layers}
        self.assertTrue(ids_originales.isdisjoint(ids_copia))

    def test_duplicado_es_independiente_del_original(self):
        copia = duplicar_slide(self.original)
        copia.layers[2].text = "Cambiado en la copia"
        self.assertNotEqual(self.original.layers[2].text, "Cambiado en la copia")

    def test_duplicado_de_photo_layer_no_comparte_dict_adjust(self):
        copia = duplicar_slide(self.original)
        foto_copia = copia.layers[0]
        foto_original = self.original.layers[0]
        foto_copia.adjust["brightness"] = 1.5
        self.assertEqual(foto_original.adjust["brightness"], 1.0)

    def test_duplicado_conserva_formato(self):
        formato = {"name": "custom", "w": 800, "h": 1000}
        original = crear_slide_por_defecto(formato=formato)
        copia = duplicar_slide(original)
        self.assertEqual(copia.format, formato)
        self.assertIsNot(copia.format, original.format)


class TestPlanCopiaEstilo(unittest.TestCase):
    def setUp(self):
        self.origen = crear_slide_por_defecto(
            photo_path="origen.jpg", titulo="Titulo origen", subtitulo="Sub origen")
        self.origen.layers[2].x = 0.9  # Título: posición distinta a la del destino
        self.origen.layers[2].size = 0.2
        self.destino = crear_slide_por_defecto(
            photo_path="destino.jpg", titulo="Titulo destino", subtitulo="Sub destino")

    def test_copia_posicion_y_tamano_de_titulo(self):
        cambios = plan_copia_estilo(self.origen, self.destino)
        titulo_destino = self.destino.layers[2]
        cambios_titulo = {(l.id, attr): val for l, attr, val in cambios if l is titulo_destino}
        self.assertEqual(cambios_titulo[(titulo_destino.id, "x")], 0.9)
        self.assertEqual(cambios_titulo[(titulo_destino.id, "size")], 0.2)

    def test_no_toca_el_texto_del_destino(self):
        cambios = plan_copia_estilo(self.origen, self.destino)
        atributos_tocados = {attr for _, attr, _ in cambios}
        self.assertNotIn("text", atributos_tocados)
        self.assertNotIn("src", atributos_tocados)

    def test_sin_diferencias_no_genera_cambios(self):
        cambios = plan_copia_estilo(self.origen, self.origen)
        self.assertEqual(cambios, [])

    def test_copia_ajustes_de_foto_como_dict_independiente(self):
        self.origen.layers[0].adjust["brightness"] = 1.8
        cambios = plan_copia_estilo(self.origen, self.destino)
        foto_destino = self.destino.layers[0]
        cambio_adjust = next(val for l, attr, val in cambios if l is foto_destino and attr == "adjust")
        self.assertEqual(cambio_adjust["brightness"], 1.8)
        self.assertIsNot(cambio_adjust, self.origen.layers[0].adjust)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_models_slide_ops -v`
Expected: `ImportError: cannot import name 'duplicar_slide'`

- [ ] **Step 3: Implementar**

En `dcpub/models.py`, cambiar la línea 3 (agregar `import copy`):

```python
import copy
from dataclasses import dataclass, field, asdict
import uuid
```

Agregar al final del archivo, después de `crear_proyecto_por_defecto` (línea 197):

```python
def duplicar_slide(slide: Slide) -> Slide:
    """Copia profunda de una lámina (formato y capas incluidos), con ids de
    capa nuevos e independientes del original."""
    copia = copy.deepcopy(slide)
    for layer in copia.layers:
        layer.id = _short_id()
    return copia


LAYER_STYLE_FIELDS = {
    ("photo", None): ("x", "y", "w", "h", "rotation", "opacity",
                       "fit", "zoom", "offset_x", "offset_y", "adjust", "overlay"),
    ("logo", None): ("x", "y", "w", "h", "rotation", "opacity", "keep_ratio"),
    ("text", "title"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("text", "subtitle"): ("x", "y", "w", "h", "rotation", "opacity", "size"),
    ("box", None): ("x", "y", "w", "h", "rotation", "opacity", "size", "icon"),
}


def _estilo_key(layer: Layer):
    role = getattr(layer, "role", None) if layer.type == "text" else None
    return (layer.type, role)


def plan_copia_estilo(origen: Slide, destino: Slide) -> list:
    """Compara las capas de `origen` y `destino` por tipo/rol y devuelve la
    lista de cambios de estilo a aplicar en `destino`: tuplas
    (capa_destino, atributo, valor_nuevo). Preserva el contenido (texto/src)
    de `destino` — solo se incluyen los campos listados en
    LAYER_STYLE_FIELDS. Capas de `destino` sin equivalente por tipo/rol en
    `origen` no generan cambios."""
    origen_por_clave = {_estilo_key(layer): layer for layer in origen.layers}

    cambios = []
    for layer_destino in destino.layers:
        clave = _estilo_key(layer_destino)
        layer_origen = origen_por_clave.get(clave)
        if layer_origen is None:
            continue
        campos = LAYER_STYLE_FIELDS.get(clave)
        if campos is None:
            continue
        for campo in campos:
            valor_nuevo = getattr(layer_origen, campo)
            if isinstance(valor_nuevo, dict):
                valor_nuevo = dict(valor_nuevo)
            if getattr(layer_destino, campo) != valor_nuevo:
                cambios.append((layer_destino, campo, valor_nuevo))
    return cambios
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_models_slide_ops -v`
Expected: `OK`

- [ ] **Step 5: Correr toda la suite (por si el import de `copy` u otro cambio afecta algo más)**

Run: `python -m unittest discover -s tests -v`
Expected: `OK`, todos los tests

- [ ] **Step 6: Commit**

```bash
git add dcpub/models.py tests/test_models_slide_ops.py
git commit -m "Agregar duplicar_slide y plan_copia_estilo a models.py"
```

---

### Task 3: Estado de lámina activa en `App` (`app.py`)

**Files:**
- Modify: `dcpub/app.py` (líneas 96-98, 785-792, 1270-1305)
- Test: `tests/test_app_slides.py` (nuevo)

**Interfaces:**
- Consumes: `Task 2` no es necesario para esta tarea; usa solo lo que ya existe en `App`.
- Produces: `App.current_slide_index: int`, `App.switch_to_slide(index: int) -> None`, `App._sync_widgets_from_slide() -> None` — usados por las Tareas 4 y 6.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/test_app_slides.py`:

```python
"""Tests de estado de lámina activa en dcpub.app.App (sin abrir Tk)."""

import unittest

from dcpub.app import App
from dcpub.models import crear_proyecto_por_defecto


class _FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _FakeText:
    def __init__(self, value=""):
        self.value = value

    def get(self, start, end=None):
        return self.value

    def delete(self, start, end):
        self.value = ""

    def insert(self, index, text):
        self.value += text


def _make_app_with_two_slides():
    app = App.__new__(App)
    app.project = crear_proyecto_por_defecto("foto1.jpg")
    app.project.slides[0].layers[2].text = "Titulo lamina 1"
    segunda = crear_proyecto_por_defecto("foto2.jpg").slides[0]
    segunda.layers[2].text = "Titulo lamina 2"
    app.project.slides.append(segunda)
    app.slide = app.project.slides[0]
    app.current_slide_index = 0
    app._selected = None
    app.v_photo = _FakeVar("")
    app.v_logo = _FakeVar("")
    app.txt_title = _FakeText("")
    app.v_sub = _FakeVar("")
    app.txt_desc = _FakeText("")
    app.v_icon = _FakeVar("planta")
    app.v_format = _FakeVar("")
    return app


class TestSyncWidgetsFromSlide(unittest.TestCase):
    def test_sync_reflects_second_slide_content(self):
        app = _make_app_with_two_slides()
        app.slide = app.project.slides[1]

        App._sync_widgets_from_slide(app)

        self.assertEqual(app.v_photo.value, "foto2.jpg")
        self.assertEqual(app.txt_title.value, "Titulo lamina 2")


class TestSwitchToSlide(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        self.calls = []
        self.app._build_property_panel = lambda: self.calls.append("props")
        self.app._refresh_layers_list = lambda: self.calls.append("layers")
        self.app._schedule_render = lambda: self.calls.append("render")

    def test_switch_updates_index_and_slide(self):
        App.switch_to_slide(self.app, 1)
        self.assertEqual(self.app.current_slide_index, 1)
        self.assertIs(self.app.slide, self.app.project.slides[1])

    def test_switch_syncs_widgets(self):
        App.switch_to_slide(self.app, 1)
        self.assertEqual(self.app.v_photo.value, "foto2.jpg")

    def test_switch_clears_selection_and_refreshes_ui(self):
        self.app._selected = self.app.project.slides[0].layers[0]
        App.switch_to_slide(self.app, 1)
        self.assertIsNone(self.app._selected)
        self.assertEqual(self.calls, ["props", "layers", "render"])

    def test_switch_ignores_out_of_range_index(self):
        App.switch_to_slide(self.app, 5)
        self.assertEqual(self.app.current_slide_index, 0)
        self.assertIs(self.app.slide, self.app.project.slides[0])
        self.assertEqual(self.calls, [])

    def test_switch_ignores_negative_index(self):
        App.switch_to_slide(self.app, -1)
        self.assertEqual(self.app.current_slide_index, 0)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides -v`
Expected: `AttributeError: type object 'App' has no attribute '_sync_widgets_from_slide'`

- [ ] **Step 3: Extraer `_sync_widgets_from_slide` y agregar `switch_to_slide`**

En `dcpub/app.py`, reemplazar el bloque de sincronización dentro de `_open_project` (líneas 1286-1299):

```python
        photo_layer = self._layer_by_kind("photo")
        self.v_photo.set(photo_layer.src if photo_layer else "")
        logo_layer = self._layer_by_kind("logo")
        self.v_logo.set(logo_layer.src if logo_layer and logo_layer.src else str(LOGO_FILE))
        title_layer = self._layer_by_kind("title")
        self.txt_title.delete("1.0", tk.END)
        self.txt_title.insert("1.0", title_layer.text if title_layer else "")
        sub_layer = self._layer_by_kind("sub")
        self.v_sub.set(sub_layer.text if sub_layer else "")
        desc_layer = self._layer_by_kind("desc")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", desc_layer.text if desc_layer else "")
        self.v_icon.set(desc_layer.icon if desc_layer else "planta")
        self.v_format.set(self._format_label_for(self.slide.format))
```

por:

```python
        self._sync_widgets_from_slide()
```

Agregar el nuevo método `_sync_widgets_from_slide` y `switch_to_slide` justo antes de `_reset` (antes de la línea `def _reset(self):`, línea 785):

```python
    def _sync_widgets_from_slide(self):
        """Refleja el contenido de self.slide en los widgets de texto/foto/logo
        del panel izquierdo. Mismo bloque que usaba _open_project, ahora
        reutilizable también al cambiar de lámina activa."""
        photo_layer = self._layer_by_kind("photo")
        self.v_photo.set(photo_layer.src if photo_layer else "")
        logo_layer = self._layer_by_kind("logo")
        self.v_logo.set(logo_layer.src if logo_layer and logo_layer.src else str(LOGO_FILE))
        title_layer = self._layer_by_kind("title")
        self.txt_title.delete("1.0", tk.END)
        self.txt_title.insert("1.0", title_layer.text if title_layer else "")
        sub_layer = self._layer_by_kind("sub")
        self.v_sub.set(sub_layer.text if sub_layer else "")
        desc_layer = self._layer_by_kind("desc")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", desc_layer.text if desc_layer else "")
        self.v_icon.set(desc_layer.icon if desc_layer else "planta")
        self.v_format.set(self._format_label_for(self.slide.format))

    def switch_to_slide(self, index):
        """Cambia la lámina activa a project.slides[index] y refresca toda la
        UI dependiente (widgets de texto, panel de propiedades, panel de
        capas, vista previa). No hace nada si el índice está fuera de rango."""
        if index < 0 or index >= len(self.project.slides):
            return
        self.current_slide_index = index
        self.slide = self.project.slides[index]
        self._selected = None
        self._sync_widgets_from_slide()
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides -v`
Expected: `OK`

- [ ] **Step 5: Refactorizar los 3 puntos hardcodeados**

En `dcpub/app.py`, línea 98, dentro de `__init__`, después de `self.slide = self.project.slides[0]`, agregar:

```python
        self.current_slide_index = 0
```

En `_reset` (línea ~786-787), reemplazar:

```python
        self.project = crear_proyecto_por_defecto(self.v_photo.get().strip())
        self.slide = self.project.slides[0]
```

por:

```python
        self.project = crear_proyecto_por_defecto(self.v_photo.get().strip())
        self.slide = self.project.slides[0]
        self.current_slide_index = 0
```

En `_open_project`, reemplazar:

```python
        loaded = load_project(Path(path_str))
        self.project = loaded
        self.slide = self.project.slides[0]
        self._project_path = Path(path_str)
```

por:

```python
        loaded = load_project(Path(path_str))
        self.project = loaded
        self.slide = self.project.slides[0]
        self.current_slide_index = 0
        self._project_path = Path(path_str)
```

- [ ] **Step 6: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: `OK`, todos los tests (incluidos los existentes de save/load y layer tokens, que no deben romperse)

- [ ] **Step 7: Commit**

```bash
git add dcpub/app.py tests/test_app_slides.py
git commit -m "Agregar estado de lamina activa (current_slide_index, switch_to_slide)"
```

---

### Task 4: Acciones de lámina en `App` (`app.py`)

**Files:**
- Modify: `dcpub/app.py` (agregar métodos después de `switch_to_slide`, de la Tarea 3)
- Test: `tests/test_app_slides.py` (agregar clases nuevas)

**Interfaces:**
- Consumes: `Task 1` (`AddSlideCommand`, `DeleteSlideCommand`, `ReorderSlideCommand`), `Task 2` (`duplicar_slide`, `plan_copia_estilo`), `Task 3` (`switch_to_slide`)
- Produces: `App._add_slide()`, `App._duplicate_slide()`, `App._delete_slide()`, `App._move_slide(direction: int)`, `App._copy_style_to_slide(origen_slide, destino_index: int)` — usados por `dcpub/slides_panel.py` en la Tarea 6.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_slides.py`, antes de `if __name__ == "__main__":`:

```python
class TestAddSlide(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._schedule_render = lambda: None

    def test_inserts_after_current_slide(self):
        App._add_slide(self.app)
        self.assertEqual(len(self.app.project.slides), 3)
        self.assertIs(self.app.project.slides[1], self.app.slide)

    def test_new_slide_uses_current_format(self):
        self.app.slide.format = {"name": "custom", "w": 800, "h": 1000}
        App._add_slide(self.app)
        self.assertEqual(self.app.slide.format, {"name": "custom", "w": 800, "h": 1000})

    def test_undo_removes_the_added_slide(self):
        App._add_slide(self.app)
        self.app.commands.undo()
        self.assertEqual(len(self.app.project.slides), 2)


class TestDuplicateSlide(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._schedule_render = lambda: None

    def test_duplicate_inserts_copy_after_current(self):
        App._duplicate_slide(self.app)
        self.assertEqual(len(self.app.project.slides), 3)
        self.assertEqual(self.app.project.slides[1].layers[2].text, "Titulo lamina 1")
        self.assertIsNot(self.app.project.slides[1], self.app.project.slides[0])


class TestDeleteSlide(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._schedule_render = lambda: None
        self.app.v_status = _FakeVar("")

    def test_deletes_current_slide(self):
        App._delete_slide(self.app)
        self.assertEqual(len(self.app.project.slides), 1)
        self.assertEqual(self.app.project.slides[0].layers[2].text, "Titulo lamina 2")

    def test_refuses_to_delete_last_slide(self):
        App._delete_slide(self.app)  # queda 1 lamina
        App._delete_slide(self.app)  # no deberia borrar la ultima
        self.assertEqual(len(self.app.project.slides), 1)


class TestMoveSlide(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._schedule_render = lambda: None

    def test_move_down_swaps_with_next(self):
        primero = self.app.project.slides[0]
        App._move_slide(self.app, 1)
        self.assertIs(self.app.project.slides[1], primero)
        self.assertEqual(self.app.current_slide_index, 1)

    def test_move_up_from_first_is_noop(self):
        App._move_slide(self.app, -1)
        self.assertEqual(self.app.current_slide_index, 0)


class TestCopyStyleToSlide(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._render_now = lambda: None

    def test_copies_style_without_touching_text(self):
        origen = self.app.project.slides[0]
        origen.layers[2].x = 0.9
        App._copy_style_to_slide(self.app, origen, 1)
        destino = self.app.project.slides[1]
        self.assertEqual(destino.layers[2].x, 0.9)
        self.assertEqual(destino.layers[2].text, "Titulo lamina 2")

    def test_undo_reverts_the_copy(self):
        origen = self.app.project.slides[0]
        origen.layers[2].x = 0.9
        destino = self.app.project.slides[1]
        x_original = destino.layers[2].x
        App._copy_style_to_slide(self.app, origen, 1)
        self.app.commands.undo()
        self.assertEqual(destino.layers[2].x, x_original)

```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides -v`
Expected: `AttributeError: type object 'App' has no attribute '_add_slide'`

- [ ] **Step 3: Implementar los métodos de acción**

En `dcpub/app.py`, agregar después de `switch_to_slide` (Tarea 3):

```python
    def _add_slide(self):
        """Inserta una lámina en blanco (layout default) justo después de la
        lámina activa, con el mismo formato que la lámina activa."""
        from .models import crear_slide_por_defecto
        from .commands import AddSlideCommand
        nueva = crear_slide_por_defecto(formato=dict(self.slide.format))
        index = self.current_slide_index + 1
        self.commands.push(AddSlideCommand(self.project.slides, nueva, index))
        self.switch_to_slide(index)

    def _duplicate_slide(self):
        """Inserta una copia completa (texto incluido) de la lámina activa
        justo después de ella."""
        from .models import duplicar_slide
        from .commands import AddSlideCommand
        copia = duplicar_slide(self.slide)
        index = self.current_slide_index + 1
        self.commands.push(AddSlideCommand(self.project.slides, copia, index))
        self.switch_to_slide(index)

    def _delete_slide(self):
        """Elimina la lámina activa, salvo que sea la última del proyecto."""
        if len(self.project.slides) <= 1:
            self.v_status.set("No se puede eliminar la última lámina.")
            return
        from .commands import DeleteSlideCommand
        slide_a_borrar = self.slide
        nuevo_index = min(self.current_slide_index, len(self.project.slides) - 2)
        self.commands.push(DeleteSlideCommand(self.project.slides, slide_a_borrar))
        self.switch_to_slide(nuevo_index)

    def _move_slide(self, direction):
        """Intercambia la lámina activa con la adyacente (direction=-1 sube,
        +1 baja). No hace nada si ya está en el extremo."""
        idx = self.current_slide_index
        otro = idx + direction
        if otro < 0 or otro >= len(self.project.slides):
            return
        from .commands import ReorderSlideCommand
        self.commands.push(ReorderSlideCommand(self.project.slides, idx, otro))
        self.switch_to_slide(otro)

    def _copy_style_to_slide(self, origen_slide, destino_index):
        """Copia posición/tamaño/estilo de las capas de `origen_slide` hacia
        la lámina en `destino_index`, preservando el texto/contenido que esa
        lámina ya tenía."""
        if destino_index < 0 or destino_index >= len(self.project.slides):
            return
        from .models import plan_copia_estilo
        from .commands import PropertyChangeCommand, CompositeCommand
        destino = self.project.slides[destino_index]
        cambios = plan_copia_estilo(origen_slide, destino)
        if not cambios:
            return
        comandos = [PropertyChangeCommand(layer, attr, getattr(layer, attr), nuevo)
                    for layer, attr, nuevo in cambios]
        self.commands.push(CompositeCommand(comandos))
        if destino_index == self.current_slide_index:
            self._render_now()

```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides -v`
Expected: `OK`

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: `OK`, todos los tests

- [ ] **Step 6: Commit**

```bash
git add dcpub/app.py tests/test_app_slides.py
git commit -m "Agregar acciones de lamina: agregar, duplicar, eliminar, mover, copiar estilo"
```

---

### Task 5: Generalizar acceso a capas por lámina + logo compartido (`app.py`)

**Files:**
- Modify: `dcpub/app.py` (`_layer_by_kind` línea 674, `_canvas_size_for` línea 1017, `_build_layers` línea 1055, `_build_left` línea 198, `_browse_logo` línea 1041, `_on_logo_direct_edit` línea 803)
- Test: `tests/test_app_slides.py` (agregar clases nuevas)

**Interfaces:**
- Consumes: `Project.shared` (ya existe en `models.py`)
- Produces: `App._layer_by_kind(kind, slide=None)`, `App._canvas_size_for(max_side, fmt=None)`, `App._build_layers_for(slide)`, `App._toggle_shared_logo()`, `App._sync_shared_logo_if_active()` — `_build_layers_for` lo usa `dcpub/slides_panel.py` en la Tarea 6 para renderizar miniaturas de láminas que no son la activa.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/test_app_slides.py`, antes de `if __name__ == "__main__":`:

```python
class TestLayerByKindWithSlideParam(unittest.TestCase):
    def test_defaults_to_self_slide(self):
        app = _make_app_with_two_slides()
        titulo = App._layer_by_kind(app, "title")
        self.assertEqual(titulo.text, "Titulo lamina 1")

    def test_accepts_explicit_slide(self):
        app = _make_app_with_two_slides()
        segunda = app.project.slides[1]
        titulo = App._layer_by_kind(app, "title", segunda)
        self.assertEqual(titulo.text, "Titulo lamina 2")


class TestCanvasSizeForWithFmt(unittest.TestCase):
    def test_defaults_to_self_slide_format(self):
        app = _make_app_with_two_slides()
        app.slide.format = {"name": "x", "w": 1080, "h": 1350}
        w, h = App._canvas_size_for(app, 400)
        self.assertEqual(h, 400)
        self.assertEqual(w, round(400 * 1080 / 1350))

    def test_accepts_explicit_format(self):
        app = _make_app_with_two_slides()
        w, h = App._canvas_size_for(app, 400, {"name": "x", "w": 1000, "h": 1000})
        self.assertEqual((w, h), (400, 400))


class TestBuildLayersFor(unittest.TestCase):
    def test_other_slide_uses_its_own_layer_text_not_live_widgets(self):
        app = _make_app_with_two_slides()
        app.v_photo = _FakeVar("foto-editada-en-pantalla.jpg")
        app.v_logo = _FakeVar("")
        app.txt_title = _FakeText("Texto tipeado ahora mismo")
        app.v_sub = _FakeVar("")
        app.txt_desc = _FakeText("")
        app.v_icon = _FakeVar("planta")

        segunda = app.project.slides[1]
        capas = App._build_layers_for(app, segunda)
        titulo = next(c for c in capas if c["type"] == "title")
        self.assertEqual(titulo["text"], "Titulo lamina 2")

    def test_current_slide_still_uses_live_widgets(self):
        app = _make_app_with_two_slides()
        app.v_photo = _FakeVar("")
        app.v_logo = _FakeVar("")
        app.txt_title = _FakeText("Texto tipeado ahora mismo")
        app.v_sub = _FakeVar("")
        app.txt_desc = _FakeText("")
        app.v_icon = _FakeVar("planta")

        capas = App._build_layers_for(app, app.slide)
        titulo = next(c for c in capas if c["type"] == "title")
        self.assertEqual(titulo["text"], "Texto tipeado ahora mismo")

    def test_build_layers_delegates_to_build_layers_for_current_slide(self):
        app = _make_app_with_two_slides()
        app.v_photo = _FakeVar("")
        app.v_logo = _FakeVar("")
        app.txt_title = _FakeText("Via _build_layers")
        app.v_sub = _FakeVar("")
        app.txt_desc = _FakeText("")
        app.v_icon = _FakeVar("planta")

        capas = App._build_layers(app)
        titulo = next(c for c in capas if c["type"] == "title")
        self.assertEqual(titulo["text"], "Via _build_layers")


class TestSharedLogo(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        self.app.v_photo = _FakeVar("")
        self.app.v_logo = _FakeVar("")
        self.app.txt_title = _FakeText("")
        self.app.v_sub = _FakeVar("")
        self.app.txt_desc = _FakeText("")
        self.app.v_icon = _FakeVar("planta")
        self.app.v_logo_shared = _FakeVar(False)
        self.app._set_dirty = lambda value: None
        self.app._schedule_render = lambda: None

    def test_toggle_on_writes_shared_logo_from_current_slide(self):
        self.app.v_logo_shared.set(True)
        App._toggle_shared_logo(self.app)
        self.assertIn("logo", self.app.project.shared)
        logo_layer = App._layer_by_kind(self.app, "logo")
        self.assertEqual(self.app.project.shared["logo"]["src"], logo_layer.src)

    def test_toggle_off_clears_shared_logo(self):
        self.app.v_logo_shared.set(True)
        App._toggle_shared_logo(self.app)
        self.app.v_logo_shared.set(False)
        App._toggle_shared_logo(self.app)
        self.assertNotIn("logo", self.app.project.shared)

    def test_build_layers_uses_shared_logo_for_any_slide(self):
        self.app.v_logo_shared.set(True)
        App._toggle_shared_logo(self.app)
        self.app.project.shared["logo"]["src"] = "logo-compartido.png"

        segunda = self.app.project.slides[1]
        capas = App._build_layers_for(self.app, segunda)
        logo = next(c for c in capas if c["type"] == "logo")
        self.assertEqual(logo["src"], "logo-compartido.png")

    def test_build_layers_uses_own_logo_when_not_shared(self):
        segunda = self.app.project.slides[1]
        logo_propio = App._layer_by_kind(self.app, "logo", segunda)
        capas = App._build_layers_for(self.app, segunda)
        logo = next(c for c in capas if c["type"] == "logo")
        self.assertEqual(logo["src"], logo_propio.src)

```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `python -m unittest tests.test_app_slides -v`
Expected: `TypeError: _layer_by_kind() takes 2 positional arguments but 3 were given`

- [ ] **Step 3: Generalizar `_layer_by_kind`**

En `dcpub/app.py`, reemplazar (línea 674-688):

```python
    def _layer_by_kind(self, kind):
        """Traduce entre el vocabulario del render ("photo"/"logo"/"title"/"sub"/"desc")
        y los tipos/roles reales de dcpub.models (Layer.type, TextLayer.role)."""
        for layer in self.slide.layers:
            if kind == "photo" and layer.type == "photo":
                return layer
            if kind == "logo" and layer.type == "logo":
                return layer
            if kind == "title" and layer.type == "text" and layer.role == "title":
                return layer
            if kind == "sub" and layer.type == "text" and layer.role == "subtitle":
                return layer
            if kind == "desc" and layer.type == "box":
                return layer
        return None
```

por:

```python
    def _layer_by_kind(self, kind, slide=None):
        """Traduce entre el vocabulario del render ("photo"/"logo"/"title"/"sub"/"desc")
        y los tipos/roles reales de dcpub.models (Layer.type, TextLayer.role).
        Busca en `slide` si se pasa, o en la lámina activa (self.slide) si no."""
        target = slide if slide is not None else self.slide
        for layer in target.layers:
            if kind == "photo" and layer.type == "photo":
                return layer
            if kind == "logo" and layer.type == "logo":
                return layer
            if kind == "title" and layer.type == "text" and layer.role == "title":
                return layer
            if kind == "sub" and layer.type == "text" and layer.role == "subtitle":
                return layer
            if kind == "desc" and layer.type == "box":
                return layer
        return None
```

- [ ] **Step 4: Generalizar `_canvas_size_for`**

Reemplazar (línea 1017-1027):

```python
    def _canvas_size_for(self, max_side):
        """Calcula (ancho, alto) en px del lienzo para el formato actual, con el
        lado mayor igual a max_side, manteniendo la proporción del formato."""
        fw, fh = self.slide.format["w"], self.slide.format["h"]
        if fh >= fw:
            h = max_side
            w = max(1, round(max_side * fw / fh))
        else:
            w = max_side
            h = max(1, round(max_side * fh / fw))
        return (w, h)
```

por:

```python
    def _canvas_size_for(self, max_side, fmt=None):
        """Calcula (ancho, alto) en px del lienzo para `fmt` (o el formato de
        la lámina activa si no se pasa), con el lado mayor igual a max_side,
        manteniendo la proporción del formato."""
        formato = fmt if fmt is not None else self.slide.format
        fw, fh = formato["w"], formato["h"]
        if fh >= fw:
            h = max_side
            w = max(1, round(max_side * fw / fh))
        else:
            w = max_side
            h = max(1, round(max_side * fh / fw))
        return (w, h)
```

- [ ] **Step 5: Generalizar `_build_layers` a `_build_layers_for` + resolver logo compartido**

Reemplazar el método completo (línea 1055-1089):

```python
    def _build_layers(self):
        layers = []
        for layer in self.slide.layers:
            if not layer.visible:
                continue
            if layer.type == "photo":
                src = self.v_photo.get().strip() if layer is self._layer_by_kind("photo") else layer.src
                layers.append({"type": "photo", "key": layer.id, "src": src,
                                "zoom": layer.zoom, "offset_x": layer.offset_x,
                                "offset_y": layer.offset_y, "opacity": layer.opacity})
            elif layer.type == "logo":
                src = self.v_logo.get().strip() if layer is self._layer_by_kind("logo") else layer.src
                layers.append({"type": "logo", "key": layer.id,
                                "src": src,
                                "x": layer.x, "y": layer.y, "size": layer.w,
                                "opacity": layer.opacity})
            elif layer.type == "text" and layer.role == "title":
                text = (self.txt_title.get("1.0", "end-1c")
                        if layer is self._layer_by_kind("title") else layer.text)
                layers.append({"type": "title", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity})
            elif layer.type == "text" and layer.role == "subtitle":
                text = self.v_sub.get() if layer is self._layer_by_kind("sub") else layer.text
                layers.append({"type": "sub", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity})
            elif layer.type == "box":
                text = (self.txt_desc.get("1.0", "end-1c")
                        if layer is self._layer_by_kind("desc") else layer.text)
                icon = self.v_icon.get() if layer is self._layer_by_kind("desc") else layer.icon
                layers.append({"type": "desc", "key": layer.id, "text": text,
                                "icon": icon, "x": layer.x, "y": layer.y,
                                "size": layer.size, "opacity": layer.opacity})
        return layers
```

por:

```python
    def _build_layers_for(self, slide):
        """Adapta las capas de `slide` al dict plano que espera render.compose().
        Si `slide` es la lámina activa (self.slide), las capas de foto/logo/
        título/subtítulo/descripción reflejan los widgets en pantalla en vez
        del valor guardado en el modelo (para que la vista previa muestre lo
        que se está tipeando antes de sincronizarlo con _sync_text_to_layers).
        Si el proyecto tiene un logo compartido activo (project.shared["logo"]),
        ese valor pisa el logo propio de la lámina, sea cual sea."""
        es_activa = slide is self.slide
        shared_logo = self.project.shared.get("logo")
        layers = []
        for layer in slide.layers:
            if not layer.visible:
                continue
            if layer.type == "photo":
                src = (self.v_photo.get().strip()
                       if es_activa and layer is self._layer_by_kind("photo", slide) else layer.src)
                layers.append({"type": "photo", "key": layer.id, "src": src,
                                "zoom": layer.zoom, "offset_x": layer.offset_x,
                                "offset_y": layer.offset_y, "opacity": layer.opacity})
            elif layer.type == "logo":
                if shared_logo is not None:
                    layers.append({"type": "logo", "key": layer.id,
                                    "src": shared_logo["src"],
                                    "x": shared_logo["x"], "y": shared_logo["y"],
                                    "size": shared_logo["w"], "opacity": layer.opacity})
                else:
                    src = (self.v_logo.get().strip()
                           if es_activa and layer is self._layer_by_kind("logo", slide) else layer.src)
                    layers.append({"type": "logo", "key": layer.id, "src": src,
                                    "x": layer.x, "y": layer.y, "size": layer.w,
                                    "opacity": layer.opacity})
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
            elif layer.type == "box":
                es_desc_activa = es_activa and layer is self._layer_by_kind("desc", slide)
                text = self.txt_desc.get("1.0", "end-1c") if es_desc_activa else layer.text
                icon = self.v_icon.get() if es_desc_activa else layer.icon
                layers.append({"type": "desc", "key": layer.id, "text": text,
                                "icon": icon, "x": layer.x, "y": layer.y,
                                "size": layer.size, "opacity": layer.opacity})
        return layers

    def _build_layers(self):
        return self._build_layers_for(self.slide)
```

- [ ] **Step 6: Agregar el checkbox y el método `_toggle_shared_logo`**

En `dcpub/app.py`, dentro de `_build_left`, en la sección "Logo" (línea 230-241), agregar el checkbox después del botón de examinar:

```python
        # Logo
        tk.Label(left, text="Logo", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        row_logo = tk.Frame(left, bg=PANEL)
        row_logo.pack(fill=tk.X, pady=(0, 4), **pad)
        e_logo = tk.Entry(row_logo, textvariable=self.v_logo, bg=FIELD, fg=TEXT,
                          insertbackground="white", relief="flat", bd=4,
                          font=("Segoe UI", 9))
        e_logo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e_logo.bind("<KeyRelease>", lambda e: self._on_logo_direct_edit())
        tk.Button(row_logo, text="…", bg="#3d3d3d", fg=TEXT, relief="flat", padx=8,
                  command=self._browse_logo).pack(side=tk.LEFT, padx=(4, 0))

        self.v_logo_shared = tk.BooleanVar(value="logo" in self.project.shared)
        tk.Checkbutton(left, text="Usar en todo el carrusel", variable=self.v_logo_shared,
                        bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                        activeforeground=TEXT, font=("Segoe UI", 8),
                        command=self._toggle_shared_logo).pack(anchor="w", pady=(0, 8), **pad)
```

(Esto reemplaza el bloque "Logo" existente; notar que `pady=(0, 8)` del `row_logo` original bajó a `(0, 4)` para dejar lugar al checkbox debajo.)

Agregar los métodos, después de `_default_logo_src` (línea 809-813):

```python
    def _toggle_shared_logo(self):
        """Escribe o borra project.shared["logo"] según el estado del checkbox
        "Usar en todo el carrusel". Al activar, toma como valor inicial el
        logo de la lámina activa."""
        if self.v_logo_shared.get():
            logo_layer = self._layer_by_kind("logo")
            self.project.shared["logo"] = {
                "src": logo_layer.src, "x": logo_layer.x, "y": logo_layer.y,
                "w": logo_layer.w, "h": logo_layer.h,
            }
        else:
            self.project.shared.pop("logo", None)
        self._set_dirty(True)
        self._schedule_render()

    def _sync_shared_logo_if_active(self):
        """Si el logo compartido está activo, actualiza su valor con el logo
        actual de la lámina activa (para que un cambio de archivo se
        propague a todo el carrusel)."""
        if "logo" in self.project.shared:
            logo_layer = self._layer_by_kind("logo")
            self.project.shared["logo"] = {
                "src": logo_layer.src, "x": logo_layer.x, "y": logo_layer.y,
                "w": logo_layer.w, "h": logo_layer.h,
            }
```

- [ ] **Step 7: Llamar a `_sync_shared_logo_if_active` al cambiar el archivo del logo**

En `_browse_logo` (línea 1041-1052), reemplazar:

```python
    def _browse_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            initialdir=str(SCRIPT_DIR),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")])
        if path:
            self.v_logo.set(path)
            logo_layer = self._layer_by_kind("logo")
            if logo_layer is not None:
                logo_layer.src = path
            self._set_dirty(True)
            self._schedule_render()
```

por:

```python
    def _browse_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            initialdir=str(SCRIPT_DIR),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")])
        if path:
            self.v_logo.set(path)
            logo_layer = self._layer_by_kind("logo")
            if logo_layer is not None:
                logo_layer.src = path
            self._sync_shared_logo_if_active()
            self._set_dirty(True)
            self._schedule_render()
```

En `_on_logo_direct_edit` (línea 803-807), reemplazar:

```python
    def _on_logo_direct_edit(self):
        logo_layer = self._layer_by_kind("logo")
        if logo_layer is not None:
            logo_layer.src = self.v_logo.get().strip()
        self._on_direct_edit()
```

por:

```python
    def _on_logo_direct_edit(self):
        logo_layer = self._layer_by_kind("logo")
        if logo_layer is not None:
            logo_layer.src = self.v_logo.get().strip()
        self._sync_shared_logo_if_active()
        self._on_direct_edit()
```

**Nota de alcance:** mover o redimensionar el logo con drag/slider mientras el logo compartido está activo actualiza solo la lámina activa; para propagar esa posición a las demás hay que desactivar y reactivar el checkbox. Es una limitación conocida de este MVP, no un bug — evita acoplar `_toggle_shared_logo` a cada punto de arrastre/slider del logo, que no fue parte del alcance acordado.

- [ ] **Step 8: Correr los tests y verificar que pasan**

Run: `python -m unittest tests.test_app_slides -v`
Expected: `OK`

- [ ] **Step 9: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: `OK`, todos los tests

- [ ] **Step 10: Commit**

```bash
git add dcpub/app.py tests/test_app_slides.py
git commit -m "Generalizar acceso a capas por lamina y agregar logo compartido"
```

---

### Task 6: Panel de miniaturas (`dcpub/slides_panel.py`)

**Files:**
- Create: `dcpub/slides_panel.py`
- Modify: `dcpub/app.py` (`_build_left` línea 198-217, `_render_now` línea 1097-1128)

**Interfaces:**
- Consumes: `App.project`, `App.current_slide_index`, `App.font_manager`, `App.switch_to_slide`, `App._add_slide`, `App._duplicate_slide`, `App._delete_slide`, `App._move_slide`, `App._copy_style_to_slide`, `App._build_layers_for`, `App._canvas_size_for` (Tareas 3-5), `render.compose` (ya existe)
- Produces: `SlidesPanel(parent, app, bg, panel_bg, accent, text_color, muted_color)` con método público `refresh()`

Este módulo es UI pura (widgets de Tkinter): siguiendo la convención ya establecida en el proyecto, los métodos que construyen widgets (`_build_left`, `_build_right` en `app.py`) no tienen tests automatizados — se verifican corriendo la app. La lógica que sí es determinística (las acciones de lámina) ya quedó cubierta por tests en la Tarea 4. Este task se valida ejecutando la app manualmente (Step 4) y, de forma automatizada, con la verificación headless de la Tarea 7.

- [ ] **Step 1: Crear el módulo `dcpub/slides_panel.py`**

```python
"""Panel de miniaturas de láminas del carrusel (panel izquierdo)."""

import tkinter as tk
from tkinter import simpledialog

from PIL import ImageTk

from .render import compose

THUMB_MAX_SIDE = 120


class SlidesPanel(tk.Frame):
    """Lista vertical scrolleable de miniaturas de las láminas del proyecto
    activo, con acciones de agregar/duplicar/eliminar/reordenar/copiar
    estilo. Depende de `app` únicamente a través de su interfaz pública:
    app.project, app.current_slide_index, app.font_manager,
    app.switch_to_slide(index), app._add_slide(), app._duplicate_slide(),
    app._delete_slide(), app._move_slide(direction),
    app._copy_style_to_slide(origen_slide, destino_index),
    app._build_layers_for(slide), app._canvas_size_for(max_side, fmt)."""

    def __init__(self, parent, app, bg, panel_bg, accent, text_color, muted_color):
        super().__init__(parent, bg=panel_bg)
        self.app = app
        self._bg = panel_bg
        self._accent = accent
        self._text = text_color
        self._muted = muted_color
        self._thumb_cache = {}  # id(slide) -> (firma, ImageTk.PhotoImage)
        self._build()

    def _build(self):
        tk.Label(self, text="🎞  Láminas", bg=self._bg, fg=self._text,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 2))

        list_container = tk.Frame(self, bg=self._bg)
        list_container.pack(fill=tk.X)
        scroll_canvas = tk.Canvas(list_container, bg=self._bg, highlightthickness=0, height=260)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=scroll_canvas.yview)
        self._rows_frame = tk.Frame(scroll_canvas, bg=self._bg)
        rows_window = scroll_canvas.create_window((0, 0), window=self._rows_frame, anchor="nw")
        self._rows_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind(
            "<Configure>", lambda e: scroll_canvas.itemconfig(rows_window, width=e.width))
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(self, bg=self._bg)
        actions.pack(fill=tk.X, pady=(4, 4))
        tk.Button(actions, text="+ Agregar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=self.app._add_slide).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(actions, text="⧉ Duplicar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=self.app._duplicate_slide).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(actions, text="🗑 Eliminar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=self.app._delete_slide).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        order_row = tk.Frame(self, bg=self._bg)
        order_row.pack(fill=tk.X, pady=(0, 6))
        tk.Button(order_row, text="▲ Subir", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=lambda: self.app._move_slide(-1)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(order_row, text="▼ Bajar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=lambda: self.app._move_slide(1)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        self.refresh()

    def refresh(self):
        """Reconstruye la lista de miniaturas a partir de app.project.slides."""
        for w in self._rows_frame.winfo_children():
            w.destroy()
        for index, slide in enumerate(self.app.project.slides):
            self._build_row(index, slide)

    def _build_row(self, index, slide):
        is_active = index == self.app.current_slide_index
        row_bg = "#3a4a2f" if is_active else self._bg
        row = tk.Frame(self._rows_frame, bg=row_bg,
                        highlightbackground=self._accent if is_active else row_bg,
                        highlightthickness=2)
        row.pack(fill=tk.X, pady=2, padx=2)

        thumb = self._thumbnail_for(slide)
        label = tk.Label(row, image=thumb, bg=row_bg)
        label.image = thumb  # evita que el GC se lleve la imagen
        label.pack(side=tk.LEFT, padx=4, pady=4)
        label.bind("<Button-1>", lambda e, i=index: self.app.switch_to_slide(i))

        info = tk.Frame(row, bg=row_bg)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(info, text=f"Lámina {index + 1}", bg=row_bg, fg=self._text,
                 font=("Segoe UI", 8)).pack(anchor="w")
        tk.Button(info, text="Copiar estilo →", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 7), command=lambda i=index: self._copy_style_dialog(i)).pack(
            anchor="w")

    def _copy_style_dialog(self, origen_index):
        total = len(self.app.project.slides)
        destino = simpledialog.askinteger(
            "Copiar estilo", f"Lámina destino (1-{total}):",
            minvalue=1, maxvalue=total, parent=self)
        if destino is None:
            return
        origen_slide = self.app.project.slides[origen_index]
        self.app._copy_style_to_slide(origen_slide, destino - 1)
        self.refresh()

    def _thumbnail_for(self, slide):
        firma = slide.to_dict()
        cache_key = id(slide)
        cached = self._thumb_cache.get(cache_key)
        if cached is not None and cached[0] == firma:
            return cached[1]
        canvas_size = self.app._canvas_size_for(THUMB_MAX_SIDE, slide.format)
        img, _ = compose(self.app._build_layers_for(slide), canvas_size, self.app.font_manager)
        imgtk = ImageTk.PhotoImage(img.convert("RGB"))
        self._thumb_cache[cache_key] = (firma, imgtk)
        return imgtk
```

- [ ] **Step 2: Instanciar `SlidesPanel` dentro de `_build_left`**

En `dcpub/app.py`, en `_build_left` (línea 198-217), agregar la instanciación al principio del método, antes del label "TEXTOS":

```python
    def _build_left(self, left):
        pad = {"padx": 16}

        from .slides_panel import SlidesPanel
        self.slides_panel = SlidesPanel(left, self, bg=PANEL, panel_bg=PANEL,
                                         accent=ACCENT, text_color=TEXT, muted_color=MUTED)
        self.slides_panel.pack(fill=tk.X, padx=16, pady=(16, 4))

        tk.Label(left, text="TEXTOS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(6, 10), **pad)
```

(el `pady=(16, 10)` original del label "TEXTOS" baja a `(6, 10)` porque ahora el panel de miniaturas ocupa el espacio superior).

- [ ] **Step 3: Refrescar el panel de miniaturas en cada render**

En `_render_now` (línea 1097-1128), agregar la llamada a `self.slides_panel.refresh()` justo antes de `self.v_status.set("Vista previa lista.")`:

```python
            self._draw_selection_overlay()
            self._draw_guides()
            self._update_readout()
            self.slides_panel.refresh()
            self.v_status.set("Vista previa lista.")
```

- [ ] **Step 4: Verificación manual**

Correr la app y confirmar visualmente (no hay display en el entorno de tests automatizados, así que este paso es manual):

Run: `python generar_publicacion.py`

Verificar:
1. Al abrir, aparece el panel "🎞 Láminas" arriba a la izquierda con una miniatura (la lámina default).
2. "+ Agregar" agrega una segunda miniatura y la selecciona.
3. Click en una miniatura cambia la lámina activa (el resto de la UI — textos, capas, vista previa — se actualiza).
4. "⧉ Duplicar", "🗑 Eliminar", "▲ Subir", "▼ Bajar" funcionan como se espera.
5. "Copiar estilo →" pide un número de lámina destino y aplica el estilo sin pisar el texto de esa lámina.
6. Ctrl+Z después de cualquiera de estas acciones la deshace.

- [ ] **Step 5: Correr toda la suite**

Run: `python -m unittest discover -s tests -v`
Expected: `OK`, todos los tests (este task no agrega tests nuevos, pero no debe romper ninguno existente)

- [ ] **Step 6: Commit**

```bash
git add dcpub/slides_panel.py dcpub/app.py
git commit -m "Agregar panel de miniaturas de laminas (dcpub/slides_panel.py)"
```

---

### Task 7: Verificación headless de cierre (Secciones 1-3 de Fase 2)

**Files:**
- Create: `verificaciones/fase2_verificacion.py`

**Interfaces:**
- Consumes: todo lo producido en las Tareas 1-6.

- [ ] **Step 1: Escribir el script de verificación headless**

Crear `verificaciones/fase2_verificacion.py`:

```python
"""Verificación headless de Fase 2 (Secciones 1-3): multi-lámina, acciones
de lámina, copiar estilo, logo compartido, guardar/cargar. No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from dcpub.models import crear_proyecto_por_defecto, crear_slide_por_defecto, duplicar_slide
from dcpub.commands import AddSlideCommand, DeleteSlideCommand, ReorderSlideCommand, CommandStack
from dcpub.render import compose
from dcpub.project_io import save_project, load_project

OUT_DIR = Path(__file__).resolve().parent / "fase2_cierre_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (800, 800), (120, 150, 90)).save(path)


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    stack = CommandStack()

    # Agregar dos láminas más
    segunda = crear_slide_por_defecto(foto_path, titulo="Lámina 2")
    stack.push(AddSlideCommand(project.slides, segunda, 1))
    tercera = duplicar_slide(project.slides[0])
    tercera.layers[2].text = "Lámina 3"
    stack.push(AddSlideCommand(project.slides, tercera, 2))
    assert len(project.slides) == 3, "esperaba 3 laminas tras agregar 2"

    # Reordenar: la 3 pasa a estar primera
    stack.push(ReorderSlideCommand(project.slides, 0, 2))
    assert project.slides[0].layers[2].text == "Lámina 3"

    # Eliminar la del medio
    a_borrar = project.slides[1]
    stack.push(DeleteSlideCommand(project.slides, a_borrar))
    assert len(project.slides) == 2

    # Deshacer todo, en orden inverso
    for _ in range(4):
        stack.undo()
    assert len(project.slides) == 1, "el undo completo debe volver a 1 lamina"

    # Rehacer todo
    for _ in range(4):
        stack.redo()
    assert len(project.slides) == 2

    # Render de cada lámina restante, preview y full-res
    for i, slide in enumerate(project.slides):
        layers = [
            {"type": "photo", "key": l.id, "src": l.src, "zoom": l.zoom,
             "offset_x": l.offset_x, "offset_y": l.offset_y, "opacity": l.opacity}
            if l.type == "photo" else
            {"type": "logo", "key": l.id, "src": l.src, "x": l.x, "y": l.y,
             "size": l.w, "opacity": l.opacity}
            if l.type == "logo" else
            {"type": "title", "key": l.id, "text": l.text, "x": l.x, "y": l.y,
             "size": l.size, "opacity": l.opacity}
            if l.type == "text" and l.role == "title" else
            {"type": "sub", "key": l.id, "text": l.text, "x": l.x, "y": l.y,
             "size": l.size, "opacity": l.opacity}
            if l.type == "text" and l.role == "subtitle" else
            {"type": "desc", "key": l.id, "text": l.text, "icon": l.icon,
             "x": l.x, "y": l.y, "size": l.size, "opacity": l.opacity}
            for l in slide.layers if l.visible
        ]
        preview_img, _ = compose(layers, (432, 540), None)
        preview_img.save(OUT_DIR / f"lamina_{i + 1}_preview.png")
        fullres_img, _ = compose(layers, (slide.format["w"], slide.format["h"]), None)
        fullres_img.save(OUT_DIR / f"lamina_{i + 1}_fullres.png")
        assert fullres_img.size == (slide.format["w"], slide.format["h"])

    # Guardar y recargar el proyecto multi-lamina
    project_path = OUT_DIR / "fase2_control.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    assert len(reloaded.slides) == len(project.slides)
    assert [s.layers[2].text for s in reloaded.slides] == [s.layers[2].text for s in project.slides]

    print("HEADLESS_OK")
    print(f"Láminas finales: {len(project.slides)}")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el script**

Run: `python verificaciones/fase2_verificacion.py`
Expected: `HEADLESS_OK` impreso al final, sin excepciones

- [ ] **Step 3: Correr toda la suite del proyecto una última vez**

Run: `python -m unittest discover -s tests -v`
Expected: `OK`, todos los tests (los de Fase 1 + Fase 3/5 de Codex + los nuevos de esta Fase 2)

- [ ] **Step 4: Commit**

```bash
git add verificaciones/fase2_verificacion.py verificaciones/fase2_cierre_control
git commit -m "Agregar verificacion headless de cierre de Fase 2 (secciones 1-3)"
```

---

## Fuera de este plan

- `dcpub/batch_import.py` y `Exporter.exportar_todas` (Secciones 4-5 del diseño): asignados a Codex en paralelo, se integran a `app.py` en un plan/tarea posterior una vez que ambas partes estén listas.
- Reordenar miniaturas por arrastre, checkbox "aplicar a todas" para paleta/CTA/fuente: fuera de alcance de Fase 2 según el diseño aprobado.
