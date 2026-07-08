"""Tests del motor de render (dcpub.render.compose y dcpub.render._get_background)."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from dcpub.fonts import FontManager
from dcpub.render import compose, wrap_text, _get_background


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


if __name__ == "__main__":
    unittest.main()
