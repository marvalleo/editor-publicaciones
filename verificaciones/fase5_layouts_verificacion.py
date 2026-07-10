"""Verificación headless de Fase 5 (Layouts A-E aplicables).
No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from dcpub.fonts import FontManager
from dcpub.models import crear_proyecto_por_defecto, plan_aplicar_layout
from dcpub.presets.layouts import LAYOUTS
from dcpub.render import compose
from dcpub.exporter import _layers_from_slide

OUT_DIR = Path(__file__).resolve().parent / "fase5_layouts_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)
    font_manager = FontManager()

    imagenes = {}
    for layout_id in LAYOUTS:
        project = crear_proyecto_por_defecto(foto_path)
        slide = project.slides[0]
        slide.layers[2].text = "Título de prueba"
        slide.layers[3].text = "Subtítulo de prueba"
        slide.layers[4].text = "Descripción de prueba para el layout"

        cambios = plan_aplicar_layout(slide, layout_id)
        assert cambios, f"layout {layout_id} no generó cambios"
        for capa, attr, valor in cambios:
            setattr(capa, attr, valor)
        slide.layout_tag = layout_id

        canvas_size = (slide.format["w"], slide.format["h"])
        layers = _layers_from_slide(slide)
        render, bboxes = compose(layers, canvas_size, font_manager, palette=project.palette)
        render.save(OUT_DIR / f"layout_{layout_id}.png")
        imagenes[layout_id] = render

    # Los 5 layouts deben producir posiciones de título distintas entre sí
    titulos_bbox = {}
    for layout_id in LAYOUTS:
        project = crear_proyecto_por_defecto(foto_path)
        slide = project.slides[0]
        for capa, attr, valor in plan_aplicar_layout(slide, layout_id):
            setattr(capa, attr, valor)
        titulo_layer = slide.layers[2]
        titulos_bbox[layout_id] = (titulo_layer.x, titulo_layer.y, titulo_layer.size)

    assert len(set(titulos_bbox.values())) == 5, \
        f"se esperaban 5 posiciones de título distintas, hubo repetidas: {titulos_bbox}"

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
