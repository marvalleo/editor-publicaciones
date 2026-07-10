"""Guardar y cargar proyectos (.json) con rutas de imagen relativas al archivo
de proyecto cuando sea posible."""

import json
from pathlib import Path

from .models import Project


def _rewrite_src_to_relative(src: str, project_dir: Path) -> str:
    if not src:
        return src
    src_path = Path(src)
    try:
        return str(src_path.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return str(src_path.resolve())


def _resolve_src_from_relative(src: str, project_dir: Path) -> str:
    if not src:
        return src
    src_path = Path(src)
    if src_path.is_absolute():
        return str(src_path)
    return str((project_dir / src_path).resolve())


def save_project(project: Project, path: Path) -> None:
    """Serializa `project` a JSON en `path`. Las rutas de imagen (`src` de capas
    de tipo photo/logo) se reescriben relativas a la carpeta de `path` cuando el
    archivo está dentro de ese árbol; si no, quedan absolutas."""
    path = Path(path)
    data = project.to_dict()
    project_dir = path.parent
    for slide_data in data["slides"]:
        for layer_data in slide_data["layers"]:
            if layer_data.get("type") in ("photo", "logo") and layer_data.get("src"):
                layer_data["src"] = _rewrite_src_to_relative(layer_data["src"], project_dir)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


_LEGACY_BOX_DEFAULT_W = 0.90
_LEGACY_BOX_DEFAULT_H = 0.0


def load_project(path: Path) -> Project:
    """Carga un Project desde el JSON en `path`, resolviendo las rutas de imagen
    relativas contra la carpeta de `path`. Migra en memoria (sin reescribir el
    archivo) las capas BoxLayer guardadas antes de que w/h fueran configurables
    (w=0 o h=0), completándolas con los defaults nuevos."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    project_dir = path.parent
    for slide_data in data["slides"]:
        for layer_data in slide_data["layers"]:
            if layer_data.get("type") in ("photo", "logo") and layer_data.get("src"):
                layer_data["src"] = _resolve_src_from_relative(layer_data["src"], project_dir)
            if layer_data.get("type") == "box":
                if not layer_data.get("w"):
                    layer_data["w"] = _LEGACY_BOX_DEFAULT_W
                if not layer_data.get("h"):
                    layer_data["h"] = _LEGACY_BOX_DEFAULT_H
    return Project.from_dict(data)
