"""Exportar láminas a PNG/JPG en resolución real."""

import re
from datetime import datetime
from pathlib import Path

from .render import compose


def _slugify(name: str) -> str:
    """Convierte un nombre de proyecto en un nombre de archivo válido:
    espacios -> guion bajo, caracteres no alfanuméricos removidos."""
    slug = re.sub(r"\s+", "_", name.strip())
    slug = re.sub(r"[^A-Za-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "publicacion"


def _canvas_size(format_data: dict, max_side: int) -> tuple[int, int]:
    fw = format_data["w"]
    fh = format_data["h"]
    if fh >= fw:
        h = max_side
        w = max(1, round(max_side * fw / fh))
    else:
        w = max_side
        h = max(1, round(max_side * fh / fw))
    return w, h


def _layers_from_slide(slide) -> list[dict]:
    layers = []
    for layer in slide.layers:
        if not layer.visible:
            continue
        if layer.type == "photo":
            layers.append({
                "type": "photo",
                "key": layer.id,
                "src": layer.src,
                "zoom": layer.zoom,
                "offset_x": layer.offset_x,
                "offset_y": layer.offset_y,
                "adjust": layer.adjust,
                "overlay": layer.overlay,
                "opacity": layer.opacity,
            })
        elif layer.type == "logo":
            layers.append({
                "type": "logo",
                "key": layer.id,
                "src": layer.src,
                "x": layer.x,
                "y": layer.y,
                "size": layer.w,
                "opacity": layer.opacity,
            })
        elif layer.type == "text" and layer.role == "title":
            layers.append({
                "type": "title",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "size": layer.size,
                "opacity": layer.opacity,
                "rotation": layer.rotation,
                "font_family": layer.font_family,
                "bold": layer.bold,
                "italic": layer.italic,
                "underline": layer.underline,
                "line_spacing": layer.line_spacing,
                "letter_spacing": layer.letter_spacing,
                "stroke_on": layer.stroke_on,
                "stroke_width": layer.stroke_width,
            })
        elif layer.type == "text" and layer.role == "subtitle":
            layers.append({
                "type": "sub",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "size": layer.size,
                "opacity": layer.opacity,
                "rotation": layer.rotation,
                "font_family": layer.font_family,
                "bold": layer.bold,
                "italic": layer.italic,
                "underline": layer.underline,
                "line_spacing": layer.line_spacing,
                "letter_spacing": layer.letter_spacing,
                "stroke_on": layer.stroke_on,
                "stroke_width": layer.stroke_width,
            })
        elif layer.type == "box":
            layers.append({
                "type": "desc",
                "key": layer.id,
                "text": layer.text,
                "icon": layer.icon,
                "x": layer.x,
                "y": layer.y,
                "w": layer.w,
                "h": layer.h,
                "size": layer.size,
                "fill": layer.fill,
                "text_color": layer.text_color,
                "opacity": layer.opacity,
            })
        elif layer.type == "cta":
            layers.append({
                "type": "cta",
                "key": layer.id,
                "text": layer.text,
                "x": layer.x,
                "y": layer.y,
                "w": layer.w,
                "h": layer.h,
                "size": layer.size,
                "fill": layer.fill,
                "text_color": layer.text_color,
                "opacity": layer.opacity,
            })
    return layers


def _save_rendered_image(img, out_path: Path, fmt: str) -> None:
    if fmt == "png":
        img.save(str(out_path))
    else:
        img.convert("RGB").save(str(out_path), quality=95)


def _export_layers(layers, format_data: dict, font_manager, dest_dir: Path, filename: str,
                   fmt: str = "png", max_side: int = 2400, palette=None) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    img, _ = compose(layers, _canvas_size(format_data, max_side), font_manager, palette=palette)
    out_path = dest_dir / filename
    _save_rendered_image(img, out_path, fmt)
    return out_path


class Exporter:
    """Exportador reutilizable para proyectos completos."""

    def __init__(self, font_manager, max_side: int = 2400):
        self.font_manager = font_manager
        self.max_side = max_side

    def exportar_todas(self, project, carpeta_destino: Path) -> list[Path]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(project.name)
        total_digits = max(2, len(str(len(project.slides))))
        paths = []

        for index, slide in enumerate(project.slides, start=1):
            filename = f"{slug}_{index:0{total_digits}d}_{timestamp}.png"
            paths.append(
                _export_layers(
                    _layers_from_slide(slide),
                    slide.format,
                    self.font_manager,
                    carpeta_destino,
                    filename,
                    fmt="png",
                    max_side=self.max_side,
                    palette=project.palette,
                )
            )

        return paths


def export_image(project, layers, font_manager, dest_dir: Path, fmt: str = "png",
                  max_side: int = 2400) -> Path:
    """Renderiza `layers` (formato dict plano de compose(), ya con el texto
    sincronizado) a resolución real y la guarda en `dest_dir`, creándolo si no
    existe. `fmt` es "png" o "jpg". Devuelve la ruta del archivo creado."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(project.name)
    ext = "png" if fmt == "png" else "jpg"
    filename = f"{slug}_{timestamp}.{ext}"
    return _export_layers(
        layers,
        project.slides[0].format,
        font_manager,
        dest_dir,
        filename,
        fmt=fmt,
        max_side=max_side,
        palette=project.palette,
    )
