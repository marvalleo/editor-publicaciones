"""Tests de dcpub.project_io (guardar/cargar proyecto con rutas relativas)."""

import json
import tempfile
import unittest
from pathlib import Path

from dcpub.models import Project, Slide, PhotoLayer, LogoLayer, CTALayer, crear_proyecto_por_defecto
from dcpub.project_io import save_project, load_project


class TestSaveProject(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_save_creates_valid_json_file(self):
        project = crear_proyecto_por_defecto()
        out = self.tmp_path / "proyecto.json"
        save_project(project, out)
        self.assertTrue(out.exists())
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], project.version)

    def test_save_rewrites_photo_src_as_relative_when_under_project_dir(self):
        photo_dir = self.tmp_path / "fotos"
        photo_dir.mkdir()
        photo_path = photo_dir / "foto.jpg"
        photo_path.write_bytes(b"fake")

        project = crear_proyecto_por_defecto(str(photo_path))
        out = self.tmp_path / "proyecto.json"
        save_project(project, out)

        data = json.loads(out.read_text(encoding="utf-8"))
        photo_layer_data = next(l for l in data["slides"][0]["layers"] if l["type"] == "photo")
        self.assertEqual(photo_layer_data["src"], str(Path("fotos") / "foto.jpg"))

    def test_save_keeps_absolute_src_when_outside_project_dir(self):
        other_dir = tempfile.TemporaryDirectory()
        try:
            photo_path = Path(other_dir.name) / "foto.jpg"
            photo_path.write_bytes(b"fake")
            project = crear_proyecto_por_defecto(str(photo_path))
            out = self.tmp_path / "proyecto.json"
            save_project(project, out)
            data = json.loads(out.read_text(encoding="utf-8"))
            photo_layer_data = next(l for l in data["slides"][0]["layers"] if l["type"] == "photo")
            self.assertEqual(Path(photo_layer_data["src"]).resolve(), photo_path.resolve())
        finally:
            other_dir.cleanup()

    def test_save_leaves_empty_src_untouched(self):
        project = crear_proyecto_por_defecto("")
        out = self.tmp_path / "proyecto.json"
        save_project(project, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        photo_layer_data = next(l for l in data["slides"][0]["layers"] if l["type"] == "photo")
        self.assertEqual(photo_layer_data["src"], "")


class TestLoadProject(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_round_trip_preserves_project_name_and_format(self):
        project = crear_proyecto_por_defecto()
        project.name = "Mi Proyecto"
        out = self.tmp_path / "proyecto.json"
        save_project(project, out)
        loaded = load_project(out)
        self.assertEqual(loaded.name, "Mi Proyecto")
        self.assertEqual(loaded.default_format, project.default_format)

    def test_round_trip_preserves_layer_count_and_order(self):
        project = crear_proyecto_por_defecto()
        out = self.tmp_path / "proyecto.json"
        save_project(project, out)
        loaded = load_project(out)
        self.assertEqual(len(loaded.slides[0].layers), len(project.slides[0].layers))
        self.assertEqual(
            [l.type for l in loaded.slides[0].layers],
            [l.type for l in project.slides[0].layers],
        )

    def test_load_resolves_relative_photo_src_against_project_dir(self):
        photo_dir = self.tmp_path / "fotos"
        photo_dir.mkdir()
        photo_path = photo_dir / "foto.jpg"
        photo_path.write_bytes(b"fake")

        project = crear_proyecto_por_defecto(str(photo_path))
        out = self.tmp_path / "proyecto.json"
        save_project(project, out)

        loaded = load_project(out)
        loaded_photo = next(l for l in loaded.slides[0].layers if l.type == "photo")
        self.assertEqual(Path(loaded_photo.src).resolve(), photo_path.resolve())

    def test_load_keeps_absolute_src_as_is(self):
        other_dir = tempfile.TemporaryDirectory()
        try:
            photo_path = Path(other_dir.name) / "foto.jpg"
            photo_path.write_bytes(b"fake")
            project = crear_proyecto_por_defecto(str(photo_path))
            out = self.tmp_path / "proyecto.json"
            save_project(project, out)
            loaded = load_project(out)
            loaded_photo = next(l for l in loaded.slides[0].layers if l.type == "photo")
            self.assertEqual(Path(loaded_photo.src).resolve(), photo_path.resolve())
        finally:
            other_dir.cleanup()


class TestLoadProjectMigratesLegacyBoxSize(unittest.TestCase):
    def test_zero_w_h_box_layer_gets_new_defaults_on_load(self):
        project = crear_proyecto_por_defecto("foto.jpg")
        desc = next(l for l in project.slides[0].layers if l.type == "box")
        desc.w = 0.0
        desc.h = 0.0

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proyecto.dcpub.json"
            save_project(project, path)

            # Confirmar que el archivo en disco efectivamente quedo en 0,0
            # (proyecto "legado" simulado), antes de cargarlo.
            raw = json.loads(path.read_text(encoding="utf-8"))
            raw_box = next(l for l in raw["slides"][0]["layers"] if l["type"] == "box")
            self.assertEqual((raw_box["w"], raw_box["h"]), (0.0, 0.0))

            reloaded = load_project(path)

            # El archivo en disco no debe haber sido reescrito por load_project.
            raw_after_load = json.loads(path.read_text(encoding="utf-8"))
            raw_box_after_load = next(
                l for l in raw_after_load["slides"][0]["layers"] if l["type"] == "box"
            )
            self.assertEqual((raw_box_after_load["w"], raw_box_after_load["h"]), (0.0, 0.0))

        reloaded_desc = next(l for l in reloaded.slides[0].layers if l.type == "box")
        self.assertEqual(reloaded_desc.w, 0.90)
        self.assertEqual(reloaded_desc.h, 0.12)

    def test_nonzero_w_h_box_layer_is_left_untouched_on_load(self):
        project = crear_proyecto_por_defecto("foto.jpg")
        desc = next(l for l in project.slides[0].layers if l.type == "box")
        desc.w = 0.5
        desc.h = 0.25

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proyecto.dcpub.json"
            save_project(project, path)
            reloaded = load_project(path)

        reloaded_desc = next(l for l in reloaded.slides[0].layers if l.type == "box")
        self.assertEqual(reloaded_desc.w, 0.5)
        self.assertEqual(reloaded_desc.h, 0.25)

    def test_partial_zero_w_h_box_layer_only_fixes_the_zero_dimension(self):
        project = crear_proyecto_por_defecto("foto.jpg")
        desc = next(l for l in project.slides[0].layers if l.type == "box")
        desc.w = 0.5
        desc.h = 0.0

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proyecto.dcpub.json"
            save_project(project, path)
            reloaded = load_project(path)

        reloaded_desc = next(l for l in reloaded.slides[0].layers if l.type == "box")
        self.assertEqual(reloaded_desc.w, 0.5)
        self.assertEqual(reloaded_desc.h, 0.12)

    def test_zero_w_h_cta_layer_is_not_migrated(self):
        project = crear_proyecto_por_defecto("foto.jpg")
        cta = CTALayer(id="cta-test", name="CTA", z=99, x=0.0, y=0.0, w=0.0, h=0.0, text="Reserva ya")
        project.slides[0].layers.append(cta)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proyecto.dcpub.json"
            save_project(project, path)
            reloaded = load_project(path)

        reloaded_cta = next(l for l in reloaded.slides[0].layers if l.type == "cta")
        self.assertEqual(reloaded_cta.w, 0.0)
        self.assertEqual(reloaded_cta.h, 0.0)


if __name__ == "__main__":
    unittest.main()
