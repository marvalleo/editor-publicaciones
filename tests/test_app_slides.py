"""Tests de estado de lámina activa en dcpub.app.App (sin abrir Tk)."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

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

    def test_build_layers_for_includes_photo_adjust_and_overlay(self):
        app = _make_app_with_two_slides()
        foto = App._layer_by_kind(app, "photo", app.slide)
        foto.adjust["brightness"] = 1.3
        foto.overlay["bottom_grad"] = True
        foto.overlay["strength"] = 0.7

        capas = App._build_layers_for(app, app.slide)

        foto_capa = next(c for c in capas if c["type"] == "photo")
        self.assertEqual(foto_capa["adjust"]["brightness"], 1.3)
        self.assertTrue(foto_capa["overlay"]["bottom_grad"])
        self.assertEqual(foto_capa["overlay"]["strength"], 0.7)

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


class TestBuildLayersForLineLayer(unittest.TestCase):
    def test_build_layers_for_includes_line_layer(self):
        from dcpub.models import LineLayer
        app = _make_app_with_two_slides()
        line = LineLayer(name="Línea", z=10, x=0.5, y=0.7,
                         length=0.30, thickness=0.004,
                         color=[1, 2, 3, 200], gap=0.05,
                         rotation=15.0, opacity=0.6)
        app.slide.layers.append(line)

        layers = App._build_layers_for(app, app.slide)

        line_dict = next(layer for layer in layers if layer["type"] == "line")
        self.assertEqual(line_dict["key"], line.id)
        self.assertEqual(line_dict["x"], 0.5)
        self.assertEqual(line_dict["y"], 0.7)
        self.assertEqual(line_dict["length"], 0.30)
        self.assertEqual(line_dict["thickness"], 0.004)
        self.assertEqual(line_dict["color"], [1, 2, 3, 200])
        self.assertEqual(line_dict["gap"], 0.05)
        self.assertEqual(line_dict["rotation"], 15.0)
        self.assertEqual(line_dict["opacity"], 0.6)


class TestAddLineLayer(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.calls = []
        self.app._build_property_panel = lambda: self.calls.append("props")
        self.app._refresh_layers_list = lambda: self.calls.append("layers")
        self.app._schedule_render = lambda: self.calls.append("render")

    def test_add_line_layer_appends_layer_and_selects_it(self):
        App._add_line_layer(self.app)

        line = self.app.slide.layers[-1]
        self.assertEqual(line.type, "line")
        self.assertEqual(line.name, "Línea")
        self.assertIs(self.app._selected, line)
        self.assertEqual(self.calls, ["props", "layers", "render"])

    def test_add_line_layer_is_undoable(self):
        before = len(self.app.slide.layers)
        App._add_line_layer(self.app)

        self.app.commands.undo()

        self.assertEqual(len(self.app.slide.layers), before)


class TestKindOfLineLayer(unittest.TestCase):
    def test_kind_of_line_layer_is_line(self):
        from dcpub.models import LineLayer
        app = App.__new__(App)

        self.assertEqual(App._kind_of(app, LineLayer()), "line")


class TestBuildLayersForDotsLayer(unittest.TestCase):
    def test_build_layers_for_includes_dots_with_project_count_and_active_index(self):
        from dcpub.models import DotsLayer
        app = _make_app_with_two_slides()
        app.current_slide_index = 1
        app.slide = app.project.slides[1]
        dots = DotsLayer(name="Puntos", z=10, x=0.5, y=0.9,
                         color=[1, 2, 3, 200], spacing=0.04,
                         opacity=0.7)
        app.slide.layers.append(dots)

        layers = App._build_layers_for(app, app.slide)

        dots_dict = next(layer for layer in layers if layer["type"] == "dots")
        self.assertEqual(dots_dict["count"], 2)
        self.assertEqual(dots_dict["active"], 1)
        self.assertEqual(dots_dict["color"], [1, 2, 3, 200])
        self.assertEqual(dots_dict["spacing"], 0.04)
        self.assertEqual(dots_dict["opacity"], 0.7)

    def test_build_layers_for_non_active_slide_uses_that_slides_own_index(self):
        """Reproduce el bug de miniaturas: SlidesPanel llama
        _build_layers_for(slide) para CADA lámina del panel, no solo la
        activa. El punto activo debe reflejar la posición de esa lámina
        dentro de project.slides, no self.current_slide_index (que sigue
        apuntando a la lámina que el usuario tiene seleccionada)."""
        from dcpub.models import DotsLayer
        app = _make_app_with_two_slides()
        app.current_slide_index = 0
        segunda = app.project.slides[1]
        segunda.layers.append(DotsLayer(name="Puntos", z=10))

        layers = App._build_layers_for(app, segunda)

        dots_dict = next(layer for layer in layers if layer["type"] == "dots")
        self.assertEqual(dots_dict["active"], 1)


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


class TestAddDotsLayer(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_with_two_slides()
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.calls = []
        self.app._build_property_panel = lambda: self.calls.append("props")
        self.app._refresh_layers_list = lambda: self.calls.append("layers")
        self.app._schedule_render = lambda: self.calls.append("render")

    def test_add_dots_layer_appends_layer_and_selects_it(self):
        App._add_dots_layer(self.app)

        dots = self.app.slide.layers[-1]
        self.assertEqual(dots.type, "dots")
        self.assertEqual(dots.name, "Puntos de carrusel")
        self.assertIs(self.app._selected, dots)
        self.assertEqual(self.calls, ["props", "layers", "render"])


class TestKindOfDotsLayer(unittest.TestCase):
    def test_kind_of_dots_layer_is_dots(self):
        from dcpub.models import DotsLayer
        app = App.__new__(App)

        self.assertEqual(App._kind_of(app, DotsLayer()), "dots")


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


class _FakeEvent:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class TestGeometricLayerPanelMetadata(unittest.TestCase):
    def test_line_and_dots_have_labels_but_no_size_range_requirement(self):
        from dcpub.app import LABELS, SIZE_RANGE

        self.assertEqual(LABELS["line"], "Línea")
        self.assertEqual(LABELS["dots"], "Puntos")
        self.assertNotIn("line", SIZE_RANGE)
        self.assertNotIn("dots", SIZE_RANGE)


class TestResizeGeometricLayers(unittest.TestCase):
    def _app_for_layer(self, layer):
        app = App.__new__(App)
        app.project = crear_proyecto_por_defecto("foto.jpg")
        app.slide = app.project.slides[0]
        app.slide.layers.append(layer)
        app._selected = layer
        app._last_bboxes = {layer.id: (40, 45, 60, 55)}
        app._bbox_key_for_layer = lambda l: l.id
        app._canvas_to_img = lambda x, y: (x, y)
        app._sync_sliders = lambda: None
        app._render_now = lambda: None
        return app

    def test_line_resize_uses_length_not_missing_size(self):
        from dcpub.models import LineLayer
        line = LineLayer(length=0.20)
        app = self._app_for_layer(line)

        App._start_resize(app, _FakeEvent(60, 50))
        App._apply_resize(app, _FakeEvent(70, 50))

        self.assertGreater(line.length, 0.20)

    def test_dots_resize_uses_spacing_not_missing_size(self):
        from dcpub.models import DotsLayer
        dots = DotsLayer(spacing=0.02)
        app = self._app_for_layer(dots)

        App._start_resize(app, _FakeEvent(60, 50))
        App._apply_resize(app, _FakeEvent(70, 50))

        self.assertGreater(dots.spacing, 0.02)


class _FakeReadout:
    def __init__(self):
        self.value = ""

    def set(self, value):
        self.value = value


class TestGeometricLayerReadout(unittest.TestCase):
    def test_line_readout_uses_length(self):
        from dcpub.models import LineLayer
        app = App.__new__(App)
        app._selected = LineLayer(x=0.1, y=0.2, length=0.33)
        app.v_readout = _FakeReadout()

        App._update_readout(app)

        self.assertIn("Largo: 0.330", app.v_readout.value)

    def test_dots_readout_uses_spacing(self):
        from dcpub.models import DotsLayer
        app = App.__new__(App)
        app._selected = DotsLayer(x=0.1, y=0.2, spacing=0.04)
        app.v_readout = _FakeReadout()

        App._update_readout(app)

        self.assertIn("Separación: 0.040", app.v_readout.value)


class TestImportBatch(unittest.TestCase):
    def setUp(self):
        from dcpub.commands import CommandStack
        self._tmpdir = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._tmpdir.name)

        self.app = App.__new__(App)
        self.app.project = crear_proyecto_por_defecto("foto_original.jpg")
        self.app.slide = self.app.project.slides[0]
        self.app.current_slide_index = 0
        self.app.commands = CommandStack()
        self.app._project_path = Path("original.json")
        self.app._selected = None
        self.app.v_logo_shared = _FakeVar(False)
        self.app.v_status = _FakeVar("")
        self.app._confirm_discard_changes = lambda: True
        self.app._sync_widgets_from_slide = lambda: None
        self.app._set_dirty = lambda value: None
        self.app._build_property_panel = lambda: None
        self.app._refresh_layers_list = lambda: None
        self.app._schedule_render = lambda: None

    def tearDown(self):
        self._tmpdir.cleanup()

    def _crear_lote(self, entradas, imagenes=("01.jpg", "02.jpg")):
        for nombre in imagenes:
            Image.new("RGB", (320, 240), (120, 140, 90)).save(self.carpeta / nombre)
        (self.carpeta / "copys.json").write_text(json.dumps(entradas), encoding="utf-8")

    def test_import_replaces_project_with_multi_slide_carousel(self):
        self._crear_lote([
            {"imagen": "01.jpg", "titulo": "Lámina uno", "subtitulo": "Sub 1"},
            {"imagen": "02.jpg", "titulo": "Lámina dos", "subtitulo": "Sub 2"},
        ])

        with patch("dcpub.app.filedialog.askdirectory", return_value=str(self.carpeta)):
            App._import_batch(self.app)

        self.assertEqual(len(self.app.project.slides), 2)
        self.assertIs(self.app.slide, self.app.project.slides[0])
        self.assertEqual(self.app.current_slide_index, 0)
        self.assertIsNone(self.app._project_path)

    def test_import_cancelled_dialog_leaves_project_untouched(self):
        proyecto_original = self.app.project

        with patch("dcpub.app.filedialog.askdirectory", return_value=""):
            App._import_batch(self.app)

        self.assertIs(self.app.project, proyecto_original)

    def test_import_respects_discard_confirmation(self):
        self.app._confirm_discard_changes = lambda: False
        proyecto_original = self.app.project

        with patch("dcpub.app.filedialog.askdirectory", return_value=str(self.carpeta)):
            App._import_batch(self.app)

        self.assertIs(self.app.project, proyecto_original)

    def test_import_with_unmatched_image_shows_warning_but_still_imports(self):
        self._crear_lote(
            [{"imagen": "01.jpg", "titulo": "Lámina uno"}],
            imagenes=("01.jpg", "02.jpg"),
        )

        with patch("dcpub.app.filedialog.askdirectory", return_value=str(self.carpeta)), \
             patch("dcpub.app.messagebox.showwarning") as mock_warn:
            App._import_batch(self.app)

        self.assertEqual(len(self.app.project.slides), 1)
        mock_warn.assert_called_once()

    def test_import_with_no_matches_shows_error_and_keeps_project(self):
        (self.carpeta / "copys.json").write_text(json.dumps([]), encoding="utf-8")
        proyecto_original = self.app.project

        with patch("dcpub.app.filedialog.askdirectory", return_value=str(self.carpeta)), \
             patch("dcpub.app.messagebox.showerror") as mock_error:
            App._import_batch(self.app)

        self.assertIs(self.app.project, proyecto_original)
        mock_error.assert_called_once()


class TestExportAll(unittest.TestCase):
    def setUp(self):
        from dcpub.fonts import FontManager
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

        foto1 = self.tmp_path / "foto1.jpg"
        foto2 = self.tmp_path / "foto2.jpg"
        Image.new("RGB", (320, 240), (120, 140, 90)).save(foto1)
        Image.new("RGB", (320, 240), (80, 100, 140)).save(foto2)

        self.app = App.__new__(App)
        self.app.project = crear_proyecto_por_defecto(str(foto1))
        segunda = crear_proyecto_por_defecto(str(foto2)).slides[0]
        self.app.project.slides.append(segunda)
        self.app.slide = self.app.project.slides[0]
        self.app.font_manager = FontManager()
        self.app.v_export_dir = _FakeVar(str(self.tmp_path / "salida"))
        self.app.v_status = _FakeVar("")
        self.app._sync_text_to_layers = lambda: None
        self.app.update = lambda: None

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_export_all_creates_one_file_per_slide(self):
        with patch("dcpub.app.messagebox.showinfo") as mock_info:
            App._export_all(self.app)

        dest = self.tmp_path / "salida"
        exported = list(dest.glob("*.png"))
        self.assertEqual(len(exported), 2)
        mock_info.assert_called_once()
