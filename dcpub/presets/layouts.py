"""Layouts de marca predefinidos (A-E): reposicionan logo/título/subtítulo/
caja de una lámina sin tocar su contenido ni la foto de fondo. Ver
docs/superpowers/specs/2026-07-10-fase5-layouts-design.md para el diseño
y docs/superpowers/specs/2026-07-10-fase5-layouts-instructivo-medidas-exactas.md
para las medidas exactas en px (convertidas acá a fracciones de un lienzo
de 1080x1350) y lo que ese instructivo pide pero el editor todavía no
soporta (alineación de texto, degradado, caja de precio, variantes B1/B2)."""

LAYOUTS = {
    "A": {
        "nombre": "Romántico central",
        "campos": {
            ("logo", None): {"x": 0.421, "y": 0.041, "w": 0.157, "h": 0.126},
            ("text", "title"): {"x": 0.093, "y": 0.181, "size": 0.086},
            ("text", "subtitle"): {"x": 0.157, "y": 0.276, "size": 0.050},
            ("box", None): {"x": 0.167, "y": 0.363, "w": 0.667, "size": 0.035},
        },
    },
    "B": {
        "nombre": "Editorial lateral (izquierda)",
        "campos": {
            ("logo", None): {"x": 0.072, "y": 0.046, "w": 0.139, "h": 0.111},
            ("text", "title"): {"x": 0.074, "y": 0.189, "size": 0.079},
            ("text", "subtitle"): {"x": 0.076, "y": 0.356, "size": 0.050},
            ("box", None): {"x": 0.067, "y": 0.463, "w": 0.463, "size": 0.035},
        },
    },
    "C": {
        "nombre": "Funcional familiar",
        "campos": {
            ("logo", None): {"x": 0.431, "y": 0.041, "w": 0.139, "h": 0.111},
            ("text", "title"): {"x": 0.079, "y": 0.181, "size": 0.073},
            ("text", "subtitle"): {"x": 0.079, "y": 0.263, "size": 0.044},
            ("box", None): {"x": 0.074, "y": 0.333, "w": 0.852, "size": 0.035},
        },
    },
    "D": {
        "nombre": "Minimal premium",
        "campos": {
            ("logo", None): {"x": 0.074, "y": 0.048, "w": 0.134, "h": 0.107},
            ("text", "title"): {"x": 0.079, "y": 0.715, "size": 0.076},
            ("text", "subtitle"): {"x": 0.081, "y": 0.800, "size": 0.040},
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
