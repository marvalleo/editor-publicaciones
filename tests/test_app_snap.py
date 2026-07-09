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


class TestOffsetDeltaForDrag(unittest.TestCase):
    def test_dragging_right_decreases_offset_x(self):
        from dcpub.app import _offset_delta_for_drag
        d_ox, d_oy = _offset_delta_for_drag(dx_img=50, dy_img=0, excess_x=500, excess_y=500)
        self.assertLess(d_ox, 0)
        self.assertEqual(d_oy, 0)

    def test_dragging_left_increases_offset_x(self):
        from dcpub.app import _offset_delta_for_drag
        d_ox, _ = _offset_delta_for_drag(dx_img=-50, dy_img=0, excess_x=500, excess_y=500)
        self.assertGreater(d_ox, 0)

    def test_zero_excess_gives_zero_delta(self):
        from dcpub.app import _offset_delta_for_drag
        d_ox, d_oy = _offset_delta_for_drag(dx_img=100, dy_img=100, excess_x=0, excess_y=0)
        self.assertEqual((d_ox, d_oy), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
