"""Verificación headless de Fase 4 (sub-fase 1): CTA + caja de descripción
configurable, migración de proyectos legado. No abre Tkinter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageChops

from dcpub.models import crear_proyecto_por_defecto, CTALayer
from dcpub.render import compose
from dcpub.project_io import save_project, load_project
from dcpub.batch_import import importar_carrusel_por_lotes
from dcpub.fonts import FontManager

OUT_DIR = Path(__file__).resolve().parent / "fase4_cta_caja_control"
OUT_DIR.mkdir(exist_ok=True)


def _foto_sintetica(path):
    Image.new("RGB", (1200, 1200), (120, 150, 90)).save(path)


def _layer_dict_box(layer):
    return {"type": "desc", "key": layer.id, "text": layer.text, "icon": layer.icon,
            "x": layer.x, "y": layer.y, "w": layer.w, "h": layer.h, "size": layer.size,
            "fill": layer.fill, "text_color": layer.text_color, "opacity": layer.opacity}


def _layer_dict_cta(layer):
    return {"type": "cta", "key": layer.id, "text": layer.text, "x": layer.x, "y": layer.y,
            "w": layer.w, "h": layer.h, "size": layer.size, "fill": layer.fill,
            "text_color": layer.text_color, "opacity": layer.opacity}


def main():
    foto_path = str(OUT_DIR / "foto_base.png")
    _foto_sintetica(foto_path)

    project = crear_proyecto_por_defecto(foto_path)
    font_manager = FontManager()
    canvas_size = (project.slides[0].format["w"], project.slides[0].format["h"])
    desc = next(l for l in project.slides[0].layers if l.type == "box")
    desc.text = "Descripción de prueba"

    # Render con la caja de descripcion default (w=0.90,h=0.12 fijados en el
    # modelo) vs. con colores/tamaño no default.
    render_default, _ = compose([_layer_dict_box(desc)], canvas_size, font_manager)
    render_default.save(OUT_DIR / "caja_default.png")

    desc.w = 0.5
    desc.h = 0.25
    desc.fill = [10, 80, 40, 220]
    desc.text_color = [255, 220, 0, 255]
    render_custom, _ = compose([_layer_dict_box(desc)], canvas_size, font_manager)
    render_custom.save(OUT_DIR / "caja_custom.png")

    diff = ImageChops.difference(render_default.convert("RGB"), render_custom.convert("RGB"))
    assert diff.getbbox() is not None, "la caja personalizada debe diferir de la default"

    # Capa CTA nueva, agregada a mano (equivalente al boton "+ Agregar CTA").
    cta = CTALayer(name="CTA", z=10, text="Reservá ahora", x=0.10, y=0.85, w=0.35, h=0.08)
    project.slides[0].layers.append(cta)
    render_con_cta, bboxes_con_cta = compose(
        [_layer_dict_box(desc), _layer_dict_cta(cta)], canvas_size, font_manager)
    render_con_cta.save(OUT_DIR / "con_cta.png")
    assert cta.id in bboxes_con_cta, f"CTA layer {cta.id} should have a bbox"

    # Guardar y recargar: el proyecto con capa CTA debe sobrevivir el ciclo.
    project_path = OUT_DIR / "fase4_control.dcpub.json"
    save_project(project, project_path)
    reloaded = load_project(project_path)
    reloaded_cta = [l for l in reloaded.slides[0].layers if l.type == "cta"]
    assert len(reloaded_cta) == 1
    assert reloaded_cta[0].text == "Reservá ahora"

    # Migracion de proyectos legado: BoxLayer con w=0,h=0 en disco vuelve con
    # los defaults nuevos en memoria tras cargar.
    legacy_project = crear_proyecto_por_defecto(foto_path)
    legacy_desc = next(l for l in legacy_project.slides[0].layers if l.type == "box")
    legacy_desc.w = 0.0
    legacy_desc.h = 0.0
    legacy_path = OUT_DIR / "fase4_legacy.dcpub.json"
    save_project(legacy_project, legacy_path)
    reloaded_legacy = load_project(legacy_path)
    reloaded_legacy_desc = next(l for l in reloaded_legacy.slides[0].layers if l.type == "box")
    assert reloaded_legacy_desc.w == 0.90
    assert reloaded_legacy_desc.h == 0.12

    # Importador por lotes crea CTALayer real.
    import_dir = OUT_DIR / "importar"
    import_dir.mkdir(exist_ok=True)
    _foto_sintetica(str(import_dir / "una.jpg"))
    import json as _json
    (import_dir / "entradas.json").write_text(_json.dumps([
        {"imagen": "una.jpg", "titulo": "T", "subtitulo": "S",
         "beneficios": ["Uno", "Dos"], "cta": "Escribinos"}
    ], ensure_ascii=False), encoding="utf-8")
    imported_project, _warnings = importar_carrusel_por_lotes(
        import_dir, project.slides[0].format)
    imported_cta = [l for l in imported_project.slides[0].layers if l.type == "cta"]
    assert len(imported_cta) == 1
    assert imported_cta[0].text == "Escribinos"

    print("HEADLESS_OK")
    print(f"Salida: {OUT_DIR}")


if __name__ == "__main__":
    main()
