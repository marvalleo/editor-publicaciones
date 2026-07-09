"""Exportar la lámina activa a PNG/JPG en resolución real."""

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


def export_image(project, layers, font_manager, dest_dir: Path, fmt: str = "png",
                  max_side: int = 2400) -> Path:
    """Renderiza `layers` (formato dict plano de compose(), ya con el texto
    sincronizado) a resolución real y la guarda en `dest_dir`, creándolo si no
    existe. `fmt` es "png" o "jpg". Devuelve la ruta del archivo creado."""
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    fw = project.slides[0].format["w"]
    fh = project.slides[0].format["h"]
    if fh >= fw:
        h = max_side
        w = max(1, round(max_side * fw / fh))
    else:
        w = max_side
        h = max(1, round(max_side * fh / fw))

    img, _ = compose(layers, (w, h), font_manager)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(project.name)
    ext = "png" if fmt == "png" else "jpg"
    out_path = dest_dir / f"{slug}_{timestamp}.{ext}"

    if fmt == "png":
        img.save(str(out_path))
    else:
        img.convert("RGB").save(str(out_path), quality=95)

    return out_path
