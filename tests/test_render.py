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

    def test_compose_uses_optional_layer_key_for_bbox(self):
        layers = [
            {"type": "photo", "key": "foto_base", "src": str(self.photo_path)},
            {"type": "title", "key": "titulo_copia", "text": "Texto",
             "x": 0.055, "y": 0.42, "size": 0.087},
        ]
        img, bboxes = compose(layers, (400, 500), self.font_manager)
        self.assertIn("foto_base", bboxes)
        self.assertIn("titulo_copia", bboxes)
        self.assertNotIn("photo", bboxes)
        self.assertNotIn("title", bboxes)

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

    def test_logo_uses_src_when_provided(self):
        logo_path = Path(self._tmpdir.name) / "logo_rojo.png"
        Image.new("RGBA", (40, 40), (255, 0, 0, 255)).save(logo_path)
        layers = [
            {"type": "logo", "src": str(logo_path), "x": 0.0, "y": 0.0, "size": 0.20},
        ]
        img, bboxes = compose(layers, (100, 100), self.font_manager)
        self.assertEqual(bboxes["logo"], (0, 0, 20, 20))
        self.assertEqual(img.getpixel((10, 10)), (255, 0, 0, 255))

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


class TestExcessForZoom(unittest.TestCase):
    def test_no_excess_when_photo_matches_canvas_at_zoom_one(self):
        from dcpub.render import excess_for_zoom
        excess_x, excess_y = excess_for_zoom((1000, 1000), (1000, 1000), zoom=1.0)
        self.assertEqual((excess_x, excess_y), (0, 0))

    def test_excess_grows_with_zoom(self):
        from dcpub.render import excess_for_zoom
        excess_1 = excess_for_zoom((1000, 1000), (1000, 1000), zoom=1.0)
        excess_2 = excess_for_zoom((1000, 1000), (1000, 1000), zoom=2.0)
        self.assertGreater(excess_2[0], excess_1[0])
        self.assertGreater(excess_2[1], excess_1[1])

    def test_wide_photo_on_taller_canvas_has_horizontal_excess(self):
        from dcpub.render import excess_for_zoom
        excess_x, excess_y = excess_for_zoom((2000, 1000), (1000, 1500), zoom=1.0)
        self.assertGreater(excess_x, 0)


class TestDescBoxConfigurable(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "desc", "key": "desc", "text": "Una descripción de prueba",
                "icon": "ninguno", "x": 0.1, "y": 0.1, "size": 0.03, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_custom_width_changes_box_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, bboxes_default = compose([self._layer(w=0.90)], (1000, 1000), fm)
        img_narrow, bboxes_narrow = compose([self._layer(w=0.30)], (1000, 1000), fm)
        self.assertNotEqual(bboxes_default["desc"][2], bboxes_narrow["desc"][2])

    def test_zero_width_falls_back_to_legacy_90_percent(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer(w=0.0)], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["desc"]
        self.assertEqual(x1 - x0, int(1000 * 0.90))

    def test_custom_height_changes_box_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes_tall = compose([self._layer(w=0.90, h=0.30)], (1000, 1000), fm)
        _, bboxes_default = compose([self._layer(w=0.90, h=0.0)], (1000, 1000), fm)
        x0a, y0a, x1a, y1a = bboxes_tall["desc"]
        x0b, y0b, x1b, y1b = bboxes_default["desc"]
        self.assertGreater(y1a - y0a, y1b - y0b)

    def test_custom_fill_changes_box_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(w=0.90, h=0.15, fill=[40, 25, 15, 215])],
                                  (400, 400), fm)
        img_custom, _ = compose([self._layer(w=0.90, h=0.15, fill=[0, 200, 0, 255])],
                                 (400, 400), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_custom.getdata()))

    def test_custom_text_color_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_white, _ = compose(
            [self._layer(w=0.90, h=0.15, text_color=[255, 255, 255, 255])], (400, 400), fm)
        img_red, _ = compose(
            [self._layer(w=0.90, h=0.15, text_color=[255, 0, 0, 255])], (400, 400), fm)
        self.assertNotEqual(list(img_white.getdata()), list(img_red.getdata()))


class TestCTABox(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "cta", "key": "cta", "text": "Reservá ahora",
                "x": 0.3, "y": 0.8, "w": 0.4, "h": 0.08, "size": 0.03,
                "fill": [40, 25, 15, 215], "text_color": [255, 255, 255, 255],
                "opacity": 1.0}
        base.update(overrides)
        return base

    def test_cta_produces_bbox_matching_w_h(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["cta"]
        self.assertEqual(x1 - x0, int(1000 * 0.4))
        self.assertEqual(y1 - y0, int(1000 * 0.08))

    def test_cta_empty_text_produces_no_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer(text="")], (1000, 1000), fm)
        self.assertNotIn("cta", bboxes)

    def test_cta_fill_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_a, _ = compose([self._layer(fill=[40, 25, 15, 215])], (400, 400), fm)
        img_b, _ = compose([self._layer(fill=[0, 100, 200, 255])], (400, 400), fm)
        self.assertNotEqual(list(img_a.getdata()), list(img_b.getdata()))

    def test_cta_does_not_draw_icon(self):
        # No debe lanzar excepción ni requerir clave "icon" en absoluto.
        from dcpub.render import compose
        fm = self._font_manager()
        layer = self._layer()
        self.assertNotIn("icon", layer)
        img, bboxes = compose([layer], (1000, 1000), fm)
        self.assertIn("cta", bboxes)


class TestLineLayerRender(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "line", "key": "linea", "x": 0.5, "y": 0.5,
                "length": 0.40, "thickness": 0.02,
                "color": [255, 0, 0, 255], "gap": 0.0,
                "rotation": 0.0, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_line_without_gap_draws_single_centered_segment(self):
        from dcpub.render import compose
        img, bboxes = compose([self._layer()], (100, 100), self._font_manager())

        self.assertIn("linea", bboxes)
        self.assertEqual(img.getpixel((50, 50)), (255, 0, 0, 255))
        self.assertEqual(img.getpixel((29, 50)), (0, 0, 0, 0))
        self.assertEqual(img.getpixel((71, 50)), (0, 0, 0, 0))

    def test_line_with_gap_draws_two_segments_and_keeps_center_empty(self):
        from dcpub.render import compose
        img, bboxes = compose([self._layer(gap=0.20)], (100, 100), self._font_manager())

        self.assertIn("linea", bboxes)
        self.assertEqual(img.getpixel((50, 50)), (0, 0, 0, 0))
        self.assertEqual(img.getpixel((35, 50)), (255, 0, 0, 255))
        self.assertEqual(img.getpixel((65, 50)), (255, 0, 0, 255))

    def test_line_opacity_zero_keeps_bbox_but_draws_no_pixels(self):
        from dcpub.render import compose
        img, bboxes = compose([self._layer(opacity=0.0)], (100, 100), self._font_manager())

        self.assertIn("linea", bboxes)
        self.assertIsNone(img.getbbox())

    def test_line_rotation_changes_rendered_pixels(self):
        from dcpub.render import compose
        img_plain, _ = compose([self._layer(rotation=0.0)], (100, 100), self._font_manager())
        img_rotated, _ = compose([self._layer(rotation=30.0)], (100, 100), self._font_manager())

        self.assertNotEqual(list(img_plain.getdata()), list(img_rotated.getdata()))


class TestDotsLayerRender(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "dots", "key": "puntos", "x": 0.5, "y": 0.5,
                "count": 3, "active": 1, "color": [0, 255, 0, 255],
                "spacing": 0.10, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_dots_draws_count_circles_and_active_is_larger(self):
        from dcpub.render import compose
        img, bboxes = compose([self._layer()], (100, 100), self._font_manager())

        self.assertIn("puntos", bboxes)
        # Los 3 centros (2 puntos base + 1 activo) deben estar pintados.
        self.assertEqual(img.getpixel((40, 50)), (0, 255, 0, 255))
        self.assertEqual(img.getpixel((50, 50)), (0, 255, 0, 255))
        self.assertEqual(img.getpixel((60, 50)), (0, 255, 0, 255))
        # El punto activo (x=50) debe tener mayor radio vertical que uno
        # base (x=40): se mide cuantos pixeles opacos hay en cada columna,
        # sin asumir un radio fijo en pixeles.
        opaque_active = sum(1 for y in range(30, 70) if img.getpixel((50, y))[3] > 0)
        opaque_base = sum(1 for y in range(30, 70) if img.getpixel((40, y))[3] > 0)
        self.assertGreater(opaque_active, opaque_base)
        # Bien por fuera de cualquier circulo debe quedar transparente.
        self.assertEqual(img.getpixel((40, 30)), (0, 0, 0, 0))

    def test_dots_opacity_zero_keeps_bbox_but_draws_no_pixels(self):
        from dcpub.render import compose
        img, bboxes = compose([self._layer(opacity=0.0)], (100, 100), self._font_manager())

        self.assertIn("puntos", bboxes)
        self.assertIsNone(img.getbbox())

    def test_dots_render_as_discrete_circles_at_realistic_canvas_width(self):
        """A resolucion real (1080), los radios fijos en fraccion de W
        superaban el rango completo del slider de spacing, fusionando los
        puntos en una sola mancha. Los puntos deben verse como circulos
        separados en el spacing por defecto (0.025)."""
        from dcpub.render import compose
        W = 1080
        count = 5
        img, bboxes = compose(
            [self._layer(count=count, active=2, spacing=0.025)], (W, W), self._font_manager())
        x0, y0, x1, y1 = bboxes["puntos"]
        mid_y = (y0 + y1) // 2
        opaque = [img.getpixel((x, mid_y))[3] > 0 for x in range(x0, x1)]
        runs = 0
        previous = False
        for is_opaque in opaque:
            if is_opaque and not previous:
                runs += 1
            previous = is_opaque
        self.assertEqual(runs, count,
                          "los puntos deben verse como circulos separados, no una mancha continua")


class TestTrackedTextHelpers(unittest.TestCase):
    def _font(self):
        from dcpub.fonts import FontManager
        return FontManager().load("body", 40)

    def test_measure_line_width_no_spacing_matches_textbbox(self):
        from dcpub.render import _measure_line_width
        font = self._font()
        img = Image.new("RGBA", (1, 1))
        draw_ctx = ImageDraw.Draw(img)
        bb = draw_ctx.textbbox((0, 0), "Hola", font=font)
        expected = bb[2] - bb[0]
        self.assertEqual(_measure_line_width(draw_ctx, "Hola", font, 0), expected)

    def test_measure_line_width_grows_with_positive_spacing(self):
        from dcpub.render import _measure_line_width
        font = self._font()
        img = Image.new("RGBA", (1, 1))
        draw_ctx = ImageDraw.Draw(img)
        w_no_spacing = _measure_line_width(draw_ctx, "Hola", font, 0)
        w_with_spacing = _measure_line_width(draw_ctx, "Hola", font, 10)
        self.assertGreater(w_with_spacing, w_no_spacing)

    def test_draw_tracked_line_with_spacing_produces_wider_pixels_than_without(self):
        from dcpub.render import _draw_tracked_line
        font = self._font()

        img_tight = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
        _draw_tracked_line(ImageDraw.Draw(img_tight), (10, 10), "Hola",
                            font, (255, 255, 255, 255), 0)

        img_spaced = Image.new("RGBA", (400, 80), (0, 0, 0, 0))
        _draw_tracked_line(ImageDraw.Draw(img_spaced), (10, 10), "Hola",
                            font, (255, 255, 255, 255), 15)

        bbox_tight = img_tight.getbbox()
        bbox_spaced = img_spaced.getbbox()
        self.assertGreater(bbox_spaced[2] - bbox_spaced[0], bbox_tight[2] - bbox_tight[0])

    def test_render_text_lines_to_image_produces_nonempty_image(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img, pad = _render_text_lines_to_image(
            ["Hola mundo"], font, fill=(255, 255, 255, 255), line_height=48)
        self.assertIsNotNone(img.getbbox())
        self.assertGreaterEqual(pad, 0)

    def test_render_text_lines_to_image_underline_adds_pixels_below_text(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img_plain, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48, underline=False)
        img_underline, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48, underline=True)
        self.assertNotEqual(list(img_plain.getdata()), list(img_underline.getdata()))

    def test_render_text_lines_to_image_shadow_adds_pixels(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img_no_shadow, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48)
        img_shadow, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48,
            shadow_offset=(3, 3), shadow_fill=(0, 0, 0, 160))
        self.assertNotEqual(list(img_no_shadow.getdata()), list(img_shadow.getdata()))

    def test_render_text_lines_to_image_stroke_changes_pixels(self):
        from dcpub.render import _render_text_lines_to_image
        font = self._font()
        img_no_stroke, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48)
        img_stroke, _ = _render_text_lines_to_image(
            ["Hola"], font, fill=(255, 255, 255, 255), line_height=48,
            stroke_width=4, stroke_fill=(20, 12, 8, 255))
        self.assertNotEqual(list(img_no_stroke.getdata()), list(img_stroke.getdata()))


class TestItalicAndRotationHelpers(unittest.TestCase):
    def _sample_image(self):
        img = Image.new("RGBA", (100, 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([(10, 10), (90, 30)], fill=(255, 255, 255, 255))
        return img

    def test_italic_shear_widens_image(self):
        from dcpub.render import _apply_italic_shear
        img = self._sample_image()
        sheared = _apply_italic_shear(img)
        self.assertGreater(sheared.width, img.width)
        self.assertEqual(sheared.height, img.height)

    def test_italic_shear_preserves_content(self):
        from dcpub.render import _apply_italic_shear
        img = self._sample_image()
        sheared = _apply_italic_shear(img)
        self.assertIsNotNone(sheared.getbbox())

    def test_rotation_zero_returns_same_image(self):
        from dcpub.render import _apply_rotation
        img = self._sample_image()
        rotated = _apply_rotation(img, 0)
        self.assertEqual(rotated.size, img.size)

    def test_rotation_nonzero_expands_canvas(self):
        from dcpub.render import _apply_rotation
        img = self._sample_image()
        rotated = _apply_rotation(img, 30)
        self.assertGreater(rotated.width, img.width)


class TestTitleRichText(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "title", "key": "title", "text": "Titulo de prueba",
                "x": 0.1, "y": 0.4, "size": 0.08, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_defaults_produce_same_bbox_as_before(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        self.assertIn("title", bboxes)

    def test_bold_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(bold=False)], (1000, 1000), fm)
        img_bold, _ = compose([self._layer(bold=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_bold.getdata()))

    def test_underline_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(underline=False)], (1000, 1000), fm)
        img_underline, _ = compose([self._layer(underline=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_underline.getdata()))

    def test_letter_spacing_changes_bbox_width(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes_tight = compose([self._layer(letter_spacing=0.0)], (1000, 1000), fm)
        _, bboxes_spaced = compose([self._layer(letter_spacing=0.3)], (1000, 1000), fm)
        w_tight = bboxes_tight["title"][2] - bboxes_tight["title"][0]
        w_spaced = bboxes_spaced["title"][2] - bboxes_spaced["title"][0]
        self.assertGreater(w_spaced, w_tight)

    def test_stroke_on_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_off, _ = compose([self._layer(stroke_on=False)], (1000, 1000), fm)
        img_on, _ = compose([self._layer(stroke_on=True, stroke_width=0.05)], (1000, 1000), fm)
        self.assertNotEqual(list(img_off.getdata()), list(img_on.getdata()))

    def test_italic_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(italic=False)], (1000, 1000), fm)
        img_italic, _ = compose([self._layer(italic=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_italic.getdata()))

    def test_rotation_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(rotation=0.0)], (1000, 1000), fm)
        img_rotated, _ = compose([self._layer(rotation=20.0)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_rotated.getdata()))

    def test_font_family_lato_changes_pixels_vs_default(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(font_family="")], (1000, 1000), fm)
        img_lato, _ = compose([self._layer(font_family="lato")], (1000, 1000), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_lato.getdata()))


class TestSubtitleRichText(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "sub", "key": "sub", "text": "Subtitulo de prueba",
                "x": 0.5, "y": 0.55, "size": 0.05, "opacity": 1.0}
        base.update(overrides)
        return base

    def test_defaults_still_produce_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        self.assertIn("sub", bboxes)

    def test_bold_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(bold=False)], (1000, 1000), fm)
        img_bold, _ = compose([self._layer(bold=True)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_bold.getdata()))

    def test_font_family_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(font_family="")], (1000, 1000), fm)
        img_playfair, _ = compose([self._layer(font_family="playfair")], (1000, 1000), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_playfair.getdata()))

    def test_rotation_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_normal, _ = compose([self._layer(rotation=0.0)], (1000, 1000), fm)
        img_rotated, _ = compose([self._layer(rotation=-15.0)], (1000, 1000), fm)
        self.assertNotEqual(list(img_normal.getdata()), list(img_rotated.getdata()))


class TestFreeTextLayerRender(unittest.TestCase):
    def _font_manager(self):
        from dcpub.fonts import FontManager
        return FontManager()

    def _layer(self, **overrides):
        base = {"type": "free", "key": "libre", "text": "Bloque de prueba",
                "x": 0.1, "y": 0.4, "size": 0.05, "opacity": 1.0,
                "color": [255, 0, 0, 255]}
        base.update(overrides)
        return base

    def test_defaults_produce_a_bbox(self):
        from dcpub.render import compose
        fm = self._font_manager()
        _, bboxes = compose([self._layer()], (1000, 1000), fm)
        self.assertIn("libre", bboxes)

    def test_uses_own_color_not_brand_colors(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img, bboxes = compose([self._layer(color=[255, 0, 0, 255])], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["libre"]
        mid_y = (y0 + y1) // 2
        # Se busca el pixel opaco mas cercano al centro geometrico en vez de
        # exigir tinta exactamente en el punto medio: con texto real, el
        # punto medio exacto puede caer en el hueco entre letras/palabras
        # segun la fuente, sin que eso indique un color incorrecto.
        opaque = [img.getpixel((x, mid_y)) for x in range(x0, x1)
                  if img.getpixel((x, mid_y))[3] > 0]
        self.assertTrue(opaque, "se esperaba al menos un pixel de tinta en la fila media")
        self.assertEqual(opaque[0][:3], (255, 0, 0))

    def test_no_forced_shadow_behind_text(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img, bboxes = compose(
            [self._layer(x=0.3, y=0.3, color=[255, 255, 255, 255])], (1000, 1000), fm)
        x0, y0, x1, y1 = bboxes["libre"]
        # 3px a la derecha/abajo del bbox (offset de sombra de titulo/sub)
        # debe seguir transparente: un bloque libre no lleva sombra forzada.
        self.assertEqual(img.getpixel((x1 + 3, y1 + 3))[3], 0)

    def test_bold_italic_stroke_rotation_change_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_plain, _ = compose([self._layer()], (1000, 1000), fm)
        img_styled, _ = compose(
            [self._layer(bold=True, italic=True, stroke_on=True,
                         stroke_width=0.03, rotation=12.0)], (1000, 1000), fm)
        self.assertNotEqual(list(img_plain.getdata()), list(img_styled.getdata()))

    def test_font_family_changes_pixels(self):
        from dcpub.render import compose
        fm = self._font_manager()
        img_default, _ = compose([self._layer(font_family="")], (1000, 1000), fm)
        img_playfair, _ = compose([self._layer(font_family="playfair")], (1000, 1000), fm)
        self.assertNotEqual(list(img_default.getdata()), list(img_playfair.getdata()))


if __name__ == "__main__":
    unittest.main()
