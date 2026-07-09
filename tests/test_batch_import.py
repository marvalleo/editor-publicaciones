"""Tests de dcpub.batch_import."""

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from dcpub.batch_import import importar_carrusel_por_lotes


FORMATO_CUADRADO = {"name": "test_square", "w": 800, "h": 800}


def _crear_imagen(path: Path, color=(120, 140, 90)):
    Image.new("RGB", (320, 240), color).save(path)


def _guardar_json(path: Path, entradas: list[dict]):
    path.write_text(json.dumps(entradas), encoding="utf-8")


def _capa_por_tipo(slide, tipo: str):
    return next(layer for layer in slide.layers if layer.type == tipo)


def _capa_texto_por_rol(slide, rol: str):
    return next(layer for layer in slide.layers if layer.type == "text" and layer.role == rol)


class TestImportarCarruselPorLotes(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_match_completo_exitoso(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _crear_imagen(self.carpeta / "02.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {
                "imagen": "01.jpg",
                "titulo": "Primera",
                "subtitulo": "Sub 1",
                "beneficios": ["Bosque", "Tinaja"],
                "cta": "Reserva hoy",
            },
            {
                "imagen": "02.jpg",
                "titulo": "Segunda",
                "subtitulo": "Sub 2",
                "beneficios": ["Vista"],
                "cta": "Consulta fechas",
            },
        ])

        project, advertencias = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual(advertencias, [])
        self.assertEqual(len(project.slides), 2)
        self.assertEqual(_capa_texto_por_rol(project.slides[0], "title").text, "Primera")
        self.assertEqual(_capa_texto_por_rol(project.slides[1], "subtitle").text, "Sub 2")

    def test_imagen_sin_entrada_se_omite_con_advertencia(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _crear_imagen(self.carpeta / "02.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {"imagen": "01.jpg", "titulo": "Primera", "subtitulo": "", "beneficios": [], "cta": ""}
        ])

        project, advertencias = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual(len(project.slides), 1)
        self.assertTrue(any("02.jpg" in advertencia for advertencia in advertencias))

    def test_entrada_sin_imagen_se_omite_con_advertencia(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {"imagen": "01.jpg", "titulo": "Primera", "subtitulo": "", "beneficios": [], "cta": ""},
            {"imagen": "02.jpg", "titulo": "Segunda", "subtitulo": "", "beneficios": [], "cta": ""},
        ])

        project, advertencias = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual(len(project.slides), 1)
        self.assertTrue(any("02.jpg" in advertencia for advertencia in advertencias))

    def test_orden_alfanumerico_por_nombre_de_imagen_no_por_json(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _crear_imagen(self.carpeta / "02.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {"imagen": "02.jpg", "titulo": "Segunda", "subtitulo": "", "beneficios": [], "cta": ""},
            {"imagen": "01.jpg", "titulo": "Primera", "subtitulo": "", "beneficios": [], "cta": ""},
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        titulos = [_capa_texto_por_rol(slide, "title").text for slide in project.slides]
        self.assertEqual(titulos, ["Primera", "Segunda"])

    def test_formato_se_aplica_a_todas_las_laminas(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _crear_imagen(self.carpeta / "02.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {"imagen": "01.jpg", "titulo": "", "subtitulo": "", "beneficios": [], "cta": ""},
            {"imagen": "02.jpg", "titulo": "", "subtitulo": "", "beneficios": [], "cta": ""},
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual([slide.format for slide in project.slides], [FORMATO_CUADRADO, FORMATO_CUADRADO])

    def test_beneficios_se_unen_con_vinetas_en_descripcion(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {
                "imagen": "01.jpg",
                "titulo": "",
                "subtitulo": "",
                "beneficios": ["Parrilla privada", "Desayuno incluido"],
                "cta": "",
            }
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        descripcion = _capa_por_tipo(project.slides[0], "box").text
        self.assertEqual(descripcion, "• Parrilla privada\n• Desayuno incluido")

    def test_cta_se_preserva_en_extra_y_se_crea_como_capa_real(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {
                "imagen": "01.jpg",
                "titulo": "Titulo",
                "subtitulo": "Subtitulo",
                "beneficios": ["Beneficio"],
                "cta": "Reserva ahora",
            }
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        self.assertEqual(project.slides[0].extra["cta"], "Reserva ahora")
        cta_layers = [l for l in project.slides[0].layers if l.type == "cta"]
        self.assertEqual(len(cta_layers), 1)
        self.assertEqual(cta_layers[0].text, "Reserva ahora")

    def test_cta_vacio_no_crea_capa(self):
        _crear_imagen(self.carpeta / "01.jpg")
        _guardar_json(self.carpeta / "copys.json", [
            {"imagen": "01.jpg", "titulo": "", "subtitulo": "", "beneficios": [], "cta": ""}
        ])

        project, _ = importar_carrusel_por_lotes(self.carpeta, FORMATO_CUADRADO)

        cta_layers = [l for l in project.slides[0].layers if l.type == "cta"]
        self.assertEqual(cta_layers, [])


if __name__ == "__main__":
    unittest.main()
