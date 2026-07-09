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


class TestPhotoAdjustSection(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.project = crear_proyecto_por_defecto("foto.jpg")
        self.app.slide = self.app.project.slides[0]
        self.foto = App._layer_by_kind(self.app, "photo", self.app.slide)
        self.app._selected = self.foto
        self.app._adjust_expanded = False
        self.app.ctrl = {}

    def test_reset_photo_adjust_restores_defaults_and_pushes_one_command(self):
        from dcpub.commands import CommandStack
        from dcpub.models import DEFAULT_PHOTO_ADJUST
        self.app.commands = CommandStack()
        self.foto.adjust["brightness"] = 1.5
        self.foto.adjust["vignette"] = 0.8
        self.app._build_property_panel = lambda: None
        self.app._schedule_render = lambda: None

        App._reset_photo_adjust(self.app, self.foto)

        self.assertEqual(self.foto.adjust, DEFAULT_PHOTO_ADJUST)

    def test_reset_photo_adjust_is_undoable_as_one_step(self):
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.foto.adjust["brightness"] = 1.5
        self.foto.adjust["vignette"] = 0.8
        self.app._build_property_panel = lambda: None
        self.app._schedule_render = lambda: None

        App._reset_photo_adjust(self.app, self.foto)
        self.app.commands.undo()

        self.assertEqual(self.foto.adjust["brightness"], 1.5)
        self.assertEqual(self.foto.adjust["vignette"], 0.8)

    def test_toggle_overlay_flag_flips_value(self):
        from dcpub.commands import CommandStack
        self.app.commands = CommandStack()
        self.app._schedule_render = lambda: None
        old = self.foto.overlay["bottom_grad"]

        App._toggle_overlay_flag(self.app, "bottom_grad")

        self.assertEqual(self.foto.overlay["bottom_grad"], not old)


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


if __name__ == "__main__":
    unittest.main()
