"""Tests de dcpub.exporter (export_image)."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from dcpub.fonts import FontManager
from dcpub.models import Project, crear_slide_por_defecto, crear_proyecto_por_defecto
from dcpub.exporter import Exporter, export_image, _slugify


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


class TestExporterExportarTodas(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.project = Project(name="Carrusel Demo")
        self.project.slides = []
        for i, color in enumerate([(120, 140, 90), (80, 100, 140), (160, 100, 80)], start=1):
            photo_path = self.tmp_path / f"{i:02d}.jpg"
            Image.new("RGB", (800, 600), color).save(photo_path)
            self.project.slides.append(
                crear_slide_por_defecto(
                    photo_path=str(photo_path),
                    titulo=f"Lámina {i}",
                    subtitulo="Subtítulo",
                    descripcion=f"Descripción {i}",
                    formato={"name": "test_vertical", "w": 400, "h": 500},
                )
            )
        self.exporter = Exporter(FontManager(), max_side=500)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_exportar_todas_genera_un_archivo_por_lamina(self):
        dest = self.tmp_path / "salida"

        paths = self.exporter.exportar_todas(self.project, dest)

        self.assertEqual(len(paths), 3)
        self.assertTrue(all(path.exists() for path in paths))

    def test_exportar_todas_usa_nombre_con_indice_y_fecha(self):
        dest = self.tmp_path / "salida"

        paths = self.exporter.exportar_todas(self.project, dest)

        nombres = [path.name for path in paths]
        self.assertRegex(nombres[0], r"^Carrusel_Demo_01_\d{8}_\d{6}\.png$")
        self.assertRegex(nombres[1], r"^Carrusel_Demo_02_\d{8}_\d{6}\.png$")
        self.assertRegex(nombres[2], r"^Carrusel_Demo_03_\d{8}_\d{6}\.png$")

    def test_exportar_todas_renderiza_contenido_de_cada_lamina(self):
        dest = self.tmp_path / "salida"

        paths = self.exporter.exportar_todas(self.project, dest)

        with Image.open(paths[0]) as img_1, Image.open(paths[1]) as img_2, Image.open(paths[2]) as img_3:
            self.assertEqual(max(img_1.size), 500)
            self.assertEqual(max(img_2.size), 500)
            self.assertEqual(max(img_3.size), 500)
            self.assertNotEqual(img_1.getpixel((10, 10)), img_2.getpixel((10, 10)))
            self.assertNotEqual(img_2.getpixel((10, 10)), img_3.getpixel((10, 10)))


class TestLayersFromSlideBoxAndCTA(unittest.TestCase):
    def test_box_layer_includes_fill_text_color_w_h(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto
        slide = crear_slide_por_defecto("foto.jpg", descripcion="Texto")
        desc = next(l for l in slide.layers if l.type == "box")
        desc.fill = [1, 2, 3, 100]
        desc.text_color = [4, 5, 6, 200]

        capas = _layers_from_slide(slide)

        desc_capa = next(c for c in capas if c["type"] == "desc")
        self.assertEqual(desc_capa["fill"], [1, 2, 3, 100])
        self.assertEqual(desc_capa["text_color"], [4, 5, 6, 200])
        self.assertEqual(desc_capa["w"], desc.w)
        self.assertEqual(desc_capa["h"], desc.h)

    def test_cta_layer_included(self):
        from dcpub.exporter import _layers_from_slide
        from dcpub.models import crear_slide_por_defecto, CTALayer
        slide = crear_slide_por_defecto("foto.jpg")
        slide.layers.append(CTALayer(name="CTA", z=10, text="Reservá",
                                      x=0.1, y=0.9, w=0.3, h=0.08))

        capas = _layers_from_slide(slide)

        cta_capa = next(c for c in capas if c["type"] == "cta")
        self.assertEqual(cta_capa["text"], "Reservá")


if __name__ == "__main__":
    unittest.main()
