"""Tests de la factory crear_proyecto_por_defecto (dcpub.models)."""

import unittest

from dcpub.models import crear_proyecto_por_defecto, crear_slide_por_defecto


def _sin_ids(slide_dict):
    data = dict(slide_dict)
    data["layers"] = [dict(layer) for layer in slide_dict["layers"]]
    for layer in data["layers"]:
        layer.pop("id", None)
    return data


class TestFactory(unittest.TestCase):
    def setUp(self):
        self.project = crear_proyecto_por_defecto("foto.jpg")
        self.slide = self.project.slides[0]

    def test_creates_one_slide_with_five_layers(self):
        self.assertEqual(len(self.project.slides), 1)
        self.assertEqual(len(self.slide.layers), 5)

    def test_layer_order_matches_v2_draw_order(self):
        types = [layer.type for layer in self.slide.layers]
        self.assertEqual(types, ["photo", "logo", "text", "text", "box"])

    def test_defaults_match_v2_values(self):
        by_name = {layer.name: layer for layer in self.slide.layers}

        logo = by_name["Logo"]
        self.assertEqual((logo.x, logo.y, logo.w), (0.40, 0.022, 0.20))

        titulo = by_name["Título"]
        self.assertEqual((titulo.x, titulo.y, titulo.size), (0.055, 0.42, 0.087))
        self.assertEqual(titulo.role, "title")
        self.assertEqual(titulo.text, "Tu título aquí")

        subtitulo = by_name["Subtítulo"]
        self.assertEqual((subtitulo.x, subtitulo.y, subtitulo.size), (0.50, 0.55, 0.050))
        self.assertEqual(subtitulo.role, "subtitle")
        self.assertEqual(subtitulo.text, "frase secundaria")

        desc = by_name["Descripción"]
        self.assertEqual((desc.x, desc.y, desc.size), (0.05, 0.808, 0.033))
        self.assertEqual(desc.icon, "planta")
        self.assertEqual(desc.text, "")

    def test_photo_layer_uses_given_path(self):
        photo = self.slide.layers[0]
        self.assertEqual(photo.src, "foto.jpg")
        self.assertEqual((photo.x, photo.y, photo.w, photo.h), (0.0, 0.0, 1.0, 1.0))
        self.assertEqual((photo.offset_x, photo.offset_y), (0.5, 0.5))

    def test_logo_layer_points_to_logo_file(self):
        logo = self.slide.layers[1]
        self.assertTrue(logo.src.endswith("logo-sin-fondo.png"))

    def test_default_photo_path_is_empty_string(self):
        project = crear_proyecto_por_defecto()
        self.assertEqual(project.slides[0].layers[0].src, "")

    def test_crear_slide_por_defecto_usa_textos_custom(self):
        slide = crear_slide_por_defecto(
            photo_path="custom.jpg",
            titulo="Titulo custom",
            subtitulo="Subtitulo custom",
            descripcion="Descripcion custom",
        )
        by_name = {layer.name: layer for layer in slide.layers}
        self.assertEqual(by_name["Foto"].src, "custom.jpg")
        self.assertEqual(by_name["Título"].text, "Titulo custom")
        self.assertEqual(by_name["Subtítulo"].text, "Subtitulo custom")
        self.assertEqual(by_name["Descripción"].text, "Descripcion custom")

    def test_crear_slide_por_defecto_usa_formato_custom(self):
        formato = {"name": "custom", "w": 800, "h": 1000}
        slide = crear_slide_por_defecto(formato=formato)
        self.assertEqual(slide.format, formato)
        self.assertIsNot(slide.format, formato)

    def test_crear_slide_por_defecto_default_equivale_a_proyecto_default(self):
        project = crear_proyecto_por_defecto("foto.jpg")
        slide = crear_slide_por_defecto("foto.jpg")
        self.assertEqual(_sin_ids(slide.to_dict()), _sin_ids(project.slides[0].to_dict()))

    def test_round_trip_preserves_full_project(self):
        from dcpub.models import Project
        restored = Project.from_dict(self.project.to_dict())
        self.assertEqual(restored.to_dict(), self.project.to_dict())


if __name__ == "__main__":
    unittest.main()
