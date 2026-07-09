"""Tests de los rangos/etiquetas de ajuste fotográfico en dcpub.app."""

import unittest

from dcpub.app import ADJUST_RANGE, ADJUST_LABELS, OVERLAY_STRENGTH_RANGE
from dcpub.models import DEFAULT_PHOTO_ADJUST


class TestAdjustRanges(unittest.TestCase):
    def test_every_default_adjust_key_has_a_range_and_label(self):
        for key in DEFAULT_PHOTO_ADJUST:
            self.assertIn(key, ADJUST_RANGE)
            self.assertIn(key, ADJUST_LABELS)

    def test_every_default_value_is_within_its_range(self):
        for key, default in DEFAULT_PHOTO_ADJUST.items():
            lo, hi = ADJUST_RANGE[key]
            self.assertLessEqual(lo, default)
            self.assertLessEqual(default, hi)

    def test_overlay_strength_range_covers_zero_to_one(self):
        self.assertEqual(OVERLAY_STRENGTH_RANGE, (0.0, 1.0))


if __name__ == "__main__":
    unittest.main()
