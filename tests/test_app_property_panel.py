"""Tests de la lógica de centrado rápido (dcpub.app._center_position)
y del acceso genérico a parámetros anidados (adjust./overlay.)."""

import unittest

from dcpub.app import App, _center_position
from dcpub.models import crear_proyecto_por_defecto


class _FakeVar:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class TestCenterPosition(unittest.TestCase):
    def test_centers_on_x_axis_only(self):
        x0, y0 = _center_position("x", 10, 20, 100, 50, 1000, 800)
        self.assertEqual(x0, 450)
        self.assertEqual(y0, 20)

    def test_centers_on_y_axis_only(self):
        x0, y0 = _center_position("y", 10, 20, 100, 50, 1000, 800)
        self.assertEqual(x0, 10)
        self.assertEqual(y0, 375)

    def test_centers_on_both_axes(self):
        x0, y0 = _center_position("both", 10, 20, 100, 50, 1000, 800)
        self.assertEqual((x0, y0), (450, 375))


class TestNestedAdjustParams(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.project = crear_proyecto_por_defecto("foto.jpg")
        self.app.slide = self.app.project.slides[0]
        self.foto = App._layer_by_kind(self.app, "photo", self.app.slide)
        self.token = self.foto.id

    def test_get_layer_value_reads_from_adjust_dict(self):
        self.foto.adjust["brightness"] = 1.4
        value = App._get_layer_value(self.app, self.token, "adjust.brightness")
        self.assertEqual(value, 1.4)

    def test_set_layer_value_writes_into_adjust_dict(self):
        App._set_layer_value(self.app, self.token, "adjust.contrast", 0.6)
        self.assertEqual(self.foto.adjust["contrast"], 0.6)

    def test_get_layer_value_reads_from_overlay_dict(self):
        self.foto.overlay["strength"] = 0.5
        value = App._get_layer_value(self.app, self.token, "overlay.strength")
        self.assertEqual(value, 0.5)

    def test_slider_release_pushes_dict_item_command(self):
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app.ctrl = {self.token: {"adjust.brightness": _FakeVar(1.4)}}
        self.app._slider_start_value = 1.0
        self.foto.adjust["brightness"] = 1.4

        App._on_slider_release(self.app, self.token, "adjust.brightness")

        self.assertEqual(len(self.app.commands._undo_stack), 1)
        self.app.commands.undo()
        self.assertEqual(self.foto.adjust["brightness"], 1.0)


if __name__ == "__main__":
    unittest.main()
