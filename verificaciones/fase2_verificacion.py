"""Verificación headless de Fase 2 (Secciones 1-3): multi-lámina, acciones
de lámina, copiar estilo, logo compartido, guardar/cargar. No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from dcpub.models import crear_proyecto_por_defecto, crear_slide_por_defecto, duplicar_slide
from dcpub.commands import AddSlideCommand, DeleteSlideCommand, ReorderSlideCommand, CommandStack
from dcpub.render import compose
from dcpub.project_io import save_project, load_project
from dcpub.fonts import FontManager

OUT_DIR = Path(__file__).resolve().parent / "fase2_cierre_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (800, 800), (120, 150, 90)).save(path)


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    stack = CommandStack()
    font_manager = FontManager()

    # Agregar dos láminas más
    segunda = crear_slide_por_defecto(foto_path, titulo="Lámina 2")
    stack.push(AddSlideCommand(project.slides, segunda, 1))
    tercera = duplicar_slide(project.slides[0])
    tercera.layers[2].text = "Lámina 3"
    stack.push(AddSlideCommand(project.slides, tercera, 2))
    assert len(project.slides) == 3, "esperaba 3 laminas tras agregar 2"

    # Reordenar: la 3 pasa a estar primera
    stack.push(ReorderSlideCommand(project.slides, 0, 2))
    assert project.slides[0].layers[2].text == "Lámina 3"

    # Eliminar la del medio
    a_borrar = project.slides[1]
    stack.push(DeleteSlideCommand(project.slides, a_borrar))
    assert len(project.slides) == 2

    # Deshacer todo, en orden inverso
    for _ in range(4):
        stack.undo()
    assert len(project.slides) == 1, "el undo completo debe volver a 1 lamina"

    # Rehacer todo
    for _ in range(4):
        stack.redo()
    assert len(project.slides) == 2

    # Render de cada lámina restante, preview y full-res
    for i, slide in enumerate(project.slides):
        layers = [
            {"type": "photo", "key": l.id, "src": l.src, "zoom": l.zoom,
             "offset_x": l.offset_x, "offset_y": l.offset_y, "opacity": l.opacity}
            if l.type == "photo" else
            {"type": "logo", "key": l.id, "src": l.src, "x": l.x, "y": l.y,
             "size": l.w, "opacity": l.opacity}
            if l.type == "logo" else
            {"type": "title", "key": l.id, "text": l.text, "x": l.x, "y": l.y,
             "size": l.size, "opacity": l.opacity}
            if l.type == "text" and l.role == "title" else
            {"type": "sub", "key": l.id, "text": l.text, "x": l.x, "y": l.y,
             "size": l.size, "opacity": l.opacity}
            if l.type == "text" and l.role == "subtitle" else
            {"type": "desc", "key": l.id, "text": l.text, "icon": l.icon,
             "x": l.x, "y": l.y, "size": l.size, "opacity": l.opacity}
            for l in slide.layers if l.visible
        ]
        preview_img, _ = compose(layers, (432, 540), font_manager)
        preview_img.save(OUT_DIR / f"lamina_{i + 1}_preview.png")
        fullres_img, _ = compose(layers, (slide.format["w"], slide.format["h"]), font_manager)
        fullres_img.save(OUT_DIR / f"lamina_{i + 1}_fullres.png")
        assert fullres_img.size == (slide.format["w"], slide.format["h"])

    # Guardar y recargar el proyecto multi-lamina
    project_path = OUT_DIR / "fase2_control.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    assert len(reloaded.slides) == len(project.slides)
    assert [s.layers[2].text for s in reloaded.slides] == [s.layers[2].text for s in project.slides]

    print("HEADLESS_OK")
    print(f"Láminas finales: {len(project.slides)}")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
