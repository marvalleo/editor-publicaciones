"""Verificación headless de Fase 3: ajustes fotográficos, overlay, encuadre
por excess_for_zoom y undo de valores anidados. No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.models import crear_proyecto_por_defecto, DEFAULT_PHOTO_ADJUST
from dcpub.commands import CommandStack, DictItemChangeCommand, CompositeCommand
from dcpub.render import compose, excess_for_zoom
from dcpub.fonts import FontManager

OUT_DIR = Path(__file__).resolve().parent / "fase3_cierre_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1600, 1600), (120, 150, 90)).save(path)


def _layer_dict(layer):
    return {"type": "photo", "key": layer.id, "src": layer.src, "zoom": layer.zoom,
            "offset_x": layer.offset_x, "offset_y": layer.offset_y,
            "opacity": layer.opacity, "adjust": layer.adjust, "overlay": layer.overlay}


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    font_manager = FontManager()
    foto = next(l for l in project.slides[0].layers if l.type == "photo")

    canvas_size = (project.slides[0].format["w"], project.slides[0].format["h"])

    # Render neutro (defaults)
    neutro_img, _ = compose([_layer_dict(foto)], canvas_size, font_manager)
    neutro_img.save(OUT_DIR / "neutro.png")

    # Aplicar ajustes + overlay no neutros vía comandos (undo real)
    stack = CommandStack()
    stack.push(CompositeCommand([
        DictItemChangeCommand(foto.adjust, "brightness", foto.adjust["brightness"], 1.4),
        DictItemChangeCommand(foto.adjust, "warmth", foto.adjust["warmth"], 0.4),
        DictItemChangeCommand(foto.adjust, "vignette", foto.adjust["vignette"], 0.6),
    ]))
    stack.push(DictItemChangeCommand(foto.overlay, "bottom_grad", foto.overlay["bottom_grad"], True))
    stack.push(DictItemChangeCommand(foto.overlay, "strength", foto.overlay["strength"], 0.8))

    ajustado_img, _ = compose([_layer_dict(foto)], canvas_size, font_manager)
    ajustado_img.save(OUT_DIR / "ajustado.png")

    diff = ImageChops.difference(neutro_img.convert("RGB"), ajustado_img.convert("RGB"))
    assert diff.getbbox() is not None, "el render ajustado debe diferir del neutro"

    # Deshacer todo: debe volver a los defaults exactos
    for _ in range(5):
        stack.undo()
    assert foto.adjust == DEFAULT_PHOTO_ADJUST, "el undo debe restaurar los defaults de adjust"
    assert foto.overlay["bottom_grad"] is False
    assert foto.overlay["strength"] == 0.0

    # excess_for_zoom: a mayor zoom, mayor margen de encuadre disponible
    excess_zoom1 = excess_for_zoom((1600, 1600), canvas_size, zoom=1.0)
    excess_zoom2 = excess_for_zoom((1600, 1600), canvas_size, zoom=2.0)
    assert excess_zoom2[0] > excess_zoom1[0]
    assert excess_zoom2[1] > excess_zoom1[1]

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
