"""Interfaz gráfica: ventana principal del editor (conectada a Project/Slide/Layer)."""

import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from PIL import Image, ImageTk

from .constants import SCRIPT_DIR, OUTPUT_DIR, ICONS, ELEMENTS, FORMATOS
from .fonts import FontManager
from .models import crear_proyecto_por_defecto
from .render import compose

DARK = "#1e1e1e"
PANEL = "#2a2a2a"
PANEL2 = "#242424"
TEXT = "#e0e0e0"
MUTED = "#9a9a9a"
ACCENT = "#8DC26F"
FIELD = "#333333"

# Rango de los sliders de tamaño por elemento (fracción del ancho)
SIZE_RANGE = {
    "logo":  (0.08, 0.40),
    "title": (0.03, 0.16),
    "sub":   (0.02, 0.10),
    "desc":  (0.015, 0.07),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción"}

HANDLE_SIZE = 5  # medio-lado del cuadradito de cada handle, en px de pantalla
NUDGE_STEP = 0.004        # paso normal (fracción del lienzo)
NUDGE_STEP_SHIFT = 0.02   # paso grande (Shift)
NUDGE_STEP_ALT = 0.001    # paso fino (Alt)
SNAP_THRESHOLD = 8    # px de pantalla
MARGIN_FRAC = 0.055   # margen del lienzo, misma fracción que usa render.py para el título


def _snap_position(new_x0, new_y0, bw, bh, iw, ih):
    """Ajusta (new_x0,new_y0) si el centro o los bordes de la caja arrastrada
    (ancho bw, alto bh) quedan cerca del centro o los márgenes del lienzo
    (iw x ih). Devuelve (new_x0, new_y0, guias), donde guias es una lista
    de ("v"|"h", posición_en_px) a dibujar como líneas guía."""
    guides = []
    margin_x = MARGIN_FRAC * iw
    margin_y = MARGIN_FRAC * ih
    cx, cy = new_x0 + bw / 2, new_y0 + bh / 2

    if abs(cx - iw / 2) <= SNAP_THRESHOLD:
        new_x0 = iw / 2 - bw / 2
        guides.append(("v", iw / 2))
    if abs(cy - ih / 2) <= SNAP_THRESHOLD:
        new_y0 = ih / 2 - bh / 2
        guides.append(("h", ih / 2))

    if abs(new_x0 - margin_x) <= SNAP_THRESHOLD:
        new_x0 = margin_x
        guides.append(("v", margin_x))
    elif abs((new_x0 + bw) - (iw - margin_x)) <= SNAP_THRESHOLD:
        new_x0 = iw - margin_x - bw
        guides.append(("v", iw - margin_x))

    if abs(new_y0 - margin_y) <= SNAP_THRESHOLD:
        new_y0 = margin_y
        guides.append(("h", margin_y))
    elif abs((new_y0 + bh) - (ih - margin_y)) <= SNAP_THRESHOLD:
        new_y0 = ih - margin_y - bh
        guides.append(("h", ih - margin_y))

    return new_x0, new_y0, guides


def _center_position(axis, x0, y0, bw, bh, iw, ih):
    """Centra la caja (esquina x0,y0, ancho bw, alto bh) en el eje pedido
    ("x", "y" o "both") dentro del lienzo (iw x ih). Devuelve (x0, y0)."""
    if axis in ("x", "both"):
        x0 = iw / 2 - bw / 2
    if axis in ("y", "both"):
        y0 = ih / 2 - bh / 2
    return x0, y0


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Generador de Publicaciones — Cabañas Don Cristobal")
        self.configure(bg=DARK)
        self.geometry("1360x820")
        self.minsize(1000, 600)

        self.font_manager = FontManager()

        # Proyecto y lámina activos (modelo formal de dcpub.models)
        self.project = crear_proyecto_por_defecto()
        self.slide = self.project.slides[0]

        # Variables de texto
        self.v_photo = tk.StringVar()
        self.v_title = tk.StringVar(value="Tu título aquí")
        self.v_sub   = tk.StringVar(value="frase secundaria")
        self.v_desc  = tk.StringVar()
        self.v_icon  = tk.StringVar(value="planta")
        self.v_format = tk.StringVar(value=self._format_label_for(self.slide.format))
        self.v_status = tk.StringVar(value="Listo.")
        self.v_readout = tk.StringVar(value="")

        # Variables de sliders {elem: {"size":var,"x":var,"y":var}} (y "photo": zoom/offset_x/offset_y)
        self.ctrl = {}

        # Control interno de render
        self._preview_imgtk = None
        self._render_job = None
        self._updating = False       # evita bucles slider<->drag
        self._drag_elem = None
        self._drag_off = (0, 0)
        self._last_bboxes = {}
        self._img_wh = (0, 0)        # tamaño en px de la imagen mostrada
        self._selected = None        # Layer seleccionada actualmente, o None
        self._handles = {}           # {nombre_handle: (x,y) en px de pantalla}
        self._resize = None          # estado del arrastre de resize en curso, o None
        self._guides = []            # líneas guía activas durante un arrastre, [(tipo,pos_px), ...]

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
        tk.Label(center, textvariable=self.v_readout, bg=DARK, fg=ACCENT,
                 font=("Segoe UI", 9)).pack(anchor="n", pady=(0, 4))

        self.canvas = tk.Canvas(center, bg="#141414", highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>", lambda e: self._schedule_render())

        self._hint_id = self.canvas.create_text(
            10, 10, anchor="nw", fill="#666", font=("Segoe UI", 12),
            text="Elige una foto en el panel izquierdo\ny presiona «Vista previa».")

        for key, dx, dy in [("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)]:
            self.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy, NUDGE_STEP))
            self.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy, NUDGE_STEP_SHIFT))
            self.bind(f"<Alt-{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy, NUDGE_STEP_ALT))

    def _build_left(self, left):
        pad = {"padx": 16}
        tk.Label(left, text="TEXTOS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(16, 10), **pad)

        # Formato
        tk.Label(left, text="🖼  Formato", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", **pad)
        self._formato_labels = [f["label"] for f in FORMATOS] + ["Personalizado…"]
        cb_formato = ttk.Combobox(left, textvariable=self.v_format, values=self._formato_labels,
                                  state="readonly", font=("Segoe UI", 9))
        cb_formato.pack(fill=tk.X, pady=(2, 10), **pad)
        cb_formato.bind("<<ComboboxSelected>>", lambda e: self._on_format_change())

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
        # Contenedor con scroll vertical: en pantallas chicas (notebooks) el
        # panel completo no entra en la altura de la ventana.
        scroll_canvas = tk.Canvas(right, bg=PANEL2, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right, orient="vertical", command=scroll_canvas.yview)
        inner = tk.Frame(scroll_canvas, bg=PANEL2)

        inner_window = scroll_canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<Configure>",
                            lambda e: scroll_canvas.itemconfig(inner_window, width=e.width))
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(_e):
            scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(_e):
            scroll_canvas.unbind_all("<MouseWheel>")

        scroll_canvas.bind("<Enter>", _bind_wheel)
        scroll_canvas.bind("<Leave>", _unbind_wheel)

        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(inner, text="POSICIÓN Y TAMAÑO", bg=PANEL2, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(inner, text="Cada elemento por separado. También puedes\narrastrarlos en la vista previa.",
                 bg=PANEL2, fg=MUTED, font=("Segoe UI", 8), justify="left").pack(
            anchor="w", padx=16, pady=(0, 8))

        self._build_photo_controls(inner)

        for elem in ELEMENTS:
            self._build_control_group(inner, elem)

        tk.Button(inner, text="↺  Restablecer posiciones", bg="#3d3d3d", fg=TEXT,
                  relief="flat", font=("Segoe UI", 9), pady=6,
                  command=self._reset).pack(fill=tk.X, padx=16, pady=(12, 16))

    def _build_photo_controls(self, parent):
        card = tk.Frame(parent, bg=PANEL, padx=12, pady=8)
        card.pack(fill=tk.X, padx=12, pady=5)

        tk.Label(card, text="Foto", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.ctrl["photo"] = {}
        self._slider(card, "photo", "zoom", "Zoom", 1.0, 3.0)
        self._slider(card, "photo", "offset_x", "Posición X del recorte", 0.0, 1.0)
        self._slider(card, "photo", "offset_y", "Posición Y del recorte", 0.0, 1.0)

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
        var = tk.DoubleVar(value=self._get_layer_value(elem, param))
        self.ctrl[elem][param] = var
        tk.Label(parent, text=label, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        s = ttk.Scale(parent, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL,
                      style="Brand.Horizontal.TScale",
                      command=lambda _v, e=elem, p=param: self._on_slider(e, p))
        s.pack(fill=tk.X)

    # ── Puente entre el vocabulario del render y el modelo ─────
    def _layer_by_kind(self, kind):
        """Traduce entre el vocabulario del render ("photo"/"logo"/"title"/"sub"/"desc")
        y los tipos/roles reales de dcpub.models (Layer.type, TextLayer.role)."""
        for layer in self.slide.layers:
            if kind == "photo" and layer.type == "photo":
                return layer
            if kind == "logo" and layer.type == "logo":
                return layer
            if kind == "title" and layer.type == "text" and layer.role == "title":
                return layer
            if kind == "sub" and layer.type == "text" and layer.role == "subtitle":
                return layer
            if kind == "desc" and layer.type == "box":
                return layer
        return None

    def _kind_of(self, layer):
        """Inverso de _layer_by_kind: dado un Layer, devuelve su "kind" de render."""
        for kind in ["photo"] + ELEMENTS:
            if self._layer_by_kind(kind) is layer:
                return kind
        return None

    def _get_layer_value(self, elem, param):
        layer = self._layer_by_kind(elem)
        if elem == "logo" and param == "size":
            return layer.w
        return getattr(layer, param)

    def _set_layer_value(self, elem, param, value):
        layer = self._layer_by_kind(elem)
        if elem == "logo" and param == "size":
            layer.w = value
            layer.h = value
        else:
            setattr(layer, param, value)

    # ── Sincronización slider  →  estado ───────────────────────
    def _on_slider(self, elem, param):
        if self._updating:
            return
        self._set_layer_value(elem, param, float(self.ctrl[elem][param].get()))
        self._schedule_render()

    def _sync_sliders(self):
        """Refleja el estado actual en los sliders sin disparar render."""
        self._updating = True
        for elem in ELEMENTS:
            for param in ("size", "x", "y"):
                self.ctrl[elem][param].set(self._get_layer_value(elem, param))
        for param in ("zoom", "offset_x", "offset_y"):
            self.ctrl["photo"][param].set(self._get_layer_value("photo", param))
        self._updating = False

    def _reset(self):
        self.project = crear_proyecto_por_defecto(self.v_photo.get().strip())
        self.slide = self.project.slides[0]
        self._selected = None
        self._sync_sliders()
        self._schedule_render()

    # ── Selección ──────────────────────────────────────────────
    def _set_selected(self, layer):
        self._selected = layer
        self._render_now()

    def _update_readout(self):
        if self._selected is None:
            self.v_readout.set("")
            return
        layer = self._selected
        kind = self._kind_of(layer)
        tam = layer.w if kind == "logo" else layer.size
        self.v_readout.set(
            f"{LABELS[kind]} · X: {layer.x:.3f}  Y: {layer.y:.3f}  Tamaño: {tam:.3f}")

    def _draw_selection_overlay(self):
        self._handles = {}
        if self._selected is None:
            return
        kind = self._kind_of(self._selected)
        bb = self._last_bboxes.get(kind)
        if not bb:
            return
        ox, oy = self._img_origin
        x0, y0, x1, y1 = bb[0] + ox, bb[1] + oy, bb[2] + ox, bb[3] + oy
        self.canvas.create_rectangle(x0, y0, x1, y1, outline=ACCENT, width=2, dash=(4, 2))

        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        points = {
            "nw": (x0, y0), "n": (mx, y0), "ne": (x1, y0),
            "w": (x0, my), "e": (x1, my),
            "sw": (x0, y1), "s": (mx, y1), "se": (x1, y1),
        }
        for name, (hx, hy) in points.items():
            self.canvas.create_rectangle(
                hx - HANDLE_SIZE, hy - HANDLE_SIZE, hx + HANDLE_SIZE, hy + HANDLE_SIZE,
                fill=ACCENT, outline=DARK)
            self._handles[name] = (hx, hy)

    def _draw_guides(self):
        ox, oy = self._img_origin
        iw, ih = self._img_wh
        for kind, pos in self._guides:
            if kind == "v":
                x = pos + ox
                self.canvas.create_line(x, oy, x, oy + ih, fill=ACCENT, dash=(3, 3))
            else:
                y = pos + oy
                self.canvas.create_line(ox, y, ox + iw, y, fill=ACCENT, dash=(3, 3))

    # ── Resize con handles ──────────────────────────────────────
    def _handle_at(self, cx, cy):
        """Devuelve el nombre del handle bajo el punto de pantalla (cx,cy), o None."""
        for name, (hx, hy) in self._handles.items():
            if abs(cx - hx) <= HANDLE_SIZE + 2 and abs(cy - hy) <= HANDLE_SIZE + 2:
                return name
        return None

    def _start_resize(self, event):
        kind = self._kind_of(self._selected)
        bb = self._last_bboxes.get(kind)
        if not bb:
            return
        x0, y0, x1, y1 = bb
        cx_img, cy_img = (x0 + x1) / 2, (y0 + y1) / 2
        ix, iy = self._canvas_to_img(event.x, event.y)
        start_dist = max(1.0, ((ix - cx_img) ** 2 + (iy - cy_img) ** 2) ** 0.5)
        self._resize = {
            "kind": kind,
            "center": (cx_img, cy_img),
            "start_dist": start_dist,
            "start_value": self._get_layer_value(kind, "size"),
        }

    def _apply_resize(self, event):
        kind = self._resize["kind"]
        cx_img, cy_img = self._resize["center"]
        ix, iy = self._canvas_to_img(event.x, event.y)
        dist = max(1.0, ((ix - cx_img) ** 2 + (iy - cy_img) ** 2) ** 0.5)
        ratio = dist / self._resize["start_dist"]
        smin, smax = SIZE_RANGE[kind]
        new_value = min(smax, max(smin, self._resize["start_value"] * ratio))
        self._set_layer_value(kind, "size", new_value)
        self._sync_sliders()
        self._render_now()

    def _nudge(self, dx_sign, dy_sign, step):
        if self._selected is None:
            return
        if isinstance(self.focus_get(), (tk.Entry, tk.Text)):
            return
        layer = self._selected
        layer.x = min(1.0, max(0.0, layer.x + dx_sign * step))
        layer.y = min(1.0, max(0.0, layer.y + dy_sign * step))
        self._sync_sliders()
        self._render_now()

    # ── Formato ────────────────────────────────────────────────
    def _format_label_for(self, fmt):
        for f in FORMATOS:
            if f["name"] == fmt.get("name"):
                return f["label"]
        return f"{fmt['w']}×{fmt['h']} (personalizado)"

    def _on_format_change(self):
        label = self.v_format.get()
        if label == "Personalizado…":
            w = simpledialog.askinteger("Formato personalizado", "Ancho (px):",
                                         initialvalue=self.slide.format["w"], minvalue=100,
                                         maxvalue=8000, parent=self)
            if not w:
                self._sync_format_label()
                return
            h = simpledialog.askinteger("Formato personalizado", "Alto (px):",
                                         initialvalue=self.slide.format["h"], minvalue=100,
                                         maxvalue=8000, parent=self)
            if not h:
                self._sync_format_label()
                return
            self.slide.format = {"name": "personalizado", "w": w, "h": h}
            self.v_format.set(self._format_label_for(self.slide.format))
        else:
            formato = next(f for f in FORMATOS if f["label"] == label)
            self.slide.format = {"name": formato["name"], "w": formato["w"], "h": formato["h"]}
        self._schedule_render()

    def _sync_format_label(self):
        """Restaura el texto del combobox al formato activo (p.ej. si se cancela el diálogo)."""
        self.v_format.set(self._format_label_for(self.slide.format))

    def _canvas_size_for(self, max_side):
        """Calcula (ancho, alto) en px del lienzo para el formato actual, con el
        lado mayor igual a max_side, manteniendo la proporción del formato."""
        fw, fh = self.slide.format["w"], self.slide.format["h"]
        if fh >= fw:
            h = max_side
            w = max(1, round(max_side * fw / fh))
        else:
            w = max_side
            h = max(1, round(max_side * fh / fw))
        return (w, h)

    # ── Foto ───────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Seleccionar foto",
            initialdir=str(SCRIPT_DIR),
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp"), ("Todos", "*.*")])
        if path:
            self.v_photo.set(path)
            self._layer_by_kind("photo").src = path
            self._schedule_render()

    # ── Capas actuales: adapta el modelo al dict plano que espera render.py ──
    def _build_layers(self):
        layers = []
        for layer in self.slide.layers:
            if not layer.visible:
                continue
            if layer.type == "photo":
                layers.append({"type": "photo", "src": self.v_photo.get().strip(),
                                "zoom": layer.zoom, "offset_x": layer.offset_x,
                                "offset_y": layer.offset_y})
            elif layer.type == "logo":
                layers.append({"type": "logo", "x": layer.x, "y": layer.y, "size": layer.w})
            elif layer.type == "text" and layer.role == "title":
                layers.append({"type": "title", "text": self.txt_title.get("1.0", "end-1c"),
                                "x": layer.x, "y": layer.y, "size": layer.size})
            elif layer.type == "text" and layer.role == "subtitle":
                layers.append({"type": "sub", "text": self.v_sub.get(),
                                "x": layer.x, "y": layer.y, "size": layer.size})
            elif layer.type == "box":
                layers.append({"type": "desc", "text": self.txt_desc.get("1.0", "end-1c"),
                                "icon": self.v_icon.get(), "x": layer.x, "y": layer.y,
                                "size": layer.size})
        return layers

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
        max_side = max(400, min(cw, ch, 1000))
        canvas_size = self._canvas_size_for(max_side)
        try:
            img, bboxes = compose(self._build_layers(), canvas_size, self.font_manager)
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
            self._draw_selection_overlay()
            self._draw_guides()
            self._update_readout()
            self.v_status.set("Vista previa lista.")
        except Exception as e:
            self.v_status.set(f"Error: {e}")

    # ── Arrastre ───────────────────────────────────────────────
    def _canvas_to_img(self, ex, ey):
        ox, oy = getattr(self, "_img_origin", (0, 0))
        return ex - ox, ey - oy

    def _on_press(self, event):
        self._guides = []
        if self._selected is not None:
            handle = self._handle_at(event.x, event.y)
            if handle is not None:
                self._start_resize(event)
                return

        ix, iy = self._canvas_to_img(event.x, event.y)
        for elem in reversed(ELEMENTS):
            layer = self._layer_by_kind(elem)
            if layer is None or layer.locked:
                continue
            bb = self._last_bboxes.get(elem)
            if bb and bb[0] <= ix <= bb[2] and bb[1] <= iy <= bb[3]:
                self._drag_elem = elem
                self._drag_off = (ix - bb[0], iy - bb[1])
                self._set_selected(layer)
                return

        self._drag_elem = None
        photo_layer = self._layer_by_kind("photo")
        bb_photo = self._last_bboxes.get("photo")
        if (photo_layer is not None and not photo_layer.locked and bb_photo
                and bb_photo[0] <= ix <= bb_photo[2] and bb_photo[1] <= iy <= bb_photo[3]):
            self._set_selected(photo_layer)
            return
        self._set_selected(None)

    def _on_drag(self, event):
        if self._resize is not None:
            self._apply_resize(event)
            return
        if not self._drag_elem:
            return
        elem = self._drag_elem
        iw, ih = self._img_wh
        if iw == 0 or ih == 0:
            return
        ix, iy = self._canvas_to_img(event.x, event.y)
        new_x0 = ix - self._drag_off[0]
        new_y0 = iy - self._drag_off[1]

        bb = self._last_bboxes.get(elem)
        bw = (bb[2] - bb[0]) if bb else 0
        bh = (bb[3] - bb[1]) if bb else 0
        new_x0, new_y0, self._guides = _snap_position(new_x0, new_y0, bw, bh, iw, ih)

        layer = self._layer_by_kind(elem)
        if elem == "sub":
            half_w = bw / 2
            cx = new_x0 + half_w
            layer.x = min(1.0, max(0.0, cx / iw))
            layer.y = min(1.0, max(0.0, new_y0 / ih))
        else:
            layer.x = min(1.0, max(0.0, new_x0 / iw))
            layer.y = min(1.0, max(0.0, new_y0 / ih))

        self._sync_sliders()
        self._render_now()

    def _on_release(self, event):
        self._drag_elem = None
        self._resize = None
        self._guides = []
        self._render_now()

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
            max_side = min(max(native, 1200), 2400)
            canvas_size = self._canvas_size_for(max_side)
            img, _ = compose(self._build_layers(), canvas_size, self.font_manager)
            img.convert("RGB").save(str(out_path), quality=95)
            self.v_status.set(f"✅  Guardada en: publicaciones/{out_path.name}")
            messagebox.showinfo("¡Listo!", f"Imagen guardada en:\n{out_path}")
        except Exception as e:
            self.v_status.set(f"Error: {e}")
            messagebox.showerror("Error al generar", str(e))
