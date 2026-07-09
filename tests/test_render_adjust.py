"""Tests de ajustes fotográficos del fondo."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from dcpub.fonts import FontManager
from dcpub.render import compose


class TestPhotoAdjustments(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.photo_path = Path(self._tmpdir.name) / "foto_patron.png"
        img = Image.new("RGB", (160, 120))
        draw = ImageDraw.Draw(img)
        for y in range(120):
            for x in range(160):
                draw.point((x, y), fill=(40 + x, 30 + y, 80 + (x + y) // 4))
        draw.rectangle((35, 25, 125, 95), outline=(230, 220, 120), width=4)
        img.save(self.photo_path)
        self.font_manager = FontManager()

    def tearDown(self):
        self._tmpdir.cleanup()

    def _render_photo(self, adjust=None, overlay=None):
        layers = [{
            "type": "photo",
            "src": str(self.photo_path),
            "adjust": adjust or {},
            "overlay": overlay or {},
        }]
        img, _ = compose(layers, (120, 120), self.font_manager)
        return img

    def _assert_distinct_from_neutral(self, adjust=None, overlay=None):
        neutral = self._render_photo()
        changed = self._render_photo(adjust=adjust, overlay=overlay)
        self.assertEqual(changed.size, neutral.size)
        self.assertNotEqual(list(changed.getdata()), list(neutral.getdata()))

    def test_brightness_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"brightness": 1.35})

    def test_contrast_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"contrast": 1.45})

    def test_saturation_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"saturation": 0.45})

    def test_warmth_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"warmth": 0.6})

    def test_sharpness_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"sharpness": 2.0})

    def test_shadows_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"shadows": 0.55})

    def test_vignette_changes_background_pixels(self):
        self._assert_distinct_from_neutral(adjust={"vignette": 0.7})

    def test_bottom_overlay_changes_background_pixels(self):
        self._assert_distinct_from_neutral(
            overlay={"bottom_grad": True, "strength": 0.7}
        )

    def test_top_overlay_changes_background_pixels(self):
        self._assert_distinct_from_neutral(
            overlay={"top_grad": True, "strength": 0.7}
        )


if __name__ == "__main__":
    unittest.main()
