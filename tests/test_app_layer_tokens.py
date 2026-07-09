"""Tests del puente App capa<->render para capas duplicadas."""

import dataclasses
import unittest

from dcpub.app import App
from dcpub.models import crear_proyecto_por_defecto


class TestLayerTokens(unittest.TestCase):
    def setUp(self):
        self.app = App.__new__(App)
        self.app.project = crear_proyecto_por_defecto()
        self.app.slide = self.app.project.slides[0]

    def test_kind_of_recognizes_duplicate_logo(self):
        logo = next(layer for layer in self.app.slide.layers if layer.type == "logo")
        copia = dataclasses.replace(logo)
        copia.id = "logo_copia"
        copia.w = 0.22
        copia.h = 0.22
        self.app.slide.layers.append(copia)

        self.assertEqual(App._kind_of(self.app, copia), "logo")
        self.assertEqual(App._get_layer_value(self.app, copia.id, "size"), 0.22)

    def test_set_layer_value_updates_duplicate_not_canonical(self):
        logo = next(layer for layer in self.app.slide.layers if layer.type == "logo")
        copia = dataclasses.replace(logo)
        copia.id = "logo_copia"
        copia.w = 0.22
        copia.h = 0.22
        self.app.slide.layers.append(copia)

        App._set_layer_value(self.app, copia.id, "size", 0.31)

        self.assertNotEqual(logo.w, 0.31)
        self.assertEqual((copia.w, copia.h), (0.31, 0.31))

    def test_build_layers_emits_unique_keys_for_duplicate_logos(self):
        logo = next(layer for layer in self.app.slide.layers if layer.type == "logo")
        copia = dataclasses.replace(logo)
        copia.id = "logo_copia"
        copia.src = "logo-copia.png"
        self.app.slide.layers.append(copia)
        self.app.v_photo = _Var("")
        self.app.v_logo = _Var("logo-canonico.png")
        self.app.txt_title = _Text("")
        self.app.v_sub = _Var("")
        self.app.txt_desc = _Text("")
        self.app.v_icon = _Var("planta")

        render_layers = App._build_layers(self.app)
        logo_layers = [layer for layer in render_layers if layer["type"] == "logo"]

        self.assertEqual([layer["key"] for layer in logo_layers], [logo.id, copia.id])
        self.assertEqual([layer["src"] for layer in logo_layers], ["logo-canonico.png", "logo-copia.png"])

    def test_sync_text_to_layers_updates_canonical_logo_src(self):
        logo = next(layer for layer in self.app.slide.layers if layer.type == "logo")
        self.app.v_photo = _Var("")
        self.app.v_logo = _Var("nuevo-logo.png")
        self.app.txt_title = _Text("")
        self.app.v_sub = _Var("")
        self.app.txt_desc = _Text("")
        self.app.v_icon = _Var("planta")

        App._sync_text_to_layers(self.app)

        self.assertEqual(logo.src, "nuevo-logo.png")

    def test_build_layers_uses_duplicate_text_content(self):
        title = next(layer for layer in self.app.slide.layers
                     if layer.type == "text" and layer.role == "title")
        copia = dataclasses.replace(title)
        copia.id = "titulo_copia"
        copia.text = "Texto de la copia"
        self.app.slide.layers.append(copia)
        self.app.v_photo = _Var("")
        self.app.v_logo = _Var("")
        self.app.txt_title = _Text("Texto canonico")
        self.app.v_sub = _Var("")
        self.app.txt_desc = _Text("")
        self.app.v_icon = _Var("planta")

        render_layers = App._build_layers(self.app)
        title_layers = [layer for layer in render_layers if layer["type"] == "title"]

        self.assertEqual(
            [(layer["key"], layer["text"]) for layer in title_layers],
            [(title.id, "Texto canonico"), (copia.id, "Texto de la copia")],
        )


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _Text:
    def __init__(self, value):
        self.value = value

    def get(self, *_args):
        return self.value


if __name__ == "__main__":
    unittest.main()
