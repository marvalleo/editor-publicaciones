"""Tests de la lógica de centrado rápido (dcpub.app._center_position)."""

import unittest

from dcpub.app import _center_position


class TestCenterPosition(unittest.TestCase):
    def test_centers_on_x_axis_only(self):
        x0, y0 = _center_position("x", 10, 20, 100, 50, 1000, 800)
        self.assertEqual(x0, 450)
        self.assertEqual(y0, 20)

    def test_centers_on_y_axis_only(self):
        x0, y0 = _center_position("y", 10, 20, 100, 50, 1000, 800)
        self.assertEqual(x0, 10)
        self.assertEqual(y0, 375)

    def test_centers_on_both_axes(self):
        x0, y0 = _center_position("both", 10, 20, 100, 50, 1000, 800)
        self.assertEqual((x0, y0), (450, 375))


if __name__ == "__main__":
    unittest.main()
