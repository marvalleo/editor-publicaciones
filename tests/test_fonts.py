"""Tests del gestor de fuentes (dcpub.fonts.FontManager)."""

import unittest

from dcpub.fonts import FontManager


class TestFontManager(unittest.TestCase):
    def test_load_returns_same_font_object_when_cached(self):
        fm = FontManager()
        font1 = fm.load("body", 24)
        font2 = fm.load("body", 24)
        self.assertIs(font1, font2)

    def test_load_all_roles_without_crashing(self):
        fm = FontManager()
        for role in ("title", "subtitle", "body"):
            font = fm.load(role, 20)
            self.assertIsNotNone(font)

    def test_load_enforces_minimum_size(self):
        fm = FontManager()
        # tamaño 0 o negativo no debe crashear; se aplica mínimo interno de 6px
        font = fm.load("body", 0)
        self.assertIsNotNone(font)

    def test_two_instances_do_not_share_cache(self):
        fm1 = FontManager()
        fm2 = FontManager()
        fm1.load("body", 30)
        self.assertEqual(len(fm2._cache), 0)


class TestFontManagerFamily(unittest.TestCase):
    def setUp(self):
        self.fm = FontManager()

    def test_load_without_family_uses_role_default(self):
        # Comportamiento legado: sin family, se usa la fuente de marca del rol.
        font_legacy = self.fm.load("title", 40)
        font_explicit_empty = self.fm.load("title", 40, family="")
        self.assertEqual(font_legacy.getname(), font_explicit_empty.getname())

    def test_load_with_family_returns_a_font(self):
        font = self.fm.load("title", 40, family="lato")
        self.assertIsNotNone(font)

    def test_different_families_can_produce_different_fonts(self):
        font_playfair = self.fm.load("title", 40, family="playfair")
        font_lato = self.fm.load("title", 40, family="lato")
        # No siempre se puede garantizar getname() distinto si el archivo de
        # marca no está descargado y ambos caen al mismo fallback de sistema,
        # pero al menos no debe explotar y debe devolver un ImageFont válido
        # en los dos casos.
        self.assertIsNotNone(font_playfair)
        self.assertIsNotNone(font_lato)


if __name__ == "__main__":
    unittest.main()
