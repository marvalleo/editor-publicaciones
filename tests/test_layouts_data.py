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

    def test_layout_a_coincide_con_valores_por_defecto(self):
        campos = LAYOUTS["A"]["campos"]
        self.assertEqual(campos[("logo", None)],
                          {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20})
        self.assertEqual(campos[("text", "title")], {"x": 0.055, "y": 0.42, "size": 0.087})
        self.assertEqual(campos[("text", "subtitle")], {"x": 0.50, "y": 0.55, "size": 0.050})
        self.assertEqual(campos[("box", None)], {"x": 0.05, "y": 0.808, "w": 0.90})


if __name__ == "__main__":
    unittest.main()
