"""Interfaz gráfica: ventana principal del editor (portada de v2.0)."""

import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from .constants import SCRIPT_DIR, OUTPUT_DIR, ICONS, ELEMENTS
from .fonts import FontManager
from .render import compose

DARK = "#1e1e1e"
PANEL = "#2a2a2a"
PANEL2 = "#242424"
TEXT = "#e0e0e0"
MUTED = "#9a9a9a"
ACCENT = "#8DC26F"
FIELD = "#333333"

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

        self.font_manager = FontManager()

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
            target=self.font_manager.download,
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

        left = tk.Frame(self, bg=PANEL, width=290)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        self._build_left(left)

        right = tk.Frame(self, bg=PANEL2, width=300)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        self._build_right(right)

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

        tk.Label(left, text="📷  Foto", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", **pad)
        row = tk.Frame(left, bg=PANEL)
        row.pack(fill=tk.X, pady=(2, 8), **pad)
        tk.Entry(row, textvariable=self.v_photo, bg=FIELD, fg=TEXT,
                 insertbackground="white", relief="flat", bd=4,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(row, text="…", bg="#3d3d3d", fg=TEXT, relief="flat", padx=8,
                  command=self._browse).pack(side=tk.LEFT, padx=(4, 0))

        tk.Label(left, text="✏️  Título  (Enter = salto de línea)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self.txt_title = tk.Text(left, height=3, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                 font=("Segoe UI", 10), relief="flat", bd=4, wrap="word")
        self.txt_title.insert("1.0", self.v_title.get())
        self.txt_title.pack(fill=tk.X, pady=(0, 8), **pad)
        self.txt_title.bind("<KeyRelease>", lambda e: self._schedule_render())

        tk.Label(left, text="✨  Subtítulo (cursiva verde)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        e_sub = tk.Entry(left, textvariable=self.v_sub, bg=FIELD, fg=TEXT,
                         insertbackground="white", relief="flat", bd=4, font=("Segoe UI", 10))
        e_sub.pack(fill=tk.X, pady=(0, 8), **pad)
        e_sub.bind("<KeyRelease>", lambda e: self._schedule_render())

        tk.Label(left, text="📝  Descripción (recuadro inferior)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self.txt_desc = tk.Text(left, height=4, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                font=("Segoe UI", 10), relief="flat", bd=4, wrap="word")
        self.txt_desc.pack(fill=tk.X, pady=(0, 8), **pad)
        self.txt_desc.bind("<KeyRelease>", lambda e: self._schedule_render())

        tk.Label(left, text="🔖  Ícono del recuadro", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        cb = ttk.Combobox(left, textvariable=self.v_icon, values=ICONS,
                          state="readonly", font=("Segoe UI", 10))
        cb.pack(fill=tk.X, pady=(0, 10), **pad)
        cb.bind("<<ComboboxSelected>>", lambda e: self._schedule_render())

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

    # ── Capas actuales (Fase 1.1: dicts; Fase 1.2 las formaliza como Layer) ──
    def _build_layers(self):
        return [
            {"type": "logo", **self.el["logo"]},
            {"type": "title", "text": self.txt_title.get("1.0", "end-1c"), **self.el["title"]},
            {"type": "sub", "text": self.v_sub.get(), **self.el["sub"]},
            {"type": "desc", "text": self.txt_desc.get("1.0", "end-1c"),
             "icon": self.v_icon.get(), **self.el["desc"]},
        ]

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
        size = max(400, min(cw, ch, 1000))
        try:
            img, bboxes = compose(path, self._build_layers(), size, self.font_manager)
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
        new_x0 = ix - self._drag_off[0]
        new_y0 = iy - self._drag_off[1]

        if elem == "sub":
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
            with Image.open(path) as im:
                native = max(im.size)
            full = min(max(native, 1200), 2400)
            img, _ = compose(path, self._build_layers(), full, self.font_manager)
            img.convert("RGB").save(str(out_path), quality=95)
            self.v_status.set(f"✅  Guardada en: publicaciones/{out_path.name}")
            messagebox.showinfo("¡Listo!", f"Imagen guardada en:\n{out_path}")
        except Exception as e:
            self.v_status.set(f"Error: {e}")
            messagebox.showerror("Error al generar", str(e))
