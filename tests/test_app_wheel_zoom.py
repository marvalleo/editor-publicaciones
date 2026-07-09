"""Tests del zoom por rueda del mouse sobre la foto."""

import unittest

from dcpub.app import App
from dcpub.commands import CommandStack, PropertyChangeCommand
from dcpub.models import crear_proyecto_por_defecto


def _make_app_for_wheel():
    app = App.__new__(App)
    app.project = crear_proyecto_por_defecto("foto.jpg")
    app.slide = app.project.slides[0]
    app._img_wh = (1000, 1000)
    app._img_origin = (0, 0)
    app._last_bboxes = {}
    app._wheel_zoom_start = None
    app._wheel_zoom_job = None
    app.ctrl = {}
    app._sync_sliders = lambda: None
    app._render_now = lambda: None
    app.after = lambda delay, fn: "job-id"
    app.after_cancel = lambda job: None
    return app


class TestOnPhotoWheel(unittest.TestCase):
    def setUp(self):
        self.app = _make_app_for_wheel()
        self.foto = App._layer_by_kind(self.app, "photo", self.app.slide)
        self.foto.zoom = 1.0
        self.app._last_bboxes = {self.app._bbox_key_for_layer(self.foto): (0, 0, 1000, 1000)}

    def test_wheel_up_increases_zoom(self):
        class _Event:
            x, y, delta = 500, 500, 120

        App._on_photo_wheel(self.app, _Event())

        self.assertAlmostEqual(self.foto.zoom, 1.1)

    def test_wheel_down_decreases_zoom_but_not_below_one(self):
        class _Event:
            x, y, delta = 500, 500, -120

        App._on_photo_wheel(self.app, _Event())

        self.assertEqual(self.foto.zoom, 1.0)

    def test_wheel_outside_photo_bbox_does_nothing(self):
        self.app._last_bboxes = {self.app._bbox_key_for_layer(self.foto): (0, 0, 100, 100)}

        class _Event:
            x, y, delta = 500, 500, 120

        App._on_photo_wheel(self.app, _Event())

        self.assertEqual(self.foto.zoom, 1.0)

    def test_wheel_up_repeated_stays_within_max(self):
        class _Event:
            x, y, delta = 500, 500, 120

        for _ in range(30):
            App._on_photo_wheel(self.app, _Event())

        self.assertEqual(self.foto.zoom, 3.0)


class TestCommitWheelZoomCollapsesUndo(unittest.TestCase):
    """El debounce debe colapsar una ráfaga de eventos de rueda en un único
    PropertyChangeCommand cuando se dispara `_commit_wheel_zoom`."""

    def setUp(self):
        self.app = _make_app_for_wheel()
        self.app.commands = CommandStack()
        self.foto = App._layer_by_kind(self.app, "photo", self.app.slide)
        self.foto.zoom = 1.0
        self.app._last_bboxes = {self.app._bbox_key_for_layer(self.foto): (0, 0, 1000, 1000)}

    def test_burst_of_wheel_events_pushes_single_command_on_commit(self):
        class _Event:
            x, y, delta = 500, 500, 120

        zoom_before_burst = self.foto.zoom

        # Ráfaga: varios eventos de rueda seguidos, como si el usuario
        # girara la rueda rápido sin soltar (el debounce reprograma el job
        # en cada uno, así que ninguno llega a comprometerse todavía).
        for _ in range(3):
            App._on_photo_wheel(self.app, _Event())

        zoom_after_burst = self.foto.zoom
        self.assertNotEqual(zoom_before_burst, zoom_after_burst)
        self.assertEqual(len(self.app.commands._undo_stack), 0)

        # Se simula que el timer del debounce finalmente se dispara tras
        # ~400ms sin más eventos de rueda.
        App._commit_wheel_zoom(self.app)

        self.assertEqual(len(self.app.commands._undo_stack), 1)
        pushed = self.app.commands._undo_stack[0]
        self.assertIsInstance(pushed, PropertyChangeCommand)
        self.assertEqual(pushed.attr, "zoom")
        self.assertEqual(pushed.old_value, zoom_before_burst)
        self.assertEqual(pushed.new_value, zoom_after_burst)

        # Deshacer el único comando restaura el zoom previo a la ráfaga.
        self.app.commands.undo()
        self.assertEqual(self.foto.zoom, zoom_before_burst)


if __name__ == "__main__":
    unittest.main()
