"""Tests del motor de render (dcpub.render.compose y dcpub.render._get_background)."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from dcpub.constants import VERDE, BLANCO
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

    def test_title_partial_opacity_blends_text_instead_of_overwriting(self):
        opaque = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Hola", "x": 0.055, "y": 0.42, "size": 0.15, "opacity": 1.0},
        ]
        faded = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Hola", "x": 0.055, "y": 0.42, "size": 0.15, "opacity": 0.5},
        ]
        no_title = [{"type": "photo", "src": str(self.photo_path)}]
        img_opaque, _ = compose(opaque, (400, 500), self.font_manager)
        img_faded, _ = compose(faded, (400, 500), self.font_manager)
        img_none, _ = compose(no_title, (400, 500), self.font_manager)
        faded_pixels = list(img_faded.getdata())
        self.assertNotEqual(faded_pixels, list(img_opaque.getdata()))
        self.assertNotEqual(faded_pixels, list(img_none.getdata()))

    def test_sub_partial_opacity_blends_text_instead_of_overwriting(self):
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

    def test_title_opacity_zero_makes_text_invisible(self):
        layers_with = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Hola", "x": 0.055, "y": 0.42, "size": 0.15, "opacity": 0.0},
        ]
        layers_without = [{"type": "photo", "src": str(self.photo_path)}]
        img_with, _ = compose(layers_with, (400, 500), self.font_manager)
        img_without, _ = compose(layers_without, (400, 500), self.font_manager)
        self.assertEqual(list(img_with.getdata()), list(img_without.getdata()))

    def test_sub_opacity_zero_makes_text_and_lines_invisible(self):
        layers_with = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "sub", "text": "frase secundaria", "x": 0.50, "y": 0.55,
             "size": 0.050, "opacity": 0.0},
        ]
        layers_without = [{"type": "photo", "src": str(self.photo_path)}]
        img_with, _ = compose(layers_with, (400, 500), self.font_manager)
        img_without, _ = compose(layers_without, (400, 500), self.font_manager)
        self.assertEqual(list(img_with.getdata()), list(img_without.getdata()))

    def test_title_and_sub_opacity_one_matches_original_direct_draw(self):
        """Regresión: a opacity=1.0 (default), title/sub deben verse pixel-identicos
        a como se veian ANTES de que existiera el soporte de opacidad (sin el
        composite de capa transparente, que puede redondear distinto en los bordes
        antialiased donde la sombra se superpone al texto)."""
        from PIL import Image as PILImage, ImageDraw as PILImageDraw

        def _reference_compose(layers, canvas_size, font_manager):
            # Copia minima de la logica pre-opacidad de title/sub (antes de esta
            # tarea), dibujando siempre directo sobre el canvas compartido, sin
            # capa intermedia. Sirve de oraculo independiente para este test.
            W, H = canvas_size
            canvas = PILImage.new("RGBA", (W, H), (0, 0, 0, 0))
            draw = PILImageDraw.Draw(canvas)
            margin = int(W * 0.055)
            for layer in layers:
                kind = layer["type"]
                if kind == "photo":
                    canvas = _get_background(
                        layer["src"], (W, H),
                        zoom=layer.get("zoom", 1.0),
                        offset_x=layer.get("offset_x", 0.5),
                        offset_y=layer.get("offset_y", 0.5),
                    )
                    draw = PILImageDraw.Draw(canvas)
                elif kind == "title":
                    title = layer["text"]
                    if title.strip():
                        tsz = max(10, int(W * layer["size"]))
                        font_t = font_manager.load("title", tsz)
                        tx = int(layer["x"] * W)
                        ty = int(layer["y"] * H)
                        max_w = W - tx - margin
                        lines = []
                        for part in title.split("\n"):
                            part = part.strip()
                            if part:
                                lines += wrap_text(part, font_t, max_w, draw)
                        lh = int(tsz * 1.22)
                        for i, line in enumerate(lines):
                            yy = ty + i * lh
                            draw.text((tx + 3, yy + 3), line, font=font_t, fill=(0, 0, 0, 160))
                            draw.text((tx, yy), line, font=font_t, fill=BLANCO + (255,))
                elif kind == "sub":
                    subtitle = layer["text"]
                    if subtitle.strip():
                        ssz = max(8, int(W * layer["size"]))
                        font_s = font_manager.load("subtitle", ssz)
                        cx = int(layer["x"] * W)
                        sy = int(layer["y"] * H)
                        bb = draw.textbbox((0, 0), subtitle, font=font_s)
                        sw, sh = bb[2] - bb[0], bb[3] - bb[1]
                        sx = cx - sw // 2
                        ly = sy + sh // 2
                        lw_deco = max(2, int(W * 0.003))
                        line_len = int(W * 0.11)
                        gap = int(W * 0.03)
                        lx1 = max(0, sx - gap - line_len)
                        draw.line([(lx1, ly), (sx - gap, ly)], fill=VERDE, width=lw_deco)
                        rx2 = min(W, sx + sw + gap + line_len)
                        draw.line([(sx + sw + gap, ly), (rx2, ly)], fill=VERDE, width=lw_deco)
                        draw.text((sx + 2, sy + 2), subtitle, font=font_s, fill=(0, 0, 0, 130))
                        draw.text((sx, sy), subtitle, font=font_s, fill=VERDE)
            return canvas

        layers = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Título de prueba", "x": 0.055, "y": 0.42, "size": 0.087},
            {"type": "sub", "text": "frase secundaria", "x": 0.50, "y": 0.55, "size": 0.050},
        ]
        img_current, _ = compose(layers, (400, 500), self.font_manager)
        img_reference = _reference_compose(layers, (400, 500), self.font_manager)
        self.assertEqual(list(img_current.getdata()), list(img_reference.getdata()))


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
