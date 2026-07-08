"""Tests de Slide y Project (dcpub.models)."""

import unittest

from dcpub.models import Slide, Project, TextLayer, PhotoLayer


class TestSlide(unittest.TestCase):
    def test_default_format_is_feed_4x5(self):
        slide = Slide()
        self.assertEqual(slide.format, {"name": "feed_4x5", "w": 1080, "h": 1350})

    def test_round_trip_preserves_layers(self):
        slide = Slide()
        slide.layers = [TextLayer(text="Hola", role="title"), PhotoLayer(src="a.jpg")]
        restored = Slide.from_dict(slide.to_dict())
        self.assertEqual(restored.format, slide.format)
        self.assertEqual(len(restored.layers), 2)
        self.assertIsInstance(restored.layers[0], TextLayer)
        self.assertIsInstance(restored.layers[1], PhotoLayer)
        self.assertEqual(restored.layers[0].text, "Hola")
        self.assertEqual(restored.layers[1].src, "a.jpg")

    def test_round_trip_empty_layers(self):
        slide = Slide()
        restored = Slide.from_dict(slide.to_dict())
        self.assertEqual(restored.layers, [])


class TestProject(unittest.TestCase):
    def test_default_palette_matches_v2(self):
        project = Project()
        self.assertEqual(project.palette["verde"], [141, 194, 111])

    def test_round_trip_preserves_slides(self):
        project = Project(name="Mi Proyecto")
        slide = Slide()
        slide.layers = [TextLayer(text="Hola")]
        project.slides = [slide]
        restored = Project.from_dict(project.to_dict())
        self.assertEqual(restored.name, "Mi Proyecto")
        self.assertEqual(len(restored.slides), 1)
        self.assertEqual(len(restored.slides[0].layers), 1)
        self.assertEqual(restored.slides[0].layers[0].text, "Hola")

    def test_shared_defaults_to_empty_dict(self):
        project = Project()
        self.assertEqual(project.shared, {})


if __name__ == "__main__":
    unittest.main()
