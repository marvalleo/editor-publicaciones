"""Tests de presets de paleta de marca."""

import unittest

from dcpub.presets.palette import PALETA_LEGACY, PALETA_PRINCIPAL, PALETAS


class TestPresetsPalette(unittest.TestCase):
    def test_paleta_principal_tiene_colores_de_marca(self):
        self.assertEqual(PALETA_PRINCIPAL["id"], "principal")
        self.assertEqual(PALETA_PRINCIPAL["verde"], [159, 184, 66])
        self.assertEqual(PALETA_PRINCIPAL["verde_oliva"], [111, 127, 50])
        self.assertEqual(PALETA_PRINCIPAL["verde_profundo"], [79, 94, 38])
        self.assertEqual(PALETA_PRINCIPAL["blanco"], [247, 241, 232])
        self.assertEqual(PALETA_PRINCIPAL["box"], [43, 30, 24, 158])
        self.assertEqual(PALETA_PRINCIPAL["sombra"], [20, 12, 8, 115])

    def test_paleta_legacy_preserva_valores_v2(self):
        self.assertEqual(PALETA_LEGACY["id"], "legacy")
        self.assertEqual(PALETA_LEGACY["verde"], [141, 194, 111])
        self.assertEqual(PALETA_LEGACY["blanco"], [255, 255, 255])
        self.assertEqual(PALETA_LEGACY["box"], [40, 25, 15, 215])

    def test_presets_estan_disponibles_por_id(self):
        self.assertIs(PALETAS["principal"], PALETA_PRINCIPAL)
        self.assertIs(PALETAS["legacy"], PALETA_LEGACY)

    def test_ambas_paletas_son_compatibles_con_project_palette(self):
        for palette in PALETAS.values():
            self.assertIn("verde", palette)
            self.assertIn("blanco", palette)
            self.assertIn("box", palette)


if __name__ == "__main__":
    unittest.main()
