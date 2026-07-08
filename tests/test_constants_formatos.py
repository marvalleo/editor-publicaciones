"""Tests de la lista de formatos disponibles (dcpub.constants.FORMATOS)."""

import unittest

from dcpub.constants import FORMATOS


class TestFormatos(unittest.TestCase):
    def test_hay_tres_formatos_predefinidos(self):
        self.assertEqual(len(FORMATOS), 3)

    def test_cada_formato_tiene_los_campos_esperados(self):
        for formato in FORMATOS:
            self.assertIn("name", formato)
            self.assertIn("label", formato)
            self.assertIn("w", formato)
            self.assertIn("h", formato)

    def test_nombres_son_unicos(self):
        nombres = [f["name"] for f in FORMATOS]
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_todos_los_formatos_son_verticales(self):
        for formato in FORMATOS:
            self.assertGreater(formato["h"], formato["w"])

    def test_primer_formato_es_4x5_1080x1350(self):
        self.assertEqual(FORMATOS[0], {
            "name": "feed_4x5", "label": "1080×1350 (4:5)", "w": 1080, "h": 1350,
        })


if __name__ == "__main__":
    unittest.main()
