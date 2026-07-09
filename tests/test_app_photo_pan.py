"""Tests del arrastre de encuadre (panear) sobre la capa foto en el canvas."""

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


def _make_app_for_pan():
    app = App.__new__(App)
    app.project = crear_proyecto_por_defecto("foto.jpg")
    app.slide = app.project.slides[0]
    app._selected = None
    app._drag_elem = None
    app._photo_pan = None
    app._img_wh = (1000, 1000)
    app._img_origin = (0, 0)
    app.ctrl = {}
    app._updating = False
    return app


class TestApplyPhotoPan(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_for_pan()
        self.foto = App._layer_by_kind(self.app, "photo", self.app.slide)
        self.foto.offset_x = 0.5
        self.foto.offset_y = 0.5
        self.app._photo_pan = {
            "layer": self.foto,
            "excess": (500, 500),
            "start_offset": (0.5, 0.5),
            "start_point": (300, 300),
        }
        self.app._sync_sliders = lambda: None
        self.app._render_now = lambda: None

    def test_drag_updates_offset_within_bounds(self):
        class _Event:
            x, y = 350, 300  # +50 en x respecto al punto de inicio

        App._apply_photo_pan(self.app, _Event())

        self.assertLess(self.foto.offset_x, 0.5)
        self.assertEqual(self.foto.offset_y, 0.5)

    def test_drag_clamps_to_zero_and_one(self):
        class _Event:
            x, y = 5000, 5000  # arrastre enorme

        App._apply_photo_pan(self.app, _Event())

        self.assertGreaterEqual(self.foto.offset_x, 0.0)
        self.assertLessEqual(self.foto.offset_x, 1.0)


if __name__ == "__main__":
    unittest.main()
