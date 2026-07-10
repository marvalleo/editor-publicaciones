"""Layouts de marca predefinidos (A-E): reposicionan logo/título/subtítulo/
caja de una lámina sin tocar su contenido ni la foto de fondo. Ver
docs/superpowers/specs/2026-07-10-fase5-layouts-design.md para el diseño."""

LAYOUTS = {
    "A": {
        "nombre": "Actual",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.055, "y": 0.42, "size": 0.087},
            ("text", "subtitle"): {"x": 0.50, "y": 0.55, "size": 0.050},
            ("box", None): {"x": 0.05, "y": 0.808, "w": 0.90},
        },
    },
    "B": {
        "nombre": "Centrado",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.12, "y": 0.44, "size": 0.080},
            ("text", "subtitle"): {"x": 0.12, "y": 0.535, "size": 0.045},
            ("box", None): {"x": 0.12, "y": 0.80, "w": 0.76},
        },
    },
    "C": {
        "nombre": "Superior",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.055, "y": 0.26, "size": 0.075},
            ("text", "subtitle"): {"x": 0.055, "y": 0.335, "size": 0.045},
            ("box", None): {"x": 0.05, "y": 0.60, "w": 0.90},
        },
    },
    "D": {
        "nombre": "Minimalista",
        "campos": {
            ("logo", None): {"x": 0.42, "y": 0.022, "w": 0.16, "h": 0.16},
            ("text", "title"): {"x": 0.06, "y": 0.82, "size": 0.055},
            ("text", "subtitle"): {"x": 0.06, "y": 0.885, "size": 0.032},
            ("box", None): {"x": 0.06, "y": 0.925, "w": 0.55},
        },
    },
    "E": {
        "nombre": "Banda ancha",
        "campos": {
            ("logo", None): {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
            ("text", "title"): {"x": 0.055, "y": 0.74, "size": 0.078},
            ("text", "subtitle"): {"x": 0.055, "y": 0.815, "size": 0.048},
            ("box", None): {"x": 0.05, "y": 0.58, "w": 0.90},
        },
    },
}
