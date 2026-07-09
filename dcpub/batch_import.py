"""Importador puro de carruseles por lotes."""

import json
from pathlib import Path

from .models import Project, crear_slide_por_defecto


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _buscar_json_unico(carpeta: Path) -> Path:
    archivos_json = sorted(carpeta.glob("*.json"))
    if len(archivos_json) != 1:
        raise ValueError(f"Se esperaba un único archivo .json en {carpeta}, se encontraron {len(archivos_json)}.")
    return archivos_json[0]


def _imagenes_por_nombre(carpeta: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in carpeta.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    }


def _beneficios_a_descripcion(beneficios) -> str:
    if not beneficios:
        return ""
    return "\n".join(f"• {str(item)}" for item in beneficios if str(item).strip())


def importar_carrusel_por_lotes(carpeta: Path, formato: dict) -> tuple[Project, list[str]]:
    """Crea un Project multi-lámina desde fotos y un JSON de copys.

    El CTA se preserva por lámina en ``slide.extra["cta"]`` y además se crea
    como ``CTALayer`` real en ``slide.layers`` cuando el texto no está vacío.
    """
    carpeta = Path(carpeta)
    json_path = _buscar_json_unico(carpeta)
    entradas = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(entradas, list):
        raise ValueError("El JSON de importación debe ser un array de objetos.")

    imagenes = _imagenes_por_nombre(carpeta)
    entradas_por_imagen = {
        str(entrada.get("imagen", "")): entrada
        for entrada in entradas
        if isinstance(entrada, dict) and entrada.get("imagen")
    }

    advertencias = []
    for nombre_imagen in sorted(imagenes):
        if nombre_imagen not in entradas_por_imagen:
            advertencias.append(f"Imagen omitida sin entrada en JSON: {nombre_imagen}")

    for nombre_imagen in sorted(entradas_por_imagen):
        if nombre_imagen not in imagenes:
            advertencias.append(f"Entrada omitida sin imagen correspondiente: {nombre_imagen}")

    project = Project()
    project.default_format = dict(formato)
    project.slides = []

    nombres_con_match = sorted(nombre for nombre in imagenes if nombre in entradas_por_imagen)
    for nombre_imagen in nombres_con_match:
        entrada = entradas_por_imagen[nombre_imagen]
        slide = crear_slide_por_defecto(
            photo_path=str(imagenes[nombre_imagen]),
            titulo=str(entrada.get("titulo", "")),
            subtitulo=str(entrada.get("subtitulo", "")),
            descripcion=_beneficios_a_descripcion(entrada.get("beneficios", [])),
            formato=formato,
        )
        cta_texto = str(entrada.get("cta", ""))
        slide.extra["cta"] = cta_texto
        if cta_texto.strip():
            from .models import CTALayer
            cta_layer = CTALayer(name="CTA", z=max((l.z for l in slide.layers), default=0) + 1,
                                  text=cta_texto, x=0.10, y=0.90, w=0.35, h=0.08)
            slide.layers.append(cta_layer)
        project.slides.append(slide)

    return project, advertencias
