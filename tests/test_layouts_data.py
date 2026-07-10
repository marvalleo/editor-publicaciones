"""Tests de dcpub.presets.layouts (datos puros de los layouts A-E)."""

import unittest

from dcpub.presets.layouts import LAYOUTS


class TestLayoutsData(unittest.TestCase):
    def test_contiene_los_5_layouts_esperados(self):
        self.assertEqual(set(LAYOUTS.keys()), {"A", "B", "C", "D", "E"})

    def test_cada_layout_tiene_nombre_y_campos(self):
        for layout_id, layout in LAYOUTS.items():
            self.assertIn("nombre", layout, f"{layout_id} sin nombre")
            self.assertIsInstance(layout["nombre"], str)
            self.assertIn("campos", layout, f"{layout_id} sin campos")

    def test_campos_usan_solo_claves_tipo_rol_permitidas(self):
        claves_permitidas = {
            ("logo", None), ("text", "title"), ("text", "subtitle"), ("box", None),
        }
        for layout_id, layout in LAYOUTS.items():
            for clave in layout["campos"]:
                self.assertIn(clave, claves_permitidas,
                              f"{layout_id} usa clave no permitida: {clave}")

    def test_campos_de_texto_no_incluyen_w_ni_h(self):
        for layout_id, layout in LAYOUTS.items():
            for clave in [("text", "title"), ("text", "subtitle")]:
                campos = layout["campos"].get(clave, {})
                self.assertNotIn("w", campos, f"{layout_id}/{clave} no debe tener w")
                self.assertNotIn("h", campos, f"{layout_id}/{clave} no debe tener h")

    def test_campos_de_caja_no_incluyen_h(self):
        for layout_id, layout in LAYOUTS.items():
            campos = layout["campos"].get(("box", None), {})
            self.assertNotIn("h", campos, f"{layout_id}/box no debe tener h")

    def test_layout_a_coincide_con_el_instructivo_de_medidas_exactas(self):
        campos = LAYOUTS["A"]["campos"]
        self.assertEqual(campos[("logo", None)],
                          {"x": 0.421, "y": 0.041, "w": 0.157, "h": 0.126})
        self.assertEqual(campos[("text", "title")], {"x": 0.093, "y": 0.181, "size": 0.086})
        self.assertEqual(campos[("text", "subtitle")], {"x": 0.157, "y": 0.276, "size": 0.050})
        self.assertEqual(campos[("box", None)],
                          {"x": 0.167, "y": 0.363, "w": 0.667, "size": 0.035})

    def test_layout_d_no_reposiciona_la_caja(self):
        # Layout D ("Minimal premium") pide explícitamente evitar una caja
        # de beneficio grande -> no incluye clave ("box", None), la caja
        # queda donde estaba sin tocarse al aplicar D.
        self.assertNotIn(("box", None), LAYOUTS["D"]["campos"])


if __name__ == "__main__":
    unittest.main()
