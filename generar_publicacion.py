"""
╔══════════════════════════════════════════════════════════════╗
║   GENERADOR DE PUBLICACIONES - Cabañas Don Cristobal         ║
║   Versión 2.0  ·  Vista previa interactiva (arrastrable)     ║
╚══════════════════════════════════════════════════════════════╝

REQUISITOS (se instalan solos la primera vez):
    pip install pillow requests

CÓMO USAR:
    1. Deja este script en la misma carpeta que tus fotos y el
       archivo "logo-sin-fondo.png" (logo con fondo transparente).
    2. Ejecuta:  python generar_publicacion.py
    3. Panel izquierdo  → escribe los textos y elige la foto.
    4. Panel central    → ARRASTRA con el mouse el logo, el título,
                          el subtítulo o el recuadro para moverlos.
    5. Panel derecho    → ajusta tamaño y posición X/Y de cada elemento.
    6. "Generar y guardar" → crea la imagen en alta resolución dentro
                             de la subcarpeta "publicaciones/".
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import urllib.request
import threading

# ── Instalar / importar Pillow automáticamente ──────────────────
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont, ImageTk


# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE MARCA
# ═══════════════════════════════════════════════════════════════

VERDE     = (141, 194, 111)     # verde lima de la marca  (#8DC26F)
BLANCO    = (255, 255, 255)
BOX_COLOR = (40, 25, 15, 215)   # recuadro inferior marrón oscuro semitransp.

SCRIPT_DIR = Path(__file__).parent
FONTS_DIR  = SCRIPT_DIR / "fonts"
OUTPUT_DIR = SCRIPT_DIR / "publicaciones"
LOGO_FILE  = SCRIPT_DIR / "logo-sin-fondo.png"

# Fuentes a descargar (Google Fonts · licencia OFL, uso libre)
FONT_URLS = {
    "PlayfairDisplay-Bold.ttf":
        "https://fonts.gstatic.com/s/playfairdisplay/v37/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKd.ttf",
    "DancingScript-Regular.ttf":
        "https://fonts.gstatic.com/s/dancingscript/v25/If2cXTr6YS-zF4S-kcSWSVi_sxjsohD9F50Ruu7BMSo3ROp6.ttf",
    "Lato-Regular.ttf":
        "https://fonts.gstatic.com/s/lato/v24/S6uyw4BMUTPHjx4wWw.ttf",
}

# Fuentes de respaldo del sistema (Windows / Mac / Linux)
FALLBACK_FONTS = {
    "title":    ["georgiab.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"],
    "subtitle": ["segoesc.ttf",  "Brush Script MT.ttf", "Comic Sans MS.ttf", "DejaVuSerif-Italic.ttf"],
    "body":     ["calibri.ttf",  "Helvetica.ttf", "Arial.ttf", "DejaVuSans.ttf"],
}

SYSTEM_FONT_DIRS = [
    Path("C:/Windows/Fonts"),
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/System/Library/Fonts"),
]

ICONS = ["planta", "montaña", "corazón", "cabaña", "ninguno"]

# Orden de dibujo / prioridad de arrastre (los últimos quedan "encima")
ELEMENTS = ["logo", "title", "sub", "desc"]

_font_cache = {}


# ═══════════════════════════════════════════════════════════════
# FUENTES
# ═══════════════════════════════════════════════════════════════

def find_system_font(candidates):
    for d in SYSTEM_FONT_DIRS:
        for fname in candidates:
            p = d / fname
            if p.exists():
                return str(p)
    return None


def load_font(role, size):
    """Carga la fuente del rol (title / subtitle / body) con cache."""
    size = max(6, int(size))
    key = (role, size)
    if key in _font_cache:
        return _font_cache[key]

    mapping = {
        "title":    ("PlayfairDisplay-Bold.ttf",  FALLBACK_FONTS["title"]),
        "subtitle": ("DancingScript-Regular.ttf", FALLBACK_FONTS["subtitle"]),
        "body":     ("Lato-Regular.ttf",          FALLBACK_FONTS["body"]),
    }
    preferred, fallbacks = mapping[role]

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

    _font_cache[key] = font
    return font


def download_fonts(callback=None):
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


# ═══════════════════════════════════════════════════════════════
# ÍCONOS (dibujados a mano, se ven nítidos a cualquier tamaño)
# ═══════════════════════════════════════════════════════════════

def draw_icon(draw, x, y, size, icon_type, color):
    lw = max(2, size // 16)
    cx, cy = x + size // 2, y + size // 2
    r = size // 2 - lw * 2

    if icon_type == "planta":
        draw.line([(cx, cy + r), (cx, cy - r // 2)], fill=color, width=lw)
        draw.arc([(cx - r // 2, cy - r // 2), (cx + lw, cy + lw)], 180, 270, fill=color, width=lw)
        draw.arc([(cx - lw, cy - r // 2), (cx + r // 2, cy + lw)], 270, 360, fill=color, width=lw)

    elif icon_type == "montaña":
        pts1 = [(cx - r, cy + r), (cx, cy - r), (cx + r, cy + r)]
        for i in range(len(pts1)):
            draw.line([pts1[i], pts1[(i + 1) % len(pts1)]], fill=color, width=lw)
        pts2 = [(cx, cy + r), (cx + r * 2 // 3, cy - r // 2), (cx + r, cy + r)]
        for i in range(len(pts2)):
            draw.line([pts2[i], pts2[(i + 1) % len(pts2)]], fill=color, width=lw)

    elif icon_type == "corazón":
        hr = r // 2
        draw.arc([(cx - r, cy - hr), (cx, cy + hr)], 180, 360, fill=color, width=lw)
        draw.arc([(cx, cy - hr), (cx + r, cy + hr)], 180, 360, fill=color, width=lw)
        draw.line([(cx - r, cy + hr), (cx, cy + r * 3 // 2)], fill=color, width=lw)
        draw.line([(cx + r, cy + hr), (cx, cy + r * 3 // 2)], fill=color, width=lw)

    elif icon_type == "cabaña":
        draw.polygon([(cx - r, cy), (cx, cy - r), (cx + r, cy)], outline=color, width=lw)
        hw = r * 2 // 3
        draw.rectangle([(cx - hw, cy), (cx + hw, cy + r)], outline=color, width=lw)
        pw = hw // 2
        draw.rectangle([(cx - pw // 2, cy + r // 2), (cx + pw // 2, cy + r)], outline=color, width=lw)


# ═══════════════════════════════════════════════════════════════
# COMPOSICIÓN DE IMAGEN
# ═══════════════════════════════════════════════════════════════

def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bx = draw.textbbox((0, 0), test, font=font)
        if bx[2] - bx[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


# Cache del fondo (foto + gradiente) para que arrastrar sea fluido
_bg_cache = {"key": None, "img": None}


def _get_background(photo_path, size):
    """Devuelve la foto escalada con el gradiente inferior aplicado (cacheado)."""
    key = (str(photo_path), size)
    if _bg_cache["key"] == key:
        return _bg_cache["img"].copy()

    photo = Image.open(photo_path).convert("RGBA")
    W, H = photo.size
    scale = size / max(W, H)
    W2, H2 = max(1, int(W * scale)), max(1, int(H * scale))
    photo = photo.resize((W2, H2), Image.LANCZOS)
    W, H = W2, H2

    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    start = int(H * 0.34)
    for y in range(start, H):
        a = int(150 * min(1.0, (y - start) / max(1, (H - start))))
        gd.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    photo = Image.alpha_composite(photo, grad)

    _bg_cache["key"] = key
    _bg_cache["img"] = photo
    return photo.copy()


def compose(photo_path, texts, elements, size):
    """
    Compone la publicación.

    texts    : {"title","subtitle","description","icon"}
    elements : {elem: {"x","y","size"}}  posiciones y tamaños en FRACCIONES.
               - logo  : x,y = esquina sup-izq;  size = diámetro (frac. de ancho)
               - title : x,y = esquina sup-izq;  size = alto de fuente (frac. ancho)
               - sub   : x   = centro horizontal; y = tope;  size = fuente
               - desc  : x,y = esquina sup-izq del recuadro; size = fuente
    size     : lado mayor de la imagen renderizada (px)

    Devuelve (imagen RGBA, bboxes) donde bboxes[elem] = (x0,y0,x1,y1) en px.
    """
    canvas = _get_background(photo_path, size)
    W, H = canvas.size
    draw = ImageDraw.Draw(canvas)
    bboxes = {}

    margin = int(W * 0.055)

    # ── LOGO ────────────────────────────────────────────────────
    if LOGO_FILE.exists():
        lsz = max(20, int(W * elements["logo"]["size"]))
        try:
            logo = Image.open(str(LOGO_FILE)).convert("RGBA").resize((lsz, lsz), Image.LANCZOS)
            lx = int(elements["logo"]["x"] * W)
            ly = int(elements["logo"]["y"] * H)
            canvas.alpha_composite(logo, (lx, ly))
            bboxes["logo"] = (lx, ly, lx + lsz, ly + lsz)
        except Exception:
            pass

    # ── TÍTULO ──────────────────────────────────────────────────
    title = texts["title"]
    if title.strip():
        tsz = max(10, int(W * elements["title"]["size"]))
        font_t = load_font("title", tsz)
        tx = int(elements["title"]["x"] * W)
        ty = int(elements["title"]["y"] * H)
        max_w = W - tx - margin
        lines = []
        for part in title.split("\n"):
            part = part.strip()
            if part:
                lines += wrap_text(part, font_t, max_w, draw)
        lh = int(tsz * 1.22)
        widest = 0
        for i, line in enumerate(lines):
            yy = ty + i * lh
            draw.text((tx + 3, yy + 3), line, font=font_t, fill=(0, 0, 0, 160))   # sombra
            draw.text((tx, yy), line, font=font_t, fill=BLANCO + (255,))
            bb = draw.textbbox((tx, yy), line, font=font_t)
            widest = max(widest, bb[2] - tx)
        bboxes["title"] = (tx, ty, tx + max(widest, 10), ty + max(1, len(lines)) * lh)

    # ── SUBTÍTULO (cursiva verde, flanqueado por líneas) ────────
    subtitle = texts["subtitle"]
    if subtitle.strip():
        ssz = max(8, int(W * elements["sub"]["size"]))
        font_s = load_font("subtitle", ssz)
        cx = int(elements["sub"]["x"] * W)
        sy = int(elements["sub"]["y"] * H)
        bb = draw.textbbox((0, 0), subtitle, font=font_s)
        sw, sh = bb[2] - bb[0], bb[3] - bb[1]
        sx = cx - sw // 2
        ly = sy + sh // 2
        lw_deco = max(2, int(W * 0.003))
        line_len = int(W * 0.11)
        gap = int(W * 0.03)
        # línea izquierda
        lx1 = max(0, sx - gap - line_len)
        draw.line([(lx1, ly), (sx - gap, ly)], fill=VERDE, width=lw_deco)
        # línea derecha
        rx2 = min(W, sx + sw + gap + line_len)
        draw.line([(sx + sw + gap, ly), (rx2, ly)], fill=VERDE, width=lw_deco)
        # texto con sombra
        draw.text((sx + 2, sy + 2), subtitle, font=font_s, fill=(0, 0, 0, 130))
        draw.text((sx, sy), subtitle, font=font_s, fill=VERDE)
        bboxes["sub"] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)

    # ── RECUADRO DE DESCRIPCIÓN ─────────────────────────────────
    description = texts["description"]
    if description.strip():
        bsz = max(8, int(W * elements["desc"]["size"]))
        font_b = load_font("body", bsz)
        box_w = int(W * 0.90)
        bx = int(elements["desc"]["x"] * W)
        by = int(elements["desc"]["y"] * H)
        bx = max(0, min(bx, W - box_w))
        corner_r = int(W * 0.033)
        pad = int(W * 0.04)

        icon = texts["icon"]
        icon_sz = max(24, int(W * 0.065))
        if icon != "ninguno":
            text_x = bx + pad + icon_sz + pad
        else:
            text_x = bx + pad * 2
        text_w = (bx + box_w) - text_x - pad
        dlines = wrap_text(description, font_b, max(10, text_w), draw)
        dlh = int(bsz * 1.48)
        text_h = len(dlines) * dlh
        box_h = max(text_h + pad, icon_sz + pad) + int(H * 0.010)

        box_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box_layer)
        bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                             radius=corner_r, fill=BOX_COLOR)
        canvas = Image.alpha_composite(canvas, box_layer)
        draw = ImageDraw.Draw(canvas)

        if icon != "ninguno":
            iy = by + (box_h - icon_sz) // 2
            draw_icon(draw, bx + pad, iy, icon_sz, icon, VERDE)

        dy = by + (box_h - text_h) // 2
        for i, l in enumerate(dlines):
            draw.text((text_x, dy + i * dlh), l, font=font_b, fill=BLANCO + (255,))

        bboxes["desc"] = (bx, by, bx + box_w, by + box_h)

    return canvas, bboxes


# ═══════════════════════════════════════════════════════════════
# INTERFAZ GRÁFICA
# ═══════════════════════════════════════════════════════════════

DARK   = "#1e1e1e"
PANEL  = "#2a2a2a"
PANEL2 = "#242424"
TEXT   = "#e0e0e0"
MUTED  = "#9a9a9a"
ACCENT = "#8DC26F"
FIELD  = "#333333"

# Valores por defecto de cada elemento (fracciones)
DEFAULTS = {
    "logo":  {"x": 0.40,  "y": 0.022, "size": 0.20},
    "title": {"x": 0.055, "y": 0.42,  "size": 0.087},
    "sub":   {"x": 0.50,  "y": 0.55,  "size": 0.050},
    "desc":  {"x": 0.05,  "y": 0.808, "size": 0.033},
}

# Rango de los sliders de tamaño por elemento (fracción del ancho)
SIZE_RANGE = {
    "logo":  (0.08, 0.40),
    "title": (0.03, 0.16),
    "sub":   (0.02, 0.10),
    "desc":  (0.015, 0.07),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generador de Publicaciones — Cabañas Don Cristobal")
        self.configure(bg=DARK)
        self.geometry("1360x820")
        self.minsize(1100, 700)

        # Estado de los elementos (copia de los defaults)
        self.el = {k: dict(v) for k, v in DEFAULTS.items()}

        # Variables de texto
        self.v_photo = tk.StringVar()
        self.v_title = tk.StringVar(value="Tu título aquí")
        self.v_sub   = tk.StringVar(value="frase secundaria")
        self.v_desc  = tk.StringVar()
        self.v_icon  = tk.StringVar(value="planta")
        self.v_status = tk.StringVar(value="Listo.")

        # Variables de sliders {elem: {"size":var,"x":var,"y":var}}
        self.ctrl = {}

        # Control interno de render
        self._preview_imgtk = None
        self._render_job = None
        self._updating = False       # evita bucles slider<->drag
        self._drag_elem = None
        self._drag_off = (0, 0)
        self._last_bboxes = {}
        self._canvas_img_id = None
        self._img_wh = (0, 0)        # tamaño en px de la imagen mostrada

        self._build_ui()

        # Descargar fuentes en segundo plano
        self.v_status.set("Descargando fuentes… (solo la primera vez)")
        threading.Thread(
            target=download_fonts,
            args=(lambda: self.v_status.set("Fuentes listas."),),
            daemon=True,
        ).start()

    # ── Construcción de la UI ──────────────────────────────────
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, arrowcolor=TEXT)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)])
        style.configure("Brand.Horizontal.TScale", background=PANEL2, troughcolor=FIELD)

        # ── PANEL IZQUIERDO: textos ──────────────────────────
        left = tk.Frame(self, bg=PANEL, width=290)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        self._build_left(left)

        # ── PANEL DERECHO: controles por elemento ────────────
        right = tk.Frame(self, bg=PANEL2, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        self._build_right(right)

        # ── PANEL CENTRAL: vista previa (grande) ─────────────
        center = tk.Frame(self, bg=DARK)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(center, text="Vista previa · arrastra los elementos con el mouse",
                 bg=DARK, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="n", pady=(8, 4))

        self.canvas = tk.Canvas(center, bg="#141414", highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>", lambda e: self._schedule_render())

        self._hint_id = self.canvas.create_text(
            10, 10, anchor="nw", fill="#666", font=("Segoe UI", 12),
            text="Elige una foto en el panel izquierdo\ny presiona «Vista previa».")

    def _build_left(self, left):
        pad = {"padx": 16}
        tk.Label(left, text="TEXTOS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(16, 10), **pad)

        # Foto
        tk.Label(left, text="📷  Foto", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", **pad)
        row = tk.Frame(left, bg=PANEL)
        row.pack(fill=tk.X, pady=(2, 8), **pad)
        tk.Entry(row, textvariable=self.v_photo, bg=FIELD, fg=TEXT,
                 insertbackground="white", relief="flat", bd=4,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(row, text="…", bg="#3d3d3d", fg=TEXT, relief="flat", padx=8,
                  command=self._browse).pack(side=tk.LEFT, padx=(4, 0))

        # Título (multilínea)
        tk.Label(left, text="✏️  Título  (Enter = salto de línea)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self.txt_title = tk.Text(left, height=3, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                 font=("Segoe UI", 10), relief="flat", bd=4, wrap="word")
        self.txt_title.insert("1.0", self.v_title.get())
        self.txt_title.pack(fill=tk.X, pady=(0, 8), **pad)
        self.txt_title.bind("<KeyRelease>", lambda e: self._schedule_render())

        # Subtítulo
        tk.Label(left, text="✨  Subtítulo (cursiva verde)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        e_sub = tk.Entry(left, textvariable=self.v_sub, bg=FIELD, fg=TEXT,
                         insertbackground="white", relief="flat", bd=4, font=("Segoe UI", 10))
        e_sub.pack(fill=tk.X, pady=(0, 8), **pad)
        e_sub.bind("<KeyRelease>", lambda e: self._schedule_render())

        # Descripción
        tk.Label(left, text="📝  Descripción (recuadro inferior)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self.txt_desc = tk.Text(left, height=4, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                font=("Segoe UI", 10), relief="flat", bd=4, wrap="word")
        self.txt_desc.pack(fill=tk.X, pady=(0, 8), **pad)
        self.txt_desc.bind("<KeyRelease>", lambda e: self._schedule_render())

        # Ícono
        tk.Label(left, text="🔖  Ícono del recuadro", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        cb = ttk.Combobox(left, textvariable=self.v_icon, values=ICONS,
                          state="readonly", font=("Segoe UI", 10))
        cb.pack(fill=tk.X, pady=(0, 10), **pad)
        cb.bind("<<ComboboxSelected>>", lambda e: self._schedule_render())

        # Botones
        tk.Button(left, text="👁  Vista previa", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 10), pady=8, command=self._render_now).pack(
            fill=tk.X, pady=(6, 4), **pad)
        tk.Button(left, text="💾  Generar y guardar", bg=ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 11, "bold"), pady=9, command=self._generate).pack(
            fill=tk.X, pady=(0, 6), **pad)

        tk.Label(left, textvariable=self.v_status, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9), wraplength=250, justify="left").pack(
            anchor="w", pady=(6, 12), **pad)

    def _build_right(self, right):
        tk.Label(right, text="POSICIÓN Y TAMAÑO", bg=PANEL2, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(right, text="Cada elemento por separado. También puedes\narrastrarlos en la vista previa.",
                 bg=PANEL2, fg=MUTED, font=("Segoe UI", 8), justify="left").pack(
            anchor="w", padx=16, pady=(0, 8))

        for elem in ELEMENTS:
            self._build_control_group(right, elem)

        tk.Button(right, text="↺  Restablecer posiciones", bg="#3d3d3d", fg=TEXT,
                  relief="flat", font=("Segoe UI", 9), pady=6,
                  command=self._reset).pack(fill=tk.X, padx=16, pady=(12, 16))

    def _build_control_group(self, parent, elem):
        card = tk.Frame(parent, bg=PANEL, padx=12, pady=8)
        card.pack(fill=tk.X, padx=12, pady=5)

        tk.Label(card, text=LABELS[elem], bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.ctrl[elem] = {}
        smin, smax = SIZE_RANGE[elem]
        size_label = "Tamaño del logo" if elem == "logo" else "Tamaño de fuente"
        self._slider(card, elem, "size", size_label, smin, smax)
        self._slider(card, elem, "x", "Posición X", 0.0, 1.0)
        self._slider(card, elem, "y", "Posición Y", 0.0, 1.0)

    def _slider(self, parent, elem, param, label, lo, hi):
        var = tk.DoubleVar(value=self.el[elem][param])
        self.ctrl[elem][param] = var
        tk.Label(parent, text=label, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        s = ttk.Scale(parent, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL,
                      style="Brand.Horizontal.TScale",
                      command=lambda _v, e=elem, p=param: self._on_slider(e, p))
        s.pack(fill=tk.X)

    # ── Sincronización slider  →  estado ───────────────────────
    def _on_slider(self, elem, param):
        if self._updating:
            return
        self.el[elem][param] = float(self.ctrl[elem][param].get())
        self._schedule_render()

    def _sync_sliders(self):
        """Refleja el estado actual en los sliders sin disparar render."""
        self._updating = True
        for elem in ELEMENTS:
            for param in ("size", "x", "y"):
                self.ctrl[elem][param].set(self.el[elem][param])
        self._updating = False

    def _reset(self):
        self.el = {k: dict(v) for k, v in DEFAULTS.items()}
        self._sync_sliders()
        self._schedule_render()

    # ── Foto ───────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Seleccionar foto",
            initialdir=str(SCRIPT_DIR),
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")])
        if path:
            self.v_photo.set(path)
            self._schedule_render()

    # ── Textos actuales ────────────────────────────────────────
    def _texts(self):
        return {
            "title":       self.txt_title.get("1.0", "end-1c"),
            "subtitle":    self.v_sub.get(),
            "description": self.txt_desc.get("1.0", "end-1c"),
            "icon":        self.v_icon.get(),
        }

    # ── Render con debounce ────────────────────────────────────
    def _schedule_render(self, delay=50):
        if self._render_job is not None:
            self.after_cancel(self._render_job)
        self._render_job = self.after(delay, self._render_now)

    def _render_now(self):
        self._render_job = None
        path = self.v_photo.get().strip()
        if not path or not Path(path).exists():
            return
        cw = max(200, self.canvas.winfo_width())
        ch = max(200, self.canvas.winfo_height())
        # tamaño de render: cabe en el canvas, con un mínimo razonable
        size = max(400, min(cw, ch, 1000))
        try:
            img, bboxes = compose(path, self._texts(), self.el, size)
            # Ajustar a canvas manteniendo proporción
            iw, ih = img.size
            fit = min(cw / iw, ch / ih, 1.0)
            if fit < 1.0:
                img = img.resize((max(1, int(iw * fit)), max(1, int(ih * fit))), Image.LANCZOS)
                bboxes = {k: tuple(c * fit for c in v) for k, v in bboxes.items()}
            self._img_wh = img.size
            self._last_bboxes = bboxes
            self._preview_imgtk = ImageTk.PhotoImage(img.convert("RGB"))

            self.canvas.delete("all")
            x0 = (cw - img.size[0]) // 2
            y0 = (ch - img.size[1]) // 2
            self._img_origin = (x0, y0)
            self.canvas.create_image(x0, y0, anchor="nw", image=self._preview_imgtk)
            self.v_status.set("Vista previa lista.")
        except Exception as e:
            self.v_status.set(f"Error: {e}")

    # ── Arrastre ───────────────────────────────────────────────
    def _canvas_to_img(self, ex, ey):
        ox, oy = getattr(self, "_img_origin", (0, 0))
        return ex - ox, ey - oy

    def _on_press(self, event):
        ix, iy = self._canvas_to_img(event.x, event.y)
        # prioridad inversa: los de encima primero
        for elem in reversed(ELEMENTS):
            bb = self._last_bboxes.get(elem)
            if bb and bb[0] <= ix <= bb[2] and bb[1] <= iy <= bb[3]:
                self._drag_elem = elem
                self._drag_off = (ix - bb[0], iy - bb[1])
                return

    def _on_drag(self, event):
        if not self._drag_elem:
            return
        elem = self._drag_elem
        iw, ih = self._img_wh
        if iw == 0 or ih == 0:
            return
        ix, iy = self._canvas_to_img(event.x, event.y)
        # nueva esquina superior-izquierda del bbox
        new_x0 = ix - self._drag_off[0]
        new_y0 = iy - self._drag_off[1]

        if elem == "sub":
            # 'x' del subtítulo es su centro
            bb = self._last_bboxes.get("sub")
            half_w = (bb[2] - bb[0]) / 2 if bb else 0
            cx = new_x0 + half_w
            self.el["sub"]["x"] = min(1.0, max(0.0, cx / iw))
            self.el["sub"]["y"] = min(1.0, max(0.0, new_y0 / ih))
        else:
            self.el[elem]["x"] = min(1.0, max(0.0, new_x0 / iw))
            self.el[elem]["y"] = min(1.0, max(0.0, new_y0 / ih))

        self._sync_sliders()
        self._render_now()

    def _on_release(self, event):
        self._drag_elem = None

    # ── Generar en alta resolución ─────────────────────────────
    def _generate(self):
        path = self.v_photo.get().strip()
        if not path:
            messagebox.showerror("Error", "Selecciona una foto primero.")
            return
        if not Path(path).exists():
            messagebox.showerror("Error", f"No se encontró la foto:\n{path}")
            return

        OUTPUT_DIR.mkdir(exist_ok=True)
        src = Path(path)
        out_path = OUTPUT_DIR / (src.stem + "_publicacion.jpg")

        self.v_status.set("Generando imagen en alta resolución…")
        self.update()
        try:
            # Resolución nativa de la foto (lado mayor), tope 2400 px
            with Image.open(path) as im:
                native = max(im.size)
            full = min(max(native, 1200), 2400)
            img, _ = compose(path, self._texts(), self.el, full)
            img.convert("RGB").save(str(out_path), quality=95)
            self.v_status.set(f"✅  Guardada en: publicaciones/{out_path.name}")
            messagebox.showinfo("¡Listo!",
                                f"Imagen guardada en:\n{out_path}")
        except Exception as e:
            self.v_status.set(f"Error: {e}")
            messagebox.showerror("Error al generar", str(e))


# ═══════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    App().mainloop()
# fin
