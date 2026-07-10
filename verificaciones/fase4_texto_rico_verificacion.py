"""Verificación headless de Fase 4 (sub-fase 2): texto rico por elemento
(fuente, bold/italic/underline, tracking, interlineado, stroke, rotación
aplicada de verdad). No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.models import crear_proyecto_por_defecto
from dcpub.render import compose
from dcpub.fonts import FontManager

OUT_DIR = Path(__file__).resolve().parent / "fase4_texto_rico_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def _layer_dict_title(layer):
    return {"type": "title", "text": layer.text, "x": layer.x,
            "y": layer.y, "size": layer.size, "opacity": layer.opacity,
            "rotation": layer.rotation, "font_family": layer.font_family,
            "bold": layer.bold, "italic": layer.italic, "underline": layer.underline,
            "line_spacing": layer.line_spacing, "letter_spacing": layer.letter_spacing,
            "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width}


def _layer_dict_sub(layer):
    return {"type": "sub", "text": layer.text, "x": layer.x,
            "y": layer.y, "size": layer.size, "opacity": layer.opacity,
            "rotation": layer.rotation, "font_family": layer.font_family,
            "bold": layer.bold, "italic": layer.italic, "underline": layer.underline,
            "line_spacing": layer.line_spacing, "letter_spacing": layer.letter_spacing,
            "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width}


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    font_manager = FontManager()
    canvas_size = (project.slides[0].format["w"], project.slides[0].format["h"])
    title = next(l for l in project.slides[0].layers
                 if l.type == "text" and l.role == "title")
    sub = next(l for l in project.slides[0].layers
               if l.type == "text" and l.role == "subtitle")

    # Render neutro (defaults) — debe verse igual al comportamiento legado.
    render_neutro, _ = compose(
        [_layer_dict_title(title), _layer_dict_sub(sub)], canvas_size, font_manager)
    render_neutro.save(OUT_DIR / "neutro.png")

    # Aplicar texto rico a titulo y subtitulo.
    title.font_family = "lato"
    title.bold = True
    title.italic = True
    title.underline = True
    title.letter_spacing = 0.08
    title.stroke_on = True
    title.stroke_width = 0.03
    title.rotation = 10.0

    sub.font_family = "playfair"
    sub.rotation = -8.0
    sub.letter_spacing = 0.05

    render_rico, bboxes_rico = compose(
        [_layer_dict_title(title), _layer_dict_sub(sub)], canvas_size, font_manager)
    render_rico.save(OUT_DIR / "texto_rico.png")

    diff = ImageChops.difference(render_neutro.convert("RGB"), render_rico.convert("RGB"))
    assert diff.getbbox() is not None, "el render con texto rico debe diferir del neutro"
    assert "title" in bboxes_rico
    assert "sub" in bboxes_rico

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
