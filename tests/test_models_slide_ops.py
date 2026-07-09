"""Tests de duplicar_slide y plan_copia_estilo (dcpub.models)."""

import unittest

from dcpub.models import crear_slide_por_defecto, duplicar_slide, plan_copia_estilo


class TestDuplicarSlide(unittest.TestCase):
    def setUp(self):
        self.original = crear_slide_por_defecto(
            photo_path="foto.jpg", titulo="Titulo", subtitulo="Sub", descripcion="Desc")

    def test_duplicado_tiene_mismo_contenido(self):
        copia = duplicar_slide(self.original)
        self.assertEqual(
            [(l.type, l.text if hasattr(l, "text") else l.src) for l in copia.layers],
            [(l.type, l.text if hasattr(l, "text") else l.src) for l in self.original.layers],
        )

    def test_duplicado_tiene_ids_de_capa_nuevos(self):
        copia = duplicar_slide(self.original)
        ids_originales = {l.id for l in self.original.layers}
        ids_copia = {l.id for l in copia.layers}
        self.assertTrue(ids_originales.isdisjoint(ids_copia))

    def test_duplicado_es_independiente_del_original(self):
        copia = duplicar_slide(self.original)
        copia.layers[2].text = "Cambiado en la copia"
        self.assertNotEqual(self.original.layers[2].text, "Cambiado en la copia")

    def test_duplicado_de_photo_layer_no_comparte_dict_adjust(self):
        copia = duplicar_slide(self.original)
        foto_copia = copia.layers[0]
        foto_original = self.original.layers[0]
        foto_copia.adjust["brightness"] = 1.5
        self.assertEqual(foto_original.adjust["brightness"], 1.0)

    def test_duplicado_conserva_formato(self):
        formato = {"name": "custom", "w": 800, "h": 1000}
        original = crear_slide_por_defecto(formato=formato)
        copia = duplicar_slide(original)
        self.assertEqual(copia.format, formato)
        self.assertIsNot(copia.format, original.format)


class TestPlanCopiaEstilo(unittest.TestCase):
    def setUp(self):
        self.origen = crear_slide_por_defecto(
            photo_path="origen.jpg", titulo="Titulo origen", subtitulo="Sub origen")
        self.origen.layers[2].x = 0.9  # Título: posición distinta a la del destino
        self.origen.layers[2].size = 0.2
        self.destino = crear_slide_por_defecto(
            photo_path="destino.jpg", titulo="Titulo destino", subtitulo="Sub destino")

    def test_copia_posicion_y_tamano_de_titulo(self):
        cambios = plan_copia_estilo(self.origen, self.destino)
        titulo_destino = self.destino.layers[2]
        cambios_titulo = {(l.id, attr): val for l, attr, val in cambios if l is titulo_destino}
        self.assertEqual(cambios_titulo[(titulo_destino.id, "x")], 0.9)
        self.assertEqual(cambios_titulo[(titulo_destino.id, "size")], 0.2)

    def test_no_toca_el_texto_del_destino(self):
        cambios = plan_copia_estilo(self.origen, self.destino)
        atributos_tocados = {attr for _, attr, _ in cambios}
        self.assertNotIn("text", atributos_tocados)
        self.assertNotIn("src", atributos_tocados)

    def test_sin_diferencias_no_genera_cambios(self):
        cambios = plan_copia_estilo(self.origen, self.origen)
        self.assertEqual(cambios, [])

    def test_copia_ajustes_de_foto_como_dict_independiente(self):
        self.origen.layers[0].adjust["brightness"] = 1.8
        cambios = plan_copia_estilo(self.origen, self.destino)
        foto_destino = self.destino.layers[0]
        cambio_adjust = next(val for l, attr, val in cambios if l is foto_destino and attr == "adjust")
        self.assertEqual(cambio_adjust["brightness"], 1.8)
        self.assertIsNot(cambio_adjust, self.origen.layers[0].adjust)


if __name__ == "__main__":
    unittest.main()
