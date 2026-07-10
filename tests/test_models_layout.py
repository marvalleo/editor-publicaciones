"""Tests de dcpub.models.plan_aplicar_layout (Fase 5 - Layouts A-E)."""

import unittest

from dcpub.models import crear_slide_por_defecto, plan_aplicar_layout


class TestPlanAplicarLayout(unittest.TestCase):
    def setUp(self):
        self.slide = crear_slide_por_defecto(
            "foto.jpg", titulo="Mi título", subtitulo="Mi subtítulo",
            descripcion="Mi descripción")

    def _aplicar(self, layout_id):
        cambios = plan_aplicar_layout(self.slide, layout_id)
        for capa, attr, valor in cambios:
            setattr(capa, attr, valor)
        return cambios

    def test_layout_b_reposiciona_titulo_subtitulo_y_caja(self):
        self._aplicar("B")
        logo = self.slide.layers[1]
        titulo = self.slide.layers[2]
        subtitulo = self.slide.layers[3]
        caja = self.slide.layers[4]
        self.assertEqual((titulo.x, titulo.y, titulo.size), (0.074, 0.189, 0.079))
        self.assertEqual((subtitulo.x, subtitulo.y, subtitulo.size), (0.076, 0.356, 0.050))
        self.assertEqual((caja.x, caja.y, caja.w, caja.size), (0.067, 0.463, 0.463, 0.035))
        self.assertEqual((logo.x, logo.y, logo.w, logo.h), (0.072, 0.046, 0.139, 0.111))

    def test_no_toca_el_contenido_de_las_capas(self):
        self._aplicar("D")
        titulo = self.slide.layers[2]
        subtitulo = self.slide.layers[3]
        caja = self.slide.layers[4]
        self.assertEqual(titulo.text, "Mi título")
        self.assertEqual(subtitulo.text, "Mi subtítulo")
        self.assertEqual(caja.text, "Mi descripción")

    def test_no_toca_la_foto_de_fondo(self):
        foto = self.slide.layers[0]
        x0, y0, w0, h0 = foto.x, foto.y, foto.w, foto.h
        self._aplicar("E")
        self.assertEqual((foto.x, foto.y, foto.w, foto.h), (x0, y0, w0, h0))

    def test_layout_inexistente_devuelve_lista_vacia(self):
        cambios = plan_aplicar_layout(self.slide, "Z")
        self.assertEqual(cambios, [])

    def test_lamina_sin_subtitulo_ignora_esa_clave_sin_error(self):
        del self.slide.layers[3]  # saca la capa de subtítulo
        cambios = plan_aplicar_layout(self.slide, "C")
        claves_afectadas = {(c[0].type, getattr(c[0], "role", None)) for c in cambios}
        self.assertNotIn(("text", "subtitle"), claves_afectadas)

    def test_caja_no_recibe_cambio_de_h(self):
        cambios = plan_aplicar_layout(self.slide, "A")
        caja = self.slide.layers[4]
        atributos_caja = {attr for capa, attr, _ in cambios if capa is caja}
        self.assertNotIn("h", atributos_caja)


if __name__ == "__main__":
    unittest.main()
