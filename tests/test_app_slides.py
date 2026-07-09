"""Tests de estado de lámina activa en dcpub.app.App (sin abrir Tk)."""

import unittest
from unittest.mock import patch

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


class TestOpenProjectSyncsSharedLogoCheckbox(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack

        self.app = App.__new__(App)
        self.app.commands = CommandStack()
        self.app.v_logo_shared = _FakeVar(False)
        self.app._confirm_discard_changes = lambda: True
        self.app._sync_widgets_from_slide = lambda: None
        self.app._set_dirty = lambda value: None
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._schedule_render = lambda: None
        self.app.v_status = _FakeVar("")

    def _open_with_project(self, proyecto):
        with patch("dcpub.app.filedialog.askopenfilename", return_value="proyecto.json"), \
             patch("dcpub.project_io.load_project", return_value=proyecto):
            App._open_project(self.app)

    def test_checkbox_is_checked_when_loaded_project_has_shared_logo(self):
        proyecto = crear_proyecto_por_defecto("foto1.jpg")
        proyecto.shared["logo"] = {"src": "logo-compartido.png"}

        self._open_with_project(proyecto)

        self.assertTrue(self.app.v_logo_shared.get())

    def test_checkbox_is_unchecked_when_loaded_project_has_no_shared_logo(self):
        self.app.v_logo_shared = _FakeVar(True)
        proyecto = crear_proyecto_por_defecto("foto1.jpg")
        proyecto.shared.pop("logo", None)

        self._open_with_project(proyecto)

        self.assertFalse(self.app.v_logo_shared.get())


class TestAfterHistoryChangeReconcilesActiveSlide(unittest.TestCase):
    """Hallazgo 1 de la revisión final: undo/redo de una operación de
    lámina (agregar/eliminar/mover) no debe dejar self.slide apuntando a
    un objeto huérfano ni current_slide_index fuera de rango."""

    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._render_now = lambda: None
        self.app._schedule_render = lambda: None
        self.app.v_status = _FakeVar("")

    def _assert_pointer_consistent(self):
        self.assertTrue(0 <= self.app.current_slide_index < len(self.app.project.slides))
        self.assertIs(self.app.slide, self.app.project.slides[self.app.current_slide_index])

    def test_add_slide_then_undo_reconciles_pointer(self):
        App._add_slide(self.app)
        self.assertEqual(self.app.current_slide_index, 1)

        App._undo(self.app)

        self._assert_pointer_consistent()
        self.assertEqual(len(self.app.project.slides), 2)

    def test_delete_slide_then_undo_reconciles_pointer(self):
        App._delete_slide(self.app)
        self.assertEqual(len(self.app.project.slides), 1)

        App._undo(self.app)

        self._assert_pointer_consistent()
        self.assertEqual(len(self.app.project.slides), 2)

    def test_move_slide_then_undo_reconciles_pointer(self):
        App._move_slide(self.app, 1)
        self.assertEqual(self.app.current_slide_index, 1)

        App._undo(self.app)

        self._assert_pointer_consistent()


class TestSyncSharedLogoOnDragAndResizeRelease(unittest.TestCase):
    """Hallazgo 3 de la revisión final: con logo compartido activo, soltar
    un drag/resize del logo debe actualizar project.shared["logo"] en vez
    de dejarlo congelado en el snapshot viejo (lo que provocaba que el
    logo "saltara" de vuelta a la posición anterior en el siguiente render)."""

    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app.v_photo = _FakeVar("")
        self.app.v_logo = _FakeVar("")
        self.app.txt_title = _FakeText("")
        self.app.v_sub = _FakeVar("")
        self.app.txt_desc = _FakeText("")
        self.app.v_icon = _FakeVar("planta")
        self.app.v_logo_shared = _FakeVar(False)
        self.app._set_dirty = lambda value: None
        self.app._schedule_render = lambda: None
        self.app._render_now = lambda: None

        self.app.v_logo_shared.set(True)
        App._toggle_shared_logo(self.app)

    def test_release_after_drag_updates_shared_logo_snapshot(self):
        logo_layer = App._layer_by_kind(self.app, "logo")
        self.app._selected = logo_layer
        self.app._drag_elem = App._token_for_layer(self.app, logo_layer)
        self.app._drag_start_xy = (logo_layer.x, logo_layer.y)
        self.app._resize = None

        logo_layer.x = 0.42
        logo_layer.y = 0.13

        App._on_release(self.app, event=None)

        self.assertEqual(self.app.project.shared["logo"]["x"], 0.42)
        self.assertEqual(self.app.project.shared["logo"]["y"], 0.13)

    def test_release_after_resize_updates_shared_logo_snapshot(self):
        logo_layer = App._layer_by_kind(self.app, "logo")
        self.app._selected = logo_layer
        self.app._drag_elem = None
        self.app._drag_start_xy = None
        token = App._token_for_layer(self.app, logo_layer)
        self.app._resize = {"kind": "logo", "token": token, "start_value": logo_layer.w}

        logo_layer.w = 0.35
        logo_layer.h = 0.35

        App._on_release(self.app, event=None)

        self.assertEqual(self.app.project.shared["logo"]["w"], 0.35)


class TestSyncSharedLogoOnNudgeAndCenter(unittest.TestCase):
    """Re-revisión del Hallazgo 3: el fix anterior cubrió drag/resize/slider,
    pero _nudge (flechas del teclado) y _center_selected (botones Centrar)
    también mueven x/y del logo sin sincronizar project.shared["logo"],
    provocando el mismo "salto" visual en el siguiente render."""

    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app.v_photo = _FakeVar("")
        self.app.v_logo = _FakeVar("")
        self.app.txt_title = _FakeText("")
        self.app.v_sub = _FakeVar("")
        self.app.txt_desc = _FakeText("")
        self.app.v_icon = _FakeVar("planta")
        self.app.v_logo_shared = _FakeVar(False)
        self.app._set_dirty = lambda value: None
        self.app._schedule_render = lambda: None
        self.app._render_now = lambda: None
        self.app._sync_sliders = lambda: None
        self.app.focus_get = lambda: None

        self.app.v_logo_shared.set(True)
        App._toggle_shared_logo(self.app)

    def test_nudge_updates_shared_logo_snapshot(self):
        logo_layer = App._layer_by_kind(self.app, "logo")
        self.app._selected = logo_layer

        App._nudge(self.app, 1, 0, 0.01)

        self.assertEqual(self.app.project.shared["logo"]["x"], logo_layer.x)
        self.assertEqual(self.app.project.shared["logo"]["y"], logo_layer.y)

    def test_center_selected_updates_shared_logo_snapshot(self):
        logo_layer = App._layer_by_kind(self.app, "logo")
        self.app._selected = logo_layer
        self.app._img_wh = (1080, 1350)
        bbox_key = App._bbox_key_for_layer(self.app, logo_layer)
        self.app._last_bboxes = {bbox_key: (100, 100, 300, 300)}

        App._center_selected(self.app, "x")

        self.assertEqual(self.app.project.shared["logo"]["x"], logo_layer.x)
        self.assertEqual(self.app.project.shared["logo"]["y"], logo_layer.y)


if __name__ == "__main__":
    unittest.main()
