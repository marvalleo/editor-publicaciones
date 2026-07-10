"""Constantes de marca, rutas y configuración compartida por el paquete dcpub."""

from pathlib import Path

VERDE = (141, 194, 111)       # verde lima de la marca (#8DC26F)
BLANCO = (247, 241, 232)      # blanco crema de la marca (#F7F1E8)
BOX_COLOR = (40, 25, 15, 215)  # recuadro inferior marrón oscuro semitransparente
TEXT_STROKE_COLOR = (20, 12, 8, 255)  # contorno de texto, fijo (no configurable)

PACKAGE_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = PACKAGE_DIR.parent
FONTS_DIR = SCRIPT_DIR / "fonts"
OUTPUT_DIR = SCRIPT_DIR / "publicaciones"
LOGO_FILE = SCRIPT_DIR / "logo-sin-fondo.png"

FONT_URLS = {
    "PlayfairDisplay-Bold.ttf":
        "https://fonts.gstatic.com/s/playfairdisplay/v37/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKd.ttf",
    "DancingScript-Regular.ttf":
        "https://fonts.gstatic.com/s/dancingscript/v25/If2cXTr6YS-zF4S-kcSWSVi_sxjsohD9F50Ruu7BMSo3ROp6.ttf",
    "Lato-Regular.ttf":
        "https://fonts.gstatic.com/s/lato/v24/S6uyw4BMUTPHjx4wWw.ttf",
}

FALLBACK_FONTS = {
    "title":    ["georgiab.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"],
    "subtitle": ["segoesc.ttf",  "Brush Script MT.ttf", "Comic Sans MS.ttf", "DejaVuSerif-Italic.ttf"],
    "body":     ["calibri.ttf",  "Helvetica.ttf", "Arial.ttf", "DejaVuSans.ttf"],
}

FAMILY_FONT_FILES = {
    "playfair": "PlayfairDisplay-Bold.ttf",
    "dancing": "DancingScript-Regular.ttf",
    "lato": "Lato-Regular.ttf",
}

SYSTEM_FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/System/Library/Fonts"),
]

ICONS = ["planta", "montaña", "corazón", "cabaña", "ninguno"]

ELEMENTS = ["logo", "title", "sub", "desc"]

FORMATOS = [
    {"name": "feed_4x5", "label": "1080×1350 (4:5)", "w": 1080, "h": 1350},
    {"name": "feed_3x4", "label": "1080×1440 (3:4)", "w": 1080, "h": 1440},
    {"name": "story_9x16", "label": "1080×1920 (9:16)", "w": 1080, "h": 1920},
]
