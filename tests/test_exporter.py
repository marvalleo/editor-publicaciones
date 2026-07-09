"""Tests de dcpub.exporter (export_image)."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from dcpub.fonts import FontManager
from dcpub.models import crear_proyecto_por_defecto
from dcpub.exporter import export_image, _slugify


class TestSlugify(unittest.TestCase):
    def test_replaces_spaces_with_underscores(self):
        self.assertEqual(_slugify("Mi Proyecto"), "Mi_Proyecto")

    def test_strips_non_alphanumeric_characters(self):
        self.assertEqual(_slugify("Café / Cabañas!"), "Caf_Cabaas")

    def test_empty_name_falls_back_to_default(self):
        self.assertEqual(_slugify(""), "publicacion")


class TestExportImage(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.photo_path = self.tmp_path / "foto.jpg"
        Image.new("RGB", (800, 600), (120, 140, 90)).save(self.photo_path)
        self.font_manager = FontManager()
        self.project = crear_proyecto_por_defecto(str(self.photo_path))
        self.project.name = "Mi Proyecto"
        self.layers = [
            {"type": "photo", "src": str(self.photo_path)},
            {"type": "title", "text": "Hola", "x": 0.055, "y": 0.42, "size": 0.087},
        ]

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_export_creates_dest_dir_if_missing(self):
        dest = self.tmp_path / "nueva_carpeta"
        self.assertFalse(dest.exists())
        export_image(self.project, self.layers, self.font_manager, dest, fmt="png")
        self.assertTrue(dest.exists())

    def test_export_png_returns_existing_file_with_png_extension(self):
        dest = self.tmp_path / "salida"
        out_path = export_image(self.project, self.layers, self.font_manager, dest, fmt="png")
        self.assertTrue(out_path.exists())
        self.assertEqual(out_path.suffix, ".png")

    def test_export_jpg_returns_existing_file_with_jpg_extension(self):
        dest = self.tmp_path / "salida"
        out_path = export_image(self.project, self.layers, self.font_manager, dest, fmt="jpg")
        self.assertTrue(out_path.exists())
        self.assertEqual(out_path.suffix, ".jpg")

    def test_export_filename_contains_slugified_project_name(self):
        dest = self.tmp_path / "salida"
        out_path = export_image(self.project, self.layers, self.font_manager, dest, fmt="png")
        self.assertIn("Mi_Proyecto", out_path.name)

    def test_exported_image_matches_max_side(self):
        dest = self.tmp_path / "salida"
        out_path = export_image(self.project, self.layers, self.font_manager, dest,
                                 fmt="png", max_side=500)
        with Image.open(out_path) as img:
            self.assertEqual(max(img.size), 500)


if __name__ == "__main__":
    unittest.main()
