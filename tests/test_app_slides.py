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
