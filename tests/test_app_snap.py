"""Tests de la lógica de snap (dcpub.app._snap_position)."""

import unittest

from dcpub.app import _snap_position


class TestSnapPosition(unittest.TestCase):
    def test_snaps_to_horizontal_center(self):
        # iw=1000, bw=100 -> centro del lienzo en x=500; centro de la caja
        # queda a 2px del centro (dentro del umbral), debe ajustarse a x=450.
        new_x0, new_y0, guides = _snap_position(452, 300, 100, 50, 1000, 800)
        self.assertEqual(new_x0, 450)
        self.assertIn(("v", 500), guides)

    def test_snaps_to_vertical_center(self):
        # ih=800, bh=50 -> centro del lienzo en y=400; centro de la caja
        # queda a 2px del centro, debe ajustarse a y=375.
        new_x0, new_y0, guides = _snap_position(300, 377, 100, 50, 1000, 800)
        self.assertEqual(new_y0, 375)
        self.assertIn(("h", 400), guides)

    def test_snaps_to_left_margin(self):
        margin_x = 0.055 * 1000
        new_x0, new_y0, guides = _snap_position(margin_x + 3, 300, 100, 50, 1000, 800)
        self.assertEqual(new_x0, margin_x)
        self.assertIn(("v", margin_x), guides)

    def test_no_snap_when_far_from_any_target(self):
        new_x0, new_y0, guides = _snap_position(200, 200, 100, 50, 1000, 800)
        self.assertEqual((new_x0, new_y0), (200, 200))
        self.assertEqual(guides, [])


if __name__ == "__main__":
    unittest.main()
