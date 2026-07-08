"""Gestión de fuentes: carga con cache, descarga y fallback del sistema."""

import urllib.request

from PIL import ImageFont

from .constants import FONTS_DIR, FONT_URLS, FALLBACK_FONTS, SYSTEM_FONT_DIRS


def find_system_font(candidates):
    for d in SYSTEM_FONT_DIRS:
        for fname in candidates:
            p = d / fname
            if p.exists():
                return str(p)
    return None


class FontManager:
    """Carga fuentes por rol con cache de instancia y descarga las fuentes de marca."""

    _ROLE_MAP = {
        "title":    ("PlayfairDisplay-Bold.ttf",  FALLBACK_FONTS["title"]),
        "subtitle": ("DancingScript-Regular.ttf", FALLBACK_FONTS["subtitle"]),
        "body":     ("Lato-Regular.ttf",          FALLBACK_FONTS["body"]),
    }

    def __init__(self):
        self._cache = {}

    def load(self, role, size):
        """Carga la fuente del rol (title / subtitle / body) con cache."""
        size = max(6, int(size))
        key = (role, size)
        if key in self._cache:
            return self._cache[key]

        preferred, fallbacks = self._ROLE_MAP[role]

        font = None
        p = FONTS_DIR / preferred
        if p.exists():
            try:
                font = ImageFont.truetype(str(p), size)
            except Exception:
                font = None
        if font is None:
            sf = find_system_font(fallbacks)
            if sf:
                try:
                    font = ImageFont.truetype(sf, size)
                except Exception:
                    font = None
        if font is None:
            font = ImageFont.load_default()

        self._cache[key] = font
        return font

    def download(self, callback=None):
        """Descarga las fuentes que falten, en segundo plano."""
        FONTS_DIR.mkdir(exist_ok=True)
        for fname, url in FONT_URLS.items():
            dest = FONTS_DIR / fname
            if dest.exists() and dest.stat().st_size > 1000:
                continue
            try:
                urllib.request.urlretrieve(url, str(dest))
            except Exception:
                pass
        if callback:
            callback()
