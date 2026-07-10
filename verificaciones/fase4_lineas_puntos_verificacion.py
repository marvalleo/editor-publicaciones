"""Verificación headless de Fase 4: líneas decorativas + puntos de carrusel.
No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.fonts import FontManager
from dcpub.models import crear_proyecto_por_defecto, LineLayer, DotsLayer
from dcpub.project_io import save_project, load_project
from dcpub.render import compose
from dcpub.exporter import _layers_from_slide

OUT_DIR = Path(__file__).resolve().parent / "fase4_lineas_puntos_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def _normalizar_ids(project):
    for slide_index, slide in enumerate(project.slides, start=1):
        for layer_index, layer in enumerate(slide.layers, start=1):
            layer.id = f"s{slide_index:02d}_l{layer_index:02d}_{layer.type}"


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    project.slides.append(crear_proyecto_por_defecto(foto_path).slides[0])
    slide = project.slides[0]
    canvas_size = (slide.format["w"], slide.format["h"])
    font_manager = FontManager()

    line = LineLayer(name="Línea", z=10, x=0.50, y=0.66,
                     length=0.35, thickness=0.006,
                     color=[255, 0, 0, 255], gap=0.08,
                     rotation=8.0)
    dots = DotsLayer(name="Puntos", z=11, x=0.50, y=0.94,
                     color=[0, 255, 0, 255], spacing=0.035)
    slide.layers.extend([line, dots])
    _normalizar_ids(project)

    layers = _layers_from_slide(slide, total_slides=len(project.slides), active_index=0)
    render, bboxes = compose(layers, canvas_size, font_manager, palette=project.palette)
    render.save(OUT_DIR / "lineas_puntos.png")

    assert line.id in bboxes, "LineLayer debe producir bbox"
    assert dots.id in bboxes, "DotsLayer debe producir bbox"
    assert render.getbbox() is not None, "el render debe tener píxeles visibles"

    neutral_layers = [layer for layer in layers if layer["type"] not in ("line", "dots")]
    neutral, _ = compose(neutral_layers, canvas_size, font_manager, palette=project.palette)
    diff = ImageChops.difference(neutral.convert("RGB"), render.convert("RGB"))
    assert diff.getbbox() is not None, "líneas/puntos deben cambiar el render"

    project_path = OUT_DIR / "fase4_lineas_puntos.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    types = [layer.type for layer in reloaded.slides[0].layers]
    assert "line" in types
    assert "dots" in types

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
