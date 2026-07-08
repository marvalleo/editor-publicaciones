"""Tests del motor de render (dcpub.render.compose y dcpub.render._get_background)."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from dcpub.fonts import FontManager
from dcpub.render import compose, wrap_text, _get_background, _apply_opacity


class TestCompose(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.photo_path = Path(self._tmpdir.name) / "foto.jpg"
        Image.new("RGB", (800, 600), (120, 140, 90)).save(self.photo_path)
        self.font_manager = FontManager()

    def tearDown(self):
        self._tmpdir.cleanup()

    def _layers(self):
        return [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "logo", "x": 0.40, "y": 0.02, "size": 0.20},
            {"type": "title", "text": "Título de prueba", "x": 0.055, "y": 0.42, "size": 0.087},
            {"type": "sub", "text": "frase secundaria", "x": 0.50, "y": 0.55, "size": 0.050},
            {"type": "desc",
             "text": "Descripción de prueba con texto suficiente para envolver en varias líneas.",
             "icon": "planta", "x": 0.05, "y": 0.808, "size": 0.033},
        ]

    def test_compose_returns_image_of_exact_canvas_size(self):
        img, bboxes = compose(self._layers(), (400, 500), self.font_manager)
        self.assertEqual(img.size, (400, 500))
        self.assertEqual(img.mode, "RGBA")

    def test_compose_returns_bbox_per_layer_with_content(self):
        img, bboxes = compose(self._layers(), (400, 500), self.font_manager)
        self.assertIn("photo", bboxes)
        self.assertIn("logo", bboxes)
        self.assertIn("title", bboxes)
        self.assertIn("sub", bboxes)
        self.assertIn("desc", bboxes)

    def test_photo_bbox_covers_full_canvas(self):
        img, bboxes = compose(self._layers(), (400, 500), self.font_manager)
        self.assertEqual(bboxes["photo"], (0, 0, 400, 500))

    def test_compose_skips_layers_with_blank_text(self):
        layers = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "   ", "x": 0.055, "y": 0.42, "size": 0.087},
        ]
        img, bboxes = compose(layers, (400, 500), self.font_manager)
        self.assertNotIn("title", bboxes)

    def test_compose_without_photo_layer_returns_transparent_canvas_of_size(self):
        layers = [{"type": "title", "text": "Solo texto", "x": 0.1, "y": 0.1, "size": 0.08}]
        img, bboxes = compose(layers, (300, 400), self.font_manager)
        self.assertEqual(img.size, (300, 400))
        self.assertNotIn("photo", bboxes)

    def test_wrap_text_splits_long_text_into_multiple_lines(self):
        img = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(img)
        font = self.font_manager.load("body", 20)
        lines = wrap_text("una dos tres cuatro cinco seis siete ocho", font, 80, draw)
        self.assertGreater(len(lines), 1)

    def test_opacity_default_matches_explicit_full_opacity(self):
        layers_default = self._layers()
        layers_explicit = [dict(l, opacity=1.0) for l in self._layers()]
        img_a, _ = compose(layers_default, (400, 500), self.font_manager)
        img_b, _ = compose(layers_explicit, (400, 500), self.font_manager)
        self.assertEqual(list(img_a.getdata()), list(img_b.getdata()))

    def test_logo_opacity_zero_makes_it_invisible(self):
        layers_with = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "logo", "x": 0.40, "y": 0.02, "size": 0.20, "opacity": 0.0},
        ]
        layers_without = [
            {"type": "photo", "src": str(self.photo_path)},
        ]
        img_with, _ = compose(layers_with, (400, 500), self.font_manager)
        img_without, _ = compose(layers_without, (400, 500), self.font_manager)
        self.assertEqual(list(img_with.getdata()), list(img_without.getdata()))

    def test_title_opacity_reduces_text_alpha(self):
        opaque = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Hola", "x": 0.055, "y": 0.42, "size": 0.15, "opacity": 1.0},
        ]
        faded = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Hola", "x": 0.055, "y": 0.42, "size": 0.15, "opacity": 0.3},
        ]
        img_opaque, _ = compose(opaque, (400, 500), self.font_manager)
        img_faded, _ = compose(faded, (400, 500), self.font_manager)
        self.assertNotEqual(list(img_opaque.getdata()), list(img_faded.getdata()))

    def test_desc_box_opacity_zero_makes_box_invisible(self):
        layers_with = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "desc", "text": "Descripción de prueba.", "icon": "ninguno",
             "x": 0.05, "y": 0.808, "size": 0.033, "opacity": 0.0},
        ]
        layers_without = [
            {"type": "photo", "src": str(self.photo_path)},
        ]
        img_with, _ = compose(layers_with, (400, 500), self.font_manager)
        img_without, _ = compose(layers_without, (400, 500), self.font_manager)
        self.assertEqual(list(img_with.getdata()), list(img_without.getdata()))

    def test_desc_bbox_present_even_at_zero_opacity(self):
        layers = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "desc", "text": "Descripción de prueba.", "icon": "planta",
             "x": 0.05, "y": 0.808, "size": 0.033, "opacity": 0.0},
        ]
        img, bboxes = compose(layers, (400, 500), self.font_manager)
        self.assertIn("desc", bboxes)

    def test_desc_icon_partial_opacity_blends_instead_of_overwriting(self):
        opaque = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "desc", "text": "X", "icon": "planta",
             "x": 0.05, "y": 0.808, "size": 0.033, "opacity": 1.0},
        ]
        faded = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "desc", "text": "X", "icon": "planta",
             "x": 0.05, "y": 0.808, "size": 0.033, "opacity": 0.5},
        ]
        no_desc = [{"type": "photo", "src": str(self.photo_path)}]
        img_opaque, _ = compose(opaque, (400, 500), self.font_manager)
        img_faded, _ = compose(faded, (400, 500), self.font_manager)
        img_none, _ = compose(no_desc, (400, 500), self.font_manager)
        faded_pixels = list(img_faded.getdata())
        # A pixel at partial opacity must differ from BOTH the fully-opaque
        # version AND the version with no desc layer at all — proving it's a
        # blend, not a straight overwrite of either extreme.
        self.assertNotEqual(faded_pixels, list(img_opaque.getdata()))
        self.assertNotEqual(faded_pixels, list(img_none.getdata()))

    def test_sub_partial_opacity_blends_decorative_lines(self):
        opaque = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "sub", "text": "frase secundaria", "x": 0.50, "y": 0.55,
             "size": 0.050, "opacity": 1.0},
        ]
        faded = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "sub", "text": "frase secundaria", "x": 0.50, "y": 0.55,
             "size": 0.050, "opacity": 0.5},
        ]
        no_sub = [{"type": "photo", "src": str(self.photo_path)}]
        img_opaque, _ = compose(opaque, (400, 500), self.font_manager)
        img_faded, _ = compose(faded, (400, 500), self.font_manager)
        img_none, _ = compose(no_sub, (400, 500), self.font_manager)
        faded_pixels = list(img_faded.getdata())
        self.assertNotEqual(faded_pixels, list(img_opaque.getdata()))
        self.assertNotEqual(faded_pixels, list(img_none.getdata()))


class TestGetBackground(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        # Foto apaisada (800x400) para poder verificar el recorte con offset.
        self.photo_path = Path(self._tmpdir.name) / "foto.jpg"
        # Crear foto con gradiente de colores (no uniforme) para verificar offset.
        img = Image.new("RGB", (800, 400))
        pixels = img.load()
        for x in range(800):
            for y in range(400):
                pixels[x, y] = (int((x / 800) * 255), int((y / 400) * 255), 128)
        img.save(self.photo_path)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_cover_fills_exact_canvas_size_without_distortion(self):
        img = _get_background(str(self.photo_path), (300, 300), zoom=1.0, offset_x=0.5, offset_y=0.5)
        self.assertEqual(img.size, (300, 300))

    def test_zoom_greater_than_one_keeps_canvas_size(self):
        img = _get_background(str(self.photo_path), (300, 300), zoom=2.0, offset_x=0.5, offset_y=0.5)
        self.assertEqual(img.size, (300, 300))

    def test_different_offsets_produce_different_pixels(self):
        left = _get_background(str(self.photo_path), (100, 300), zoom=1.5, offset_x=0.0, offset_y=0.5)
        right = _get_background(str(self.photo_path), (100, 300), zoom=1.5, offset_x=1.0, offset_y=0.5)
        self.assertNotEqual(list(left.getdata()), list(right.getdata()))


class TestApplyOpacity(unittest.TestCase):
    def test_scales_alpha_of_rgba_color(self):
        self.assertEqual(_apply_opacity((10, 20, 30, 200), 0.5), (10, 20, 30, 100))

    def test_full_opacity_keeps_alpha_unchanged(self):
        self.assertEqual(_apply_opacity((10, 20, 30, 200), 1.0), (10, 20, 30, 200))

    def test_rgb_input_assumes_full_alpha_before_scaling(self):
        self.assertEqual(_apply_opacity((10, 20, 30), 0.5), (10, 20, 30, 128))

    def test_zero_opacity_gives_zero_alpha(self):
        self.assertEqual(_apply_opacity((10, 20, 30, 255), 0.0), (10, 20, 30, 0))

    def test_opacity_is_clamped_to_valid_range(self):
        self.assertEqual(_apply_opacity((10, 20, 30, 200), 5.0), (10, 20, 30, 200))
        self.assertEqual(_apply_opacity((10, 20, 30, 200), -1.0), (10, 20, 30, 0))


if __name__ == "__main__":
    unittest.main()
