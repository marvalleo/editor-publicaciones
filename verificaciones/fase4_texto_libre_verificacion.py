"""Verificación headless de Fase 4 (cierre): bloques de texto libre.
No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.fonts import FontManager
from dcpub.models import crear_proyecto_por_defecto, TextLayer
from dcpub.project_io import save_project, load_project
from dcpub.render import compose
from dcpub.exporter import _layers_from_slide

OUT_DIR = Path(__file__).resolve().parent / "fase4_texto_libre_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    slide = project.slides[0]
    canvas_size = (slide.format["w"], slide.format["h"])
    font_manager = FontManager()

    libre = TextLayer(name="Texto libre", role="free", z=50,
                       text="Bloque libre\nsegunda linea", x=0.10, y=0.15,
                       size=0.045, color=[255, 210, 0, 255],
                       font_family="dancing", bold=True, italic=True,
                       stroke_on=True, stroke_width=0.02, rotation=-6.0)
    slide.layers.append(libre)
    libre.id = "s01_free_01"

    layers = _layers_from_slide(slide)
    render, bboxes = compose(layers, canvas_size, font_manager, palette=project.palette)
    render.save(OUT_DIR / "texto_libre.png")

    assert libre.id in bboxes, "el bloque de texto libre debe producir bbox"

    neutral_layers = [l for l in layers if l["type"] != "free"]
    neutral, _ = compose(neutral_layers, canvas_size, font_manager, palette=project.palette)
    diff = ImageChops.difference(neutral.convert("RGB"), render.convert("RGB"))
    assert diff.getbbox() is not None, "el bloque libre debe cambiar el render"

    project_path = OUT_DIR / "fase4_texto_libre.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    roles = [l.role for l in reloaded.slides[0].layers if l.type == "text"]
    assert "free" in roles

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
