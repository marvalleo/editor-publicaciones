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


if __name__ == "__main__":
    unittest.main()
