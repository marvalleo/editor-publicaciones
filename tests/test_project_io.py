"""Tests de dcpub.project_io (guardar/cargar proyecto con rutas relativas)."""

import json
import tempfile
import unittest
from pathlib import Path

from dcpub.models import Project, Slide, PhotoLayer, LogoLayer, crear_proyecto_por_defecto
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


if __name__ == "__main__":
    unittest.main()
