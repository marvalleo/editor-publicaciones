"""Interfaz gráfica: ventana principal del editor (conectada a Project/Slide/Layer)."""

import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from PIL import Image, ImageTk

from .constants import SCRIPT_DIR, OUTPUT_DIR, ICONS, ELEMENTS, FORMATOS, LOGO_FILE
from .fonts import FontManager
from .models import crear_proyecto_por_defecto, _short_id
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
    "cta":   (0.015, 0.07),
    "free":  (0.02, 0.12),
}

LABELS = {"logo": "Logo", "title": "Título", "sub": "Subtítulo", "desc": "Descripción",
          "cta": "CTA", "line": "Línea", "dots": "Puntos", "free": "Texto"}

# Rangos de los ajustes fotográficos, alineados a los clamps de render.py
ADJUST_RANGE = {
    "brightness": (0.0, 2.0),
    "contrast": (0.0, 2.0),
    "saturation": (0.0, 2.0),
    "warmth": (-1.0, 1.0),
    "sharpness": (0.0, 2.0),
    "shadows": (-1.0, 1.0),
    "vignette": (0.0, 1.0),
}

ADJUST_LABELS = {
    "brightness": "Brillo",
    "contrast": "Contraste",
    "saturation": "Saturación",
    "warmth": "Calidez",
    "sharpness": "Nitidez",
    "shadows": "Sombras",
    "vignette": "Viñeta",
}

OVERLAY_STRENGTH_RANGE = (0.0, 1.0)

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


def _offset_delta_for_drag(dx_img, dy_img, excess_x, excess_y):
    """Traduce un desplazamiento de mouse (dx_img, dy_img) en px de la
    imagen de preview a un delta de (offset_x, offset_y) fraccional de la
    foto. Arrastrar a la derecha/abajo debe revelar contenido a la
    izquierda/arriba (como panear un mapa), de ahí el signo negativo."""
    d_ox = (-dx_img / excess_x) if excess_x > 0 else 0.0
    d_oy = (-dy_img / excess_y) if excess_y > 0 else 0.0
    return d_ox, d_oy


def _center_position(axis, x0, y0, bw, bh, iw, ih):
    """Centra la caja (esquina x0,y0, ancho bw, alto bh) en el eje pedido
    ("x", "y" o "both") dentro del lienzo (iw x ih). Devuelve (x0, y0)."""
    if axis in ("x", "both"):
        x0 = iw / 2 - bw / 2
    if axis in ("y", "both"):
        y0 = ih / 2 - bh / 2
    return x0, y0


def _rgba_to_hex(rgba):
    r, g, b = rgba[0], rgba[1], rgba[2]
    return f"#{r:02x}{g:02x}{b:02x}"


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
        self.current_slide_index = 0

        # Variables de texto
        self.v_photo = tk.StringVar()
        self.v_logo = tk.StringVar(value=self._default_logo_src())
        self.v_title = tk.StringVar(value="Tu título aquí")
        self.v_sub   = tk.StringVar(value="frase secundaria")
        self.v_desc  = tk.StringVar()
        self.v_icon  = tk.StringVar(value="planta")
        self.v_format = tk.StringVar(value=self._format_label_for(self.slide.format))
        self.v_export_fmt = tk.StringVar(value="png")
        self.v_export_dir = tk.StringVar(value=str(OUTPUT_DIR))
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
        self._drag_start_xy = None
        self._slider_start_value = None
        self._last_bboxes = {}
        self._img_wh = (0, 0)        # tamaño en px de la imagen mostrada
        self._selected = None        # Layer seleccionada actualmente, o None
        self._handles = {}           # {nombre_handle: (x,y) en px de pantalla}
        self._resize = None          # estado del arrastre de resize en curso, o None
        self._guides = []            # líneas guía activas durante un arrastre, [(tipo,pos_px), ...]
        self._adjust_expanded = False  # colapsado por defecto
        self._photo_pan = None       # datos del arrastre de encuadre en curso, o None
        self._wheel_zoom_start = None  # zoom al iniciar un gesto de rueda, para el undo agrupado
        self._wheel_zoom_job = None
        self._color_alpha_start = None  # valor [r,g,b,a] al iniciar el arrastre del alpha

        from .commands import CommandStack
        self.commands = CommandStack(on_change=self._on_commands_changed)

        self._project_path = None   # Path del .json actual, o None si es nuevo/sin guardar
        self._dirty = False         # True si hay cambios sin guardar

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        self.canvas.bind("<MouseWheel>", self._on_photo_wheel)

        self._hint_id = self.canvas.create_text(
            10, 10, anchor="nw", fill="#666", font=("Segoe UI", 12),
            text="Elige una foto en el panel izquierdo\ny presiona «Vista previa».")

        for key, dx, dy in [("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)]:
            self.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy, NUDGE_STEP))
            self.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy, NUDGE_STEP_SHIFT))
            self.bind(f"<Alt-{key}>", lambda e, dx=dx, dy=dy: self._nudge(dx, dy, NUDGE_STEP_ALT))

        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Control-Shift-Z>", lambda e: self._redo())

    def _build_left(self, left):
        pad = {"padx": 16}

        lbl_textos = tk.Label(left, text="TEXTOS", bg=PANEL, fg=ACCENT,
                               font=("Segoe UI", 11, "bold"))
        lbl_textos.pack(anchor="w", pady=(6, 10), **pad)

        # Formato
        tk.Label(left, text="🖼  Formato", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", **pad)
        self._formato_labels = [f["label"] for f in FORMATOS] + ["Personalizado…"]
        cb_formato = ttk.Combobox(left, textvariable=self.v_format, values=self._formato_labels,
                                  state="readonly", font=("Segoe UI", 9))
        cb_formato.pack(fill=tk.X, pady=(2, 10), **pad)
        cb_formato.bind("<<ComboboxSelected>>", lambda e: self._on_format_change())

        # Layout
        tk.Label(left, text="🧩  Layout", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        row_layout = tk.Frame(left, bg=PANEL)
        row_layout.pack(fill=tk.X, pady=(2, 10), **pad)
        for layout_id in ("A", "B", "C", "D", "E"):
            tk.Button(row_layout, text=layout_id, bg="#3d3d3d", fg=TEXT, relief="flat",
                      font=("Segoe UI", 9, "bold"), width=3,
                      command=lambda lid=layout_id: self._apply_layout(lid)).pack(
                side=tk.LEFT, padx=(0, 4))

        # Capas
        tk.Label(left, text="📚  Capas", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self._layers_list_frame = tk.Frame(left, bg=PANEL)
        self._layers_list_frame.pack(fill=tk.X, pady=(0, 10), **pad)
        self._refresh_layers_list()

        tk.Button(left, text="+ Agregar CTA", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_cta_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar línea", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_line_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar puntos", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_dots_layer).pack(
            fill=tk.X, pady=(0, 4), **pad)
        tk.Button(left, text="+ Agregar texto", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._add_text_layer).pack(
            fill=tk.X, pady=(0, 10), **pad)

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

        # Logo
        tk.Label(left, text="Logo", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        row_logo = tk.Frame(left, bg=PANEL)
        row_logo.pack(fill=tk.X, pady=(0, 4), **pad)
        e_logo = tk.Entry(row_logo, textvariable=self.v_logo, bg=FIELD, fg=TEXT,
                          insertbackground="white", relief="flat", bd=4,
                          font=("Segoe UI", 9))
        e_logo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        e_logo.bind("<KeyRelease>", lambda e: self._on_logo_direct_edit())
        tk.Button(row_logo, text="…", bg="#3d3d3d", fg=TEXT, relief="flat", padx=8,
                  command=self._browse_logo).pack(side=tk.LEFT, padx=(4, 0))

        self.v_logo_shared = tk.BooleanVar(value="logo" in self.project.shared)
        tk.Checkbutton(left, text="Usar en todo el carrusel", variable=self.v_logo_shared,
                        bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                        activeforeground=TEXT, font=("Segoe UI", 8),
                        command=self._toggle_shared_logo).pack(anchor="w", pady=(0, 8), **pad)

        # Título (multilínea)
        tk.Label(left, text="✏️  Título  (Enter = salto de línea)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self.txt_title = tk.Text(left, height=3, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                 font=("Segoe UI", 10), relief="flat", bd=4, wrap="word")
        self.txt_title.insert("1.0", self.v_title.get())
        self.txt_title.pack(fill=tk.X, pady=(0, 8), **pad)
        self.txt_title.bind("<KeyRelease>", lambda e: self._on_direct_edit())

        # Subtítulo
        tk.Label(left, text="✨  Subtítulo (cursiva verde)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        e_sub = tk.Entry(left, textvariable=self.v_sub, bg=FIELD, fg=TEXT,
                         insertbackground="white", relief="flat", bd=4, font=("Segoe UI", 10))
        e_sub.pack(fill=tk.X, pady=(0, 8), **pad)
        e_sub.bind("<KeyRelease>", lambda e: self._on_direct_edit())

        # Descripción
        tk.Label(left, text="📝  Descripción (recuadro inferior)", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        self.txt_desc = tk.Text(left, height=4, bg=FIELD, fg=TEXT, insertbackground=TEXT,
                                font=("Segoe UI", 10), relief="flat", bd=4, wrap="word")
        self.txt_desc.pack(fill=tk.X, pady=(0, 8), **pad)
        self.txt_desc.bind("<KeyRelease>", lambda e: self._on_direct_edit())

        # Ícono
        tk.Label(left, text="🔖  Ícono del recuadro", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2), **pad)
        cb = ttk.Combobox(left, textvariable=self.v_icon, values=ICONS,
                          state="readonly", font=("Segoe UI", 10))
        cb.pack(fill=tk.X, pady=(0, 10), **pad)
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_direct_edit())

        # Proyecto
        proj_row = tk.Frame(left, bg=PANEL)
        proj_row.pack(fill=tk.X, pady=(4, 4), **pad)
        tk.Button(proj_row, text="📂 Abrir", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), command=self._open_project).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        tk.Button(proj_row, text="💾 Guardar", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 9), command=self._save_project).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        tk.Button(left, text="🗂  Importar carrusel por lotes…", bg="#3d3d3d", fg=TEXT,
                  relief="flat", font=("Segoe UI", 9),
                  command=self._import_batch).pack(fill=tk.X, pady=(0, 6), **pad)

        # Botones
        tk.Button(left, text="👁  Vista previa", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 10), pady=8, command=self._render_now).pack(
            fill=tk.X, pady=(6, 4), **pad)

        export_row = tk.Frame(left, bg=PANEL)
        export_row.pack(fill=tk.X, pady=(2, 2), **pad)
        tk.Label(export_row, text="Formato:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        cb_fmt = ttk.Combobox(export_row, textvariable=self.v_export_fmt,
                              values=["png", "jpg"], state="readonly", width=6,
                              font=("Segoe UI", 9))
        cb_fmt.pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(export_row, text="📁 Carpeta…", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._choose_export_dir).pack(
            side=tk.RIGHT)

        tk.Button(left, text="📤  Exportar", bg=ACCENT, fg="white", relief="flat",
                  font=("Segoe UI", 11, "bold"), pady=9, command=self._export).pack(
            fill=tk.X, pady=(4, 4), **pad)
        tk.Button(left, text="📤  Exportar todas las láminas", bg="#3d3d3d", fg=TEXT,
                  relief="flat", font=("Segoe UI", 9),
                  command=self._export_all).pack(fill=tk.X, pady=(0, 6), **pad)

        # Panel de miniaturas de láminas: se instancia al final (después de
        # txt_title/txt_desc, de los que depende _build_layers_for para
        # componer las miniaturas) pero se empaqueta antes que "TEXTOS" para
        # que aparezca visualmente arriba de todo, como pide el diseño.
        from .slides_panel import SlidesPanel
        self.slides_panel = SlidesPanel(left, self, bg=PANEL, panel_bg=PANEL,
                                         accent=ACCENT, text_color=TEXT, muted_color=MUTED)
        self.slides_panel.pack(fill=tk.X, padx=16, pady=(16, 4), before=lbl_textos)

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

        tk.Label(inner, text="PROPIEDADES", bg=PANEL2, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(inner, text="Hacé click en un elemento de la vista previa\npara editarlo acá.",
                 bg=PANEL2, fg=MUTED, font=("Segoe UI", 8), justify="left").pack(
            anchor="w", padx=16, pady=(0, 8))

        self._props_body = tk.Frame(inner, bg=PANEL2)
        self._props_body.pack(fill=tk.X)

        tk.Button(inner, text="↺  Restablecer posiciones", bg="#3d3d3d", fg=TEXT,
                  relief="flat", font=("Segoe UI", 9), pady=6,
                  command=self._reset).pack(fill=tk.X, padx=16, pady=(12, 16))

        self._build_property_panel()

    def _refresh_layers_list(self):
        """Reconstruye la lista de capas del panel izquierdo, ordenada de mayor
        a menor z (la capa que se dibuja al frente aparece primero)."""
        for w in self._layers_list_frame.winfo_children():
            w.destroy()

        layers_by_z = sorted(self.slide.layers, key=lambda l: l.z, reverse=True)
        for layer in layers_by_z:
            self._build_layer_row(self._layers_list_frame, layer)

    def _build_layer_row(self, parent, layer):
        is_selected = layer is self._selected
        row_bg = "#3a4a2f" if is_selected else PANEL
        row = tk.Frame(parent, bg=row_bg)
        row.pack(fill=tk.X, pady=1)

        visible_icon = "👁" if layer.visible else "🙈"
        tk.Button(row, text=visible_icon, bg=row_bg, fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), width=2,
                  command=lambda l=layer: self._toggle_layer_visible(l)).pack(side=tk.LEFT)

        lock_icon = "🔒" if layer.locked else "🔓"
        tk.Button(row, text=lock_icon, bg=row_bg, fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), width=2,
                  command=lambda l=layer: self._toggle_layer_locked(l)).pack(side=tk.LEFT)

        name_label = tk.Label(row, text=layer.name, bg=row_bg, fg=TEXT,
                               font=("Segoe UI", 8), anchor="w")
        name_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        name_label.bind("<Button-1>", lambda e, l=layer: self._set_selected(l))
        name_label.bind("<Double-Button-1>", lambda e, l=layer, lbl=name_label:
                         self._start_rename(l, lbl, row))

        tk.Button(row, text="▲", bg=row_bg, fg=TEXT, relief="flat",
                  font=("Segoe UI", 7), width=2,
                  command=lambda l=layer: self._move_layer_z(l, 1)).pack(side=tk.LEFT)
        tk.Button(row, text="▼", bg=row_bg, fg=TEXT, relief="flat",
                  font=("Segoe UI", 7), width=2,
                  command=lambda l=layer: self._move_layer_z(l, -1)).pack(side=tk.LEFT)
        tk.Button(row, text="⧉", bg=row_bg, fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), width=2,
                  command=lambda l=layer: self._duplicate_layer(l)).pack(side=tk.LEFT)
        tk.Button(row, text="🗑", bg=row_bg, fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), width=2,
                  command=lambda l=layer: self._delete_layer(l)).pack(side=tk.LEFT)

    def _start_rename(self, layer, label_widget, row):
        entry_var = tk.StringVar(value=layer.name)
        entry = tk.Entry(row, textvariable=entry_var, bg=FIELD, fg=TEXT,
                          insertbackground=TEXT, relief="flat", bd=2,
                          font=("Segoe UI", 8))
        label_widget.pack_forget()
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        entry.focus_set()
        entry.select_range(0, tk.END)

        def _commit(_event=None):
            new_name = entry_var.get().strip()
            if new_name:
                self._rename_layer(layer, new_name)
            else:
                self._refresh_layers_list()

        entry.bind("<Return>", _commit)
        entry.bind("<FocusOut>", _commit)
        entry.bind("<Escape>", lambda e: self._refresh_layers_list())

    def _toggle_layer_visible(self, layer):
        from .commands import PropertyChangeCommand
        old_value = layer.visible
        self.commands.push(PropertyChangeCommand(layer, "visible", old_value, not old_value))
        self._refresh_layers_list()
        if layer is self._selected:
            self._build_property_panel()
        self._schedule_render()

    def _toggle_layer_locked(self, layer):
        from .commands import PropertyChangeCommand
        old_value = layer.locked
        self.commands.push(PropertyChangeCommand(layer, "locked", old_value, not old_value))
        self._refresh_layers_list()
        if layer is self._selected:
            self._build_property_panel()
        self._schedule_render()

    def _move_layer_z(self, layer, direction):
        layers_by_z = sorted(self.slide.layers, key=lambda l: l.z, reverse=True)
        idx = layers_by_z.index(layer)
        swap_idx = idx - direction
        if swap_idx < 0 or swap_idx >= len(layers_by_z):
            return
        other = layers_by_z[swap_idx]
        from .commands import ReorderLayerCommand
        self.commands.push(ReorderLayerCommand(layer, layer.z, other.z, other, other.z, layer.z))
        self._refresh_layers_list()
        self._schedule_render()

    def _duplicate_layer(self, layer):
        import dataclasses
        new_layer = dataclasses.replace(layer)
        new_layer.id = _short_id()
        new_layer.name = layer.name + " (copia)"
        new_layer.z = max((l.z for l in self.slide.layers), default=0) + 1
        index = len(self.slide.layers)
        from .commands import AddLayerCommand
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._set_selected(new_layer)
        self._refresh_layers_list()
        self._schedule_render()

    def _add_cta_layer(self):
        from .models import CTALayer
        from .commands import AddLayerCommand
        new_z = max((l.z for l in self.slide.layers), default=0) + 1
        new_layer = CTALayer(name="CTA", z=new_z, text="Reservá ahora",
                              x=0.10, y=0.90, w=0.35, h=0.08)
        index = len(self.slide.layers)
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._selected = new_layer
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _add_line_layer(self):
        from .models import LineLayer
        from .commands import AddLayerCommand
        new_z = max((l.z for l in self.slide.layers), default=0) + 1
        new_layer = LineLayer(name="Línea", z=new_z, x=0.50, y=0.70)
        index = len(self.slide.layers)
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._selected = new_layer
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _add_dots_layer(self):
        from .models import DotsLayer
        from .commands import AddLayerCommand
        new_z = max((l.z for l in self.slide.layers), default=0) + 1
        new_layer = DotsLayer(name="Puntos de carrusel", z=new_z, x=0.50, y=0.94)
        index = len(self.slide.layers)
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._selected = new_layer
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _add_text_layer(self):
        from .models import TextLayer
        from .commands import AddLayerCommand
        new_z = max((l.z for l in self.slide.layers), default=0) + 1
        new_layer = TextLayer(name="Texto", role="free", z=new_z,
                               text="Texto libre", x=0.10, y=0.50, size=0.04)
        index = len(self.slide.layers)
        self.commands.push(AddLayerCommand(self.slide.layers, new_layer, index))
        self._selected = new_layer
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _delete_layer(self, layer):
        from .commands import DeleteLayerCommand
        self.commands.push(DeleteLayerCommand(self.slide.layers, layer))
        if layer is self._selected:
            self._set_selected(None)
        self._refresh_layers_list()
        self._schedule_render()

    def _rename_layer(self, layer, new_name):
        old_name = layer.name
        if old_name != new_name:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, "name", old_name, new_name))
        self._refresh_layers_list()

    def _build_property_panel(self):
        """Reconstruye el contenido del panel derecho según la capa seleccionada."""
        for w in self._props_body.winfo_children():
            w.destroy()
        self.ctrl = {}

        if self._selected is None:
            tk.Label(self._props_body, text="Seleccioná una capa en la vista previa.",
                     bg=PANEL2, fg=MUTED, font=("Segoe UI", 9), wraplength=250,
                     justify="left").pack(anchor="w", padx=16, pady=8)
            return

        layer = self._selected
        kind = self._kind_of(layer)
        if kind is None:
            return
        token = self._token_for_layer(layer)

        card = tk.Frame(self._props_body, bg=PANEL, padx=12, pady=8)
        card.pack(fill=tk.X, padx=12, pady=5)

        label = "Foto" if kind == "photo" else LABELS[kind]
        tk.Label(card, text=label, bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        header = tk.Frame(card, bg=PANEL)
        header.pack(fill=tk.X, pady=(4, 6))
        visible_text = "🙈  Ocultar" if layer.visible else "👁  Mostrar"
        tk.Button(header, text=visible_text, bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._toggle_visible).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        locked_text = "🔓  Desbloquear" if layer.locked else "🔒  Bloquear"
        tk.Button(header, text=locked_text, bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), command=self._toggle_locked).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        self.ctrl[token] = {}
        disabled = layer.locked

        if kind == "photo":
            self._slider(card, token, "zoom", "Zoom", 1.0, 3.0, disabled=disabled)
            self._slider(card, token, "offset_x", "Posición X del recorte", 0.0, 1.0,
                         disabled=disabled)
            self._slider(card, token, "offset_y", "Posición Y del recorte", 0.0, 1.0,
                         disabled=disabled)
            self._slider(card, token, "opacity", "Opacidad", 0.0, 1.0,
                         disabled=disabled, as_percent=True)
            self._build_photo_adjust_section(card, layer, token, disabled)
            return

        if kind not in ("line", "dots"):
            smin, smax = SIZE_RANGE[kind]
            size_label = "Tamaño del logo" if kind == "logo" else "Tamaño de fuente"
        self._slider(card, token, "x", "Posición X", 0.0, 1.0, disabled=disabled)
        self._slider(card, token, "y", "Posición Y", 0.0, 1.0, disabled=disabled)
        if kind in ("desc", "cta"):
            self._slider(card, token, "w", "Ancho de la caja", 0.10, 0.95, disabled=disabled)
            self._slider(card, token, "h", "Alto de la caja", 0.03, 0.50, disabled=disabled)
            self._color_picker(card, layer, "fill", "Color de la caja", disabled=disabled)
            self._color_picker(card, layer, "text_color", "Color del texto", disabled=disabled)
        if kind == "line":
            self._slider(card, token, "length", "Largo", 0.05, 0.80, disabled=disabled)
            self._slider(card, token, "thickness", "Grosor", 0.001, 0.03, disabled=disabled)
            self._slider(card, token, "gap", "Separación", 0.0, 0.30, disabled=disabled)
            self._color_picker(card, layer, "color", "Color de línea", disabled=disabled)
        if kind == "dots":
            total = len(self.project.slides)
            active = self.current_slide_index + 1
            tk.Label(card, text=f"Carrusel: {active}/{total}", bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
            self._slider(card, token, "spacing", "Separación", 0.005, 0.12, disabled=disabled)
            self._color_picker(card, layer, "color", "Color de puntos", disabled=disabled)
        if kind == "cta":
            tk.Label(card, text="Texto del CTA", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
            cta_text_var = tk.StringVar(value=layer.text)
            cta_entry = tk.Entry(card, textvariable=cta_text_var, bg=FIELD, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=2,
                                  font=("Segoe UI", 9),
                                  state=tk.DISABLED if disabled else tk.NORMAL)
            cta_entry.pack(fill=tk.X)
            cta_entry.bind(
                "<Return>",
                lambda e, l=layer, old=layer.text, v=cta_text_var:
                    self._on_cta_text_commit(l, old, v.get()))
            cta_entry.bind(
                "<FocusOut>",
                lambda e, l=layer, old=layer.text, v=cta_text_var:
                    self._on_cta_text_commit(l, old, v.get()))
        if kind == "free":
            tk.Label(card, text="Texto", bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
            free_text = tk.Text(card, height=3, bg=FIELD, fg=TEXT,
                                 insertbackground=TEXT, relief="flat", bd=2,
                                 font=("Segoe UI", 9),
                                 state=tk.DISABLED if disabled else tk.NORMAL)
            free_text.insert("1.0", layer.text)
            free_text.pack(fill=tk.X, pady=(2, 6))
            free_text.bind(
                "<FocusOut>",
                lambda e, l=layer, old=layer.text, w=free_text:
                    self._on_cta_text_commit(l, old, w.get("1.0", "end-1c")))
            self._color_picker(card, layer, "color", "Color del texto", disabled=disabled)
        if kind in ("title", "sub", "free"):
            self._build_text_style_section(card, layer, token, disabled)
        if kind not in ("line", "dots"):
            self._slider(card, token, "size", size_label, smin, smax, disabled=disabled)
        self._slider(card, token, "opacity", "Opacidad", 0.0, 1.0,
                     disabled=disabled, as_percent=True)

        align_row = tk.Frame(card, bg=PANEL)
        align_row.pack(fill=tk.X, pady=(8, 0))
        btn_state = tk.DISABLED if disabled else tk.NORMAL
        tk.Button(align_row, text="↔ Centrar H", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), state=btn_state,
                  command=lambda: self._center_selected("x")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(align_row, text="↕ Centrar V", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), state=btn_state,
                  command=lambda: self._center_selected("y")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(align_row, text="+ Centrar", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), state=btn_state,
                  command=lambda: self._center_selected("both")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

    def _build_photo_adjust_section(self, card, layer, token, disabled):
        toggle_row = tk.Frame(card, bg=PANEL)
        toggle_row.pack(fill=tk.X, pady=(10, 0))
        arrow = "▼" if self._adjust_expanded else "▶"
        tk.Button(toggle_row, text=f"{arrow} Ajustes", bg=PANEL, fg=ACCENT, relief="flat",
                  font=("Segoe UI", 9, "bold"), anchor="w",
                  command=self._toggle_adjust_section).pack(side=tk.LEFT, fill=tk.X, expand=True)
        if not disabled:
            tk.Button(toggle_row, text="Restablecer", bg="#3d3d3d", fg=TEXT, relief="flat",
                      font=("Segoe UI", 8),
                      command=lambda l=layer: self._reset_photo_adjust(l)).pack(side=tk.RIGHT)

        if not self._adjust_expanded:
            return

        for key, label in ADJUST_LABELS.items():
            lo, hi = ADJUST_RANGE[key]
            self._slider(card, token, f"adjust.{key}", label, lo, hi, disabled=disabled)

        tk.Frame(card, bg="#3d3d3d", height=1).pack(fill=tk.X, pady=(8, 6))

        state = tk.DISABLED if disabled else tk.NORMAL
        top_var = tk.BooleanVar(value=layer.overlay["top_grad"])
        tk.Checkbutton(card, text="Degradado superior", variable=top_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_overlay_flag("top_grad")).pack(anchor="w")

        bottom_var = tk.BooleanVar(value=layer.overlay["bottom_grad"])
        tk.Checkbutton(card, text="Degradado inferior", variable=bottom_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_overlay_flag("bottom_grad")).pack(anchor="w")

        lo, hi = OVERLAY_STRENGTH_RANGE
        self._slider(card, token, "overlay.strength", "Intensidad del overlay", lo, hi,
                     disabled=disabled)

    def _build_text_style_section(self, card, layer, token, disabled):
        from .constants import FAMILY_FONT_FILES
        state = tk.DISABLED if disabled else tk.NORMAL

        tk.Label(card, text="Fuente", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))
        family_labels = {"": "Marca (por rol)", "playfair": "Playfair Display",
                          "dancing": "Dancing Script", "lato": "Lato"}
        family_keys = [""] + list(FAMILY_FONT_FILES.keys())
        family_var = tk.StringVar(value=family_labels.get(layer.font_family, "Marca (por rol)"))
        family_combo = ttk.Combobox(card, textvariable=family_var,
                                     values=[family_labels[k] for k in family_keys],
                                     state="readonly" if not disabled else tk.DISABLED,
                                     font=("Segoe UI", 9))
        family_combo.pack(fill=tk.X, pady=(2, 6))
        label_to_key = {v: k for k, v in family_labels.items()}
        family_combo.bind(
            "<<ComboboxSelected>>",
            lambda e, l=layer, v=family_var:
                self._on_font_family_change(l, label_to_key[v.get()]))

        style_row = tk.Frame(card, bg=PANEL)
        style_row.pack(fill=tk.X, pady=(0, 6))
        bold_var = tk.BooleanVar(value=layer.bold)
        tk.Checkbutton(style_row, text="Negrita", variable=bold_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "bold")).pack(side=tk.LEFT)
        italic_var = tk.BooleanVar(value=layer.italic)
        tk.Checkbutton(style_row, text="Cursiva", variable=italic_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "italic")).pack(side=tk.LEFT, padx=(8, 0))
        underline_var = tk.BooleanVar(value=layer.underline)
        tk.Checkbutton(style_row, text="Subrayado", variable=underline_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "underline")).pack(side=tk.LEFT, padx=(8, 0))

        self._slider(card, token, "line_spacing", "Interlineado", 0.8, 2.5, disabled=disabled)
        self._slider(card, token, "letter_spacing", "Espaciado entre letras", -0.05, 0.4,
                     disabled=disabled)

        stroke_var = tk.BooleanVar(value=layer.stroke_on)
        tk.Checkbutton(card, text="Contorno", variable=stroke_var,
                       bg=PANEL, fg=TEXT, selectcolor=FIELD, activebackground=PANEL,
                       activeforeground=TEXT, font=("Segoe UI", 8), state=state,
                       command=lambda: self._toggle_text_flag(layer, "stroke_on")).pack(anchor="w")
        self._slider(card, token, "stroke_width", "Grosor del contorno", 0.0, 0.15,
                     disabled=disabled or not layer.stroke_on)

        self._slider(card, token, "rotation", "Rotación (grados)", -45.0, 45.0, disabled=disabled)

    def _format_value(self, value, as_percent):
        if as_percent:
            return f"{round(value * 100)}"
        return f"{value:.3f}"

    def _slider(self, parent, elem, param, label, lo, hi, disabled=False, as_percent=False):
        value = self._get_layer_value(elem, param)
        var = tk.DoubleVar(value=value)
        self.ctrl[elem][param] = var

        tk.Label(parent, text=label, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X)

        state = tk.DISABLED if disabled else tk.NORMAL
        s = ttk.Scale(row, from_=lo, to=hi, variable=var, orient=tk.HORIZONTAL,
                      style="Brand.Horizontal.TScale", state=state,
                      command=lambda _v, e=elem, p=param, ap=as_percent: self._on_slider(e, p, ap))
        s.pack(side=tk.LEFT, fill=tk.X, expand=True)
        s.bind("<ButtonPress-1>", lambda e, el=elem, p=param: self._on_slider_press(el, p))
        s.bind("<ButtonRelease-1>", lambda e, el=elem, p=param: self._on_slider_release(el, p))

        entry_var = tk.StringVar(value=self._format_value(value, as_percent))
        entry = tk.Entry(row, textvariable=entry_var, width=6, bg=FIELD, fg=TEXT,
                          insertbackground=TEXT, relief="flat", bd=2,
                          font=("Segoe UI", 8), state=state)
        entry.pack(side=tk.LEFT, padx=(6, 0))
        entry.bind("<Return>",
                   lambda e, elem=elem, param=param, lo=lo, hi=hi, ap=as_percent,
                   var=var, ev=entry_var: self._on_entry_commit(elem, param, lo, hi, ap, var, ev))
        entry.bind("<FocusOut>",
                   lambda e, elem=elem, param=param, lo=lo, hi=hi, ap=as_percent,
                   var=var, ev=entry_var: self._on_entry_commit(elem, param, lo, hi, ap, var, ev))
        self.ctrl[elem][param + "_entry"] = entry_var

    def _on_cta_text_commit(self, layer, old_value, new_value):
        if old_value != new_value:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, "text", old_value, new_value))
        self._schedule_render()

    def _on_entry_commit(self, elem, param, lo, hi, as_percent, var, entry_var):
        raw = entry_var.get().strip().replace(",", ".")
        try:
            num = float(raw)
        except ValueError:
            entry_var.set(self._format_value(var.get(), as_percent))
            return
        value = num / 100 if as_percent else num
        value = min(hi, max(lo, value))
        var.set(value)
        entry_var.set(self._format_value(value, as_percent))

        old_value = self._get_layer_value(elem, param)
        if old_value != value:
            layer = self._layer_by_token(elem)
            kind = self._kind_of(layer)
            from .commands import PropertyChangeCommand, CompositeCommand, DictItemChangeCommand
            if "." in param:
                group, key = param.split(".", 1)
                self.commands.push(
                    DictItemChangeCommand(getattr(layer, group), key, old_value, value))
            elif kind == "logo" and param == "size":
                self.commands.push(CompositeCommand([
                    PropertyChangeCommand(layer, "w", old_value, value),
                    PropertyChangeCommand(layer, "h", old_value, value),
                ]))
            else:
                self.commands.push(PropertyChangeCommand(layer, param, old_value, value))
            if kind == "logo":
                self._sync_shared_logo_if_active()
        self._schedule_render()

    def _toggle_visible(self):
        if self._selected is None:
            return
        from .commands import PropertyChangeCommand
        layer = self._selected
        old_value = layer.visible
        self.commands.push(PropertyChangeCommand(layer, "visible", old_value, not old_value))
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _toggle_locked(self):
        if self._selected is None:
            return
        from .commands import PropertyChangeCommand
        layer = self._selected
        old_value = layer.locked
        self.commands.push(PropertyChangeCommand(layer, "locked", old_value, not old_value))
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _toggle_adjust_section(self):
        self._adjust_expanded = not self._adjust_expanded
        self._build_property_panel()

    def _reset_photo_adjust(self, layer):
        from .commands import DictItemChangeCommand, CompositeCommand
        from .models import DEFAULT_PHOTO_ADJUST
        cmds = [
            DictItemChangeCommand(layer.adjust, key, layer.adjust[key], default)
            for key, default in DEFAULT_PHOTO_ADJUST.items()
            if layer.adjust[key] != default
        ]
        if cmds:
            self.commands.push(CompositeCommand(cmds))
        self._build_property_panel()
        self._schedule_render()

    def _toggle_overlay_flag(self, key):
        layer = self._selected
        if layer is None or self._kind_of(layer) != "photo" or layer.locked:
            return
        from .commands import DictItemChangeCommand
        old_value = layer.overlay[key]
        self.commands.push(DictItemChangeCommand(layer.overlay, key, old_value, not old_value))
        self._schedule_render()

    def _toggle_text_flag(self, layer, attr):
        if layer.locked:
            return
        from .commands import PropertyChangeCommand
        old_value = getattr(layer, attr)
        self.commands.push(PropertyChangeCommand(layer, attr, old_value, not old_value))
        if attr == "stroke_on":
            self._build_property_panel()
        self._schedule_render()

    def _on_font_family_change(self, layer, new_value):
        old_value = layer.font_family
        if old_value != new_value:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, "font_family", old_value, new_value))
            self._build_property_panel()
        self._schedule_render()

    def _center_selected(self, axis):
        if self._selected is None or self._selected.locked:
            return
        kind = self._kind_of(self._selected)
        bb = self._last_bboxes.get(self._bbox_key_for_layer(self._selected))
        if not bb:
            return
        iw, ih = self._img_wh
        if iw == 0 or ih == 0:
            return
        x0, y0, x1, y1 = bb
        bw, bh = x1 - x0, y1 - y0
        new_x0, new_y0 = _center_position(axis, x0, y0, bw, bh, iw, ih)

        layer = self._selected
        old_x, old_y = layer.x, layer.y
        if kind == "sub":
            half_w = bw / 2
            cx = new_x0 + half_w
            final_x = min(1.0, max(0.0, cx / iw))
            final_y = min(1.0, max(0.0, new_y0 / ih))
        else:
            final_x = min(1.0, max(0.0, new_x0 / iw))
            final_y = min(1.0, max(0.0, new_y0 / ih))

        if (final_x, final_y) != (old_x, old_y):
            from .commands import PropertyChangeCommand, CompositeCommand
            self.commands.push(CompositeCommand([
                PropertyChangeCommand(layer, "x", old_x, final_x),
                PropertyChangeCommand(layer, "y", old_y, final_y),
            ]))
            if kind == "logo":
                self._sync_shared_logo_if_active()

        self._sync_sliders()
        self._render_now()

    # ── Puente entre el vocabulario del render y el modelo ─────
    def _layer_by_kind(self, kind, slide=None):
        """Traduce entre el vocabulario del render ("photo"/"logo"/"title"/"sub"/"desc")
        y los tipos/roles reales de dcpub.models (Layer.type, TextLayer.role).
        Busca en `slide` si se pasa, o en la lámina activa (self.slide) si no."""
        target = slide if slide is not None else self.slide
        for layer in target.layers:
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
        """Dado un Layer, devuelve su tipo visual para render/propiedades."""
        if layer is None:
            return None
        if layer.type == "photo":
            return "photo"
        if layer.type == "logo":
            return "logo"
        if layer.type == "text" and layer.role == "title":
            return "title"
        if layer.type == "text" and layer.role == "subtitle":
            return "sub"
        if layer.type == "box":
            return "desc"
        if layer.type == "cta":
            return "cta"
        if layer.type == "line":
            return "line"
        if layer.type == "dots":
            return "dots"
        if layer.type == "text" and layer.role == "free":
            return "free"
        return None

    def _token_for_layer(self, layer):
        return layer.id

    def _layer_by_token(self, token):
        for layer in self.slide.layers:
            if layer.id == token:
                return layer
        return self._layer_by_kind(token)

    def _bbox_key_for_layer(self, layer):
        return layer.id

    def _get_layer_value(self, elem, param):
        layer = self._layer_by_token(elem)
        if "." in param:
            group, key = param.split(".", 1)
            return getattr(layer, group)[key]
        if self._kind_of(layer) == "logo" and param == "size":
            return layer.w
        if param == "line_spacing":
            return getattr(layer, param) or 1.22
        return getattr(layer, param)

    def _set_layer_value(self, elem, param, value):
        layer = self._layer_by_token(elem)
        if "." in param:
            group, key = param.split(".", 1)
            getattr(layer, group)[key] = value
            return
        if self._kind_of(layer) == "logo" and param == "size":
            layer.w = value
            layer.h = value
        else:
            setattr(layer, param, value)

    # ── Sincronización slider  →  estado ───────────────────────
    def _on_slider(self, elem, param, as_percent=False):
        if self._updating:
            return
        value = float(self.ctrl[elem][param].get())
        self._set_layer_value(elem, param, value)
        entry_var = self.ctrl[elem].get(param + "_entry")
        if entry_var is not None:
            entry_var.set(self._format_value(value, as_percent))
        self._schedule_render()

    def _on_slider_press(self, elem, param):
        self._slider_start_value = self._get_layer_value(elem, param)

    def _on_slider_release(self, elem, param):
        if self._slider_start_value is None:
            return
        old_value = self._slider_start_value
        self._slider_start_value = None
        layer = self._layer_by_token(elem)
        kind = self._kind_of(layer)
        if kind == "logo" and param == "size":
            new_w, new_h = layer.w, layer.h
            if (old_value, old_value) != (new_w, new_h):
                from .commands import PropertyChangeCommand, CompositeCommand
                self.commands.push(CompositeCommand([
                    PropertyChangeCommand(layer, "w", old_value, new_w),
                    PropertyChangeCommand(layer, "h", old_value, new_h),
                ]))
            self._sync_shared_logo_if_active()
            return
        new_value = self._get_layer_value(elem, param)
        if old_value != new_value:
            from .commands import PropertyChangeCommand, DictItemChangeCommand
            if "." in param:
                group, key = param.split(".", 1)
                self.commands.push(
                    DictItemChangeCommand(getattr(layer, group), key, old_value, new_value))
            else:
                self.commands.push(PropertyChangeCommand(layer, param, old_value, new_value))
            if kind == "logo":
                self._sync_shared_logo_if_active()

    def _on_color_alpha_press(self, layer, attr):
        self._color_alpha_start = list(getattr(layer, attr))

    def _on_color_alpha_release(self, layer, attr):
        if self._color_alpha_start is None:
            return
        old_value = self._color_alpha_start
        self._color_alpha_start = None
        new_value = list(getattr(layer, attr))
        if old_value != new_value:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(layer, attr, old_value, new_value))

    def _on_color_alpha_change(self, layer, attr, alpha_var, swatch):
        value = list(getattr(layer, attr))
        while len(value) < 4:
            value.append(255)
        value[3] = int(alpha_var.get())
        setattr(layer, attr, value)
        swatch.config(bg=_rgba_to_hex(value))
        self._schedule_render()

    def _pick_color(self, layer, attr, swatch):
        from tkinter import colorchooser
        from .commands import PropertyChangeCommand
        old_value = list(getattr(layer, attr))
        _, hex_color = colorchooser.askcolor(color=_rgba_to_hex(old_value),
                                              title="Elegir color")
        if hex_color is None:
            return
        rgb16 = self.winfo_rgb(hex_color)
        r, g, b = rgb16[0] // 256, rgb16[1] // 256, rgb16[2] // 256
        alpha = old_value[3] if len(old_value) > 3 else 255
        new_value = [r, g, b, alpha]
        if new_value != old_value:
            self.commands.push(PropertyChangeCommand(layer, attr, old_value, new_value))
            swatch.config(bg=_rgba_to_hex(new_value))
            self._schedule_render()

    def _color_picker(self, parent, layer, attr, label, disabled=False):
        tk.Label(parent, text=label, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill=tk.X)

        rgba = list(getattr(layer, attr))
        swatch = tk.Label(row, bg=_rgba_to_hex(rgba), width=3, relief="flat")
        swatch.pack(side=tk.LEFT, padx=(0, 6))

        state = tk.DISABLED if disabled else tk.NORMAL
        tk.Button(row, text="Elegir color…", bg="#3d3d3d", fg=TEXT, relief="flat",
                  font=("Segoe UI", 8), state=state,
                  command=lambda: self._pick_color(layer, attr, swatch)).pack(side=tk.LEFT)

        alpha_value = rgba[3] if len(rgba) > 3 else 255
        alpha_var = tk.IntVar(value=alpha_value)
        alpha_scale = ttk.Scale(
            row, from_=0, to=255, variable=alpha_var, orient=tk.HORIZONTAL,
            style="Brand.Horizontal.TScale", state=state,
            command=lambda _v, l=layer, a=attr, v=alpha_var, s=swatch:
                self._on_color_alpha_change(l, a, v, s))
        alpha_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
        alpha_scale.bind("<ButtonPress-1>",
                          lambda e, l=layer, a=attr: self._on_color_alpha_press(l, a))
        alpha_scale.bind("<ButtonRelease-1>",
                          lambda e, l=layer, a=attr: self._on_color_alpha_release(l, a))

    def _sync_sliders(self):
        """Refleja el estado actual en los controles del panel activo, sin disparar render."""
        if self._selected is None:
            return
        token = self._token_for_layer(self._selected)
        if token not in self.ctrl:
            return
        self._updating = True
        for param, var in list(self.ctrl[token].items()):
            if param.endswith("_entry"):
                continue
            value = self._get_layer_value(token, param)
            var.set(value)
            entry_var = self.ctrl[token].get(param + "_entry")
            if entry_var is not None:
                entry_var.set(self._format_value(value, param == "opacity"))
        self._updating = False

    def _sync_widgets_from_slide(self):
        """Refleja el contenido de self.slide en los widgets de texto/foto/logo
        del panel izquierdo. Mismo bloque que usaba _open_project, ahora
        reutilizable también al cambiar de lámina activa."""
        photo_layer = self._layer_by_kind("photo")
        self.v_photo.set(photo_layer.src if photo_layer else "")
        logo_layer = self._layer_by_kind("logo")
        self.v_logo.set(logo_layer.src if logo_layer and logo_layer.src else str(LOGO_FILE))
        title_layer = self._layer_by_kind("title")
        self.txt_title.delete("1.0", tk.END)
        self.txt_title.insert("1.0", title_layer.text if title_layer else "")
        sub_layer = self._layer_by_kind("sub")
        self.v_sub.set(sub_layer.text if sub_layer else "")
        desc_layer = self._layer_by_kind("desc")
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", desc_layer.text if desc_layer else "")
        self.v_icon.set(desc_layer.icon if desc_layer else "planta")
        self.v_format.set(self._format_label_for(self.slide.format))

    def switch_to_slide(self, index):
        """Cambia la lámina activa a project.slides[index] y refresca toda la
        UI dependiente (widgets de texto, panel de propiedades, panel de
        capas, vista previa). No hace nada si el índice está fuera de rango."""
        if index < 0 or index >= len(self.project.slides):
            return
        self.current_slide_index = index
        self.slide = self.project.slides[index]
        self._selected = None
        self._sync_widgets_from_slide()
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()

    def _add_slide(self):
        """Inserta una lámina en blanco (layout default) justo después de la
        lámina activa, con el mismo formato que la lámina activa."""
        from .models import crear_slide_por_defecto
        from .commands import AddSlideCommand
        nueva = crear_slide_por_defecto(formato=dict(self.slide.format))
        index = self.current_slide_index + 1
        self.commands.push(AddSlideCommand(self.project.slides, nueva, index))
        self.switch_to_slide(index)

    def _duplicate_slide(self):
        """Inserta una copia completa (texto incluido) de la lámina activa
        justo después de ella."""
        from .models import duplicar_slide
        from .commands import AddSlideCommand
        copia = duplicar_slide(self.slide)
        index = self.current_slide_index + 1
        self.commands.push(AddSlideCommand(self.project.slides, copia, index))
        self.switch_to_slide(index)

    def _delete_slide(self):
        """Elimina la lámina activa, salvo que sea la última del proyecto."""
        if len(self.project.slides) <= 1:
            self.v_status.set("No se puede eliminar la última lámina.")
            return
        from .commands import DeleteSlideCommand
        slide_a_borrar = self.slide
        nuevo_index = min(self.current_slide_index, len(self.project.slides) - 2)
        self.commands.push(DeleteSlideCommand(self.project.slides, slide_a_borrar))
        self.switch_to_slide(nuevo_index)

    def _move_slide(self, direction):
        """Intercambia la lámina activa con la adyacente (direction=-1 sube,
        +1 baja). No hace nada si ya está en el extremo."""
        idx = self.current_slide_index
        otro = idx + direction
        if otro < 0 or otro >= len(self.project.slides):
            return
        from .commands import ReorderSlideCommand
        self.commands.push(ReorderSlideCommand(self.project.slides, idx, otro))
        self.switch_to_slide(otro)

    def _copy_style_to_slide(self, origen_slide, destino_index):
        """Copia posición/tamaño/estilo de las capas de `origen_slide` hacia
        la lámina en `destino_index`, preservando el texto/contenido que esa
        lámina ya tenía."""
        if destino_index < 0 or destino_index >= len(self.project.slides):
            return
        from .models import plan_copia_estilo
        from .commands import PropertyChangeCommand, CompositeCommand
        destino = self.project.slides[destino_index]
        cambios = plan_copia_estilo(origen_slide, destino)
        if not cambios:
            return
        comandos = [PropertyChangeCommand(layer, attr, getattr(layer, attr), nuevo)
                    for layer, attr, nuevo in cambios]
        self.commands.push(CompositeCommand(comandos))
        if destino_index == self.current_slide_index:
            self._render_now()

    def _apply_layout(self, layout_id):
        """Reposiciona logo/título/subtítulo/caja de la lámina activa según
        el layout elegido (A-E), preservando su contenido. No afecta otras
        láminas ni la foto de fondo."""
        from .models import plan_aplicar_layout
        from .commands import PropertyChangeCommand, CompositeCommand
        cambios = plan_aplicar_layout(self.slide, layout_id)
        if not cambios:
            return
        comandos = [PropertyChangeCommand(layer, attr, getattr(layer, attr), nuevo)
                    for layer, attr, nuevo in cambios]
        comandos.append(PropertyChangeCommand(
            self.slide, "layout_tag", self.slide.layout_tag, layout_id))
        self.commands.push(CompositeCommand(comandos))
        self._build_property_panel()
        self._render_now()

    def _reset(self):
        self.project = crear_proyecto_por_defecto(self.v_photo.get().strip())
        self.slide = self.project.slides[0]
        self.current_slide_index = 0
        self.v_logo.set(self._default_logo_src())
        self._selected = None
        self._build_property_panel()
        self._set_dirty(True)
        self._schedule_render()

    def _on_commands_changed(self):
        """Callback del CommandStack: se ejecuta en cada push/undo/redo."""
        self._set_dirty(True)

    def _on_direct_edit(self):
        """Marca cambios hechos desde widgets que no pasan por comandos."""
        self._set_dirty(True)
        self._schedule_render()

    def _on_logo_direct_edit(self):
        logo_layer = self._layer_by_kind("logo")
        if logo_layer is not None:
            logo_layer.src = self.v_logo.get().strip()
        self._sync_shared_logo_if_active()
        self._on_direct_edit()

    def _default_logo_src(self):
        logo_layer = self._layer_by_kind("logo") if hasattr(self, "slide") else None
        if logo_layer is not None and logo_layer.src:
            return logo_layer.src
        return str(LOGO_FILE)

    def _toggle_shared_logo(self):
        """Escribe o borra project.shared["logo"] según el estado del checkbox
        "Usar en todo el carrusel". Al activar, toma como valor inicial el
        logo de la lámina activa."""
        if self.v_logo_shared.get():
            logo_layer = self._layer_by_kind("logo")
            self.project.shared["logo"] = {
                "src": logo_layer.src, "x": logo_layer.x, "y": logo_layer.y,
                "w": logo_layer.w, "h": logo_layer.h,
            }
        else:
            self.project.shared.pop("logo", None)
        self._set_dirty(True)
        self._schedule_render()

    def _sync_shared_logo_if_active(self):
        """Si el logo compartido está activo, actualiza su valor con el logo
        actual de la lámina activa (para que un cambio de archivo se
        propague a todo el carrusel)."""
        if "logo" in self.project.shared:
            logo_layer = self._layer_by_kind("logo")
            self.project.shared["logo"] = {
                "src": logo_layer.src, "x": logo_layer.x, "y": logo_layer.y,
                "w": logo_layer.w, "h": logo_layer.h,
            }

    def _set_dirty(self, value):
        self._dirty = value
        self._update_title()

    def _update_title(self):
        base = "Generador de Publicaciones — Cabañas Don Cristobal"
        if self._project_path is not None:
            base += f" — {self._project_path.name}"
        if self._dirty:
            base += " *"
        self.title(base)

    def _sync_text_to_layers(self):
        """Copia el contenido actual de los widgets de texto a los campos
        text/icon/src del modelo, para que guardar/exportar reflejen lo que se
        ve en pantalla."""
        title_layer = self._layer_by_kind("title")
        if title_layer is not None:
            title_layer.text = self.txt_title.get("1.0", "end-1c")
        sub_layer = self._layer_by_kind("sub")
        if sub_layer is not None:
            sub_layer.text = self.v_sub.get()
        desc_layer = self._layer_by_kind("desc")
        if desc_layer is not None:
            desc_layer.text = self.txt_desc.get("1.0", "end-1c")
            desc_layer.icon = self.v_icon.get()
        photo_layer = self._layer_by_kind("photo")
        if photo_layer is not None:
            photo_layer.src = self.v_photo.get().strip()
        logo_layer = self._layer_by_kind("logo")
        if logo_layer is not None:
            logo_layer.src = self.v_logo.get().strip()

    def _undo(self):
        if self.commands.undo():
            self._after_history_change()

    def _redo(self):
        if self.commands.redo():
            self._after_history_change()

    def _after_history_change(self):
        """Refresca toda la UI después de un undo/redo, porque el modelo
        cambió por fuera del flujo normal de edición. Si self.slide ya no
        está en project.slides (undo/redo de una operación de lámina la
        agregó o quitó), reconcilia el puntero de lámina activa antes de
        refrescar nada más."""
        if self.slide in self.project.slides:
            self.current_slide_index = self.project.slides.index(self.slide)
        else:
            self.current_slide_index = min(self.current_slide_index,
                                            len(self.project.slides) - 1)
            self.slide = self.project.slides[self.current_slide_index]
            self._selected = None
            self._sync_widgets_from_slide()
        self._sync_sliders()
        self._build_property_panel()
        self._refresh_layers_list()
        self._render_now()

    # ── Selección ──────────────────────────────────────────────
    def _set_selected(self, layer):
        self._selected = layer
        self._build_property_panel()
        self._refresh_layers_list()
        self._render_now()

    def _update_readout(self):
        if self._selected is None:
            self.v_readout.set("")
            return
        layer = self._selected
        kind = self._kind_of(layer)
        if kind == "photo":
            self.v_readout.set(
                f"Foto · Zoom: {layer.zoom:.2f}  "
                f"Recorte: {layer.offset_x:.2f}, {layer.offset_y:.2f}")
            return
        if kind == "logo":
            tam = layer.w
            size_label = "Tamaño"
        elif kind == "line":
            tam = layer.length
            size_label = "Largo"
        elif kind == "dots":
            tam = layer.spacing
            size_label = "Separación"
        else:
            tam = layer.size
            size_label = "Tamaño"
        self.v_readout.set(
            f"{LABELS[kind]} · X: {layer.x:.3f}  Y: {layer.y:.3f}  {size_label}: {tam:.3f}")

    def _draw_selection_overlay(self):
        self._handles = {}
        if self._selected is None:
            return
        kind = self._kind_of(self._selected)
        if kind is None or kind == "photo":
            return
        bb = self._last_bboxes.get(self._bbox_key_for_layer(self._selected))
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

    def _resize_param_for_kind(self, kind):
        if kind == "line":
            return "length"
        if kind == "dots":
            return "spacing"
        return "size"

    def _start_resize(self, event):
        kind = self._kind_of(self._selected)
        token = self._token_for_layer(self._selected)
        bb = self._last_bboxes.get(self._bbox_key_for_layer(self._selected))
        if not bb:
            return
        x0, y0, x1, y1 = bb
        cx_img, cy_img = (x0 + x1) / 2, (y0 + y1) / 2
        ix, iy = self._canvas_to_img(event.x, event.y)
        start_dist = max(1.0, ((ix - cx_img) ** 2 + (iy - cy_img) ** 2) ** 0.5)
        self._resize = {
            "kind": kind,
            "token": token,
            "center": (cx_img, cy_img),
            "start_dist": start_dist,
            "param": self._resize_param_for_kind(kind),
            "start_value": self._get_layer_value(token, self._resize_param_for_kind(kind)),
        }

    def _apply_resize(self, event):
        kind = self._resize["kind"]
        token = self._resize["token"]
        cx_img, cy_img = self._resize["center"]
        ix, iy = self._canvas_to_img(event.x, event.y)
        dist = max(1.0, ((ix - cx_img) ** 2 + (iy - cy_img) ** 2) ** 0.5)
        ratio = dist / self._resize["start_dist"]
        param = self._resize["param"]
        if param == "length":
            smin, smax = 0.05, 0.80
        elif param == "spacing":
            smin, smax = 0.005, 0.12
        else:
            smin, smax = SIZE_RANGE[kind]
        new_value = min(smax, max(smin, self._resize["start_value"] * ratio))
        self._set_layer_value(token, param, new_value)
        self._sync_sliders()
        self._render_now()

    def _nudge(self, dx_sign, dy_sign, step):
        if self._selected is None:
            return
        if isinstance(self.focus_get(), (tk.Entry, tk.Text)):
            return
        kind = self._kind_of(self._selected)
        if kind == "photo":
            return
        layer = self._selected
        old_x, old_y = layer.x, layer.y
        new_x = min(1.0, max(0.0, layer.x + dx_sign * step))
        new_y = min(1.0, max(0.0, layer.y + dy_sign * step))
        if (new_x, new_y) != (old_x, old_y):
            from .commands import PropertyChangeCommand, CompositeCommand
            self.commands.push(CompositeCommand([
                PropertyChangeCommand(layer, "x", old_x, new_x),
                PropertyChangeCommand(layer, "y", old_y, new_y),
            ]))
            if kind == "logo":
                self._sync_shared_logo_if_active()
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
        self._set_dirty(True)
        self._schedule_render()

    def _sync_format_label(self):
        """Restaura el texto del combobox al formato activo (p.ej. si se cancela el diálogo)."""
        self.v_format.set(self._format_label_for(self.slide.format))

    def _canvas_size_for(self, max_side, fmt=None):
        """Calcula (ancho, alto) en px del lienzo para `fmt` (o el formato de
        la lámina activa si no se pasa), con el lado mayor igual a max_side,
        manteniendo la proporción del formato."""
        formato = fmt if fmt is not None else self.slide.format
        fw, fh = formato["w"], formato["h"]
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
            self._set_dirty(True)
            self._schedule_render()

    def _browse_logo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar logo",
            initialdir=str(SCRIPT_DIR),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")])
        if path:
            self.v_logo.set(path)
            logo_layer = self._layer_by_kind("logo")
            if logo_layer is not None:
                logo_layer.src = path
            self._sync_shared_logo_if_active()
            self._set_dirty(True)
            self._schedule_render()

    # ── Capas actuales: adapta el modelo al dict plano que espera render.py ──
    def _build_layers_for(self, slide):
        """Adapta las capas de `slide` al dict plano que espera render.compose().
        Si `slide` es la lámina activa (self.slide), las capas de foto/logo/
        título/subtítulo/descripción reflejan los widgets en pantalla en vez
        del valor guardado en el modelo (para que la vista previa muestre lo
        que se está tipeando antes de sincronizarlo con _sync_text_to_layers).
        Si el proyecto tiene un logo compartido activo (project.shared["logo"]),
        ese valor pisa el logo propio de la lámina, sea cual sea."""
        es_activa = slide is self.slide
        shared_logo = self.project.shared.get("logo")
        layers = []
        for layer in slide.layers:
            if not layer.visible:
                continue
            if layer.type == "photo":
                src = (self.v_photo.get().strip()
                       if es_activa and layer is self._layer_by_kind("photo", slide) else layer.src)
                layers.append({"type": "photo", "key": layer.id, "src": src,
                                "zoom": layer.zoom, "offset_x": layer.offset_x,
                                "offset_y": layer.offset_y, "opacity": layer.opacity,
                                "adjust": layer.adjust, "overlay": layer.overlay})
            elif layer.type == "logo":
                if shared_logo is not None:
                    layers.append({"type": "logo", "key": layer.id,
                                    "src": shared_logo["src"],
                                    "x": shared_logo["x"], "y": shared_logo["y"],
                                    "size": shared_logo["w"], "opacity": layer.opacity})
                else:
                    src = (self.v_logo.get().strip()
                           if es_activa and layer is self._layer_by_kind("logo", slide) else layer.src)
                    layers.append({"type": "logo", "key": layer.id, "src": src,
                                    "x": layer.x, "y": layer.y, "size": layer.w,
                                    "opacity": layer.opacity})
            elif layer.type == "text" and layer.role == "title":
                text = (self.txt_title.get("1.0", "end-1c")
                        if es_activa and layer is self._layer_by_kind("title", slide) else layer.text)
                layers.append({"type": "title", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity, "rotation": layer.rotation,
                                "font_family": layer.font_family, "bold": layer.bold,
                                "italic": layer.italic, "underline": layer.underline,
                                "line_spacing": layer.line_spacing,
                                "letter_spacing": layer.letter_spacing,
                                "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width})
            elif layer.type == "text" and layer.role == "subtitle":
                text = (self.v_sub.get()
                        if es_activa and layer is self._layer_by_kind("sub", slide) else layer.text)
                layers.append({"type": "sub", "key": layer.id, "text": text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity, "rotation": layer.rotation,
                                "font_family": layer.font_family, "bold": layer.bold,
                                "italic": layer.italic, "underline": layer.underline,
                                "line_spacing": layer.line_spacing,
                                "letter_spacing": layer.letter_spacing,
                                "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width})
            elif layer.type == "text" and layer.role == "free":
                layers.append({"type": "free", "key": layer.id, "text": layer.text,
                                "x": layer.x, "y": layer.y, "size": layer.size,
                                "opacity": layer.opacity, "rotation": layer.rotation,
                                "font_family": layer.font_family, "bold": layer.bold,
                                "italic": layer.italic, "underline": layer.underline,
                                "line_spacing": layer.line_spacing,
                                "letter_spacing": layer.letter_spacing,
                                "stroke_on": layer.stroke_on, "stroke_width": layer.stroke_width,
                                "color": layer.color})
            elif layer.type == "box":
                es_desc_activa = es_activa and layer is self._layer_by_kind("desc", slide)
                text = self.txt_desc.get("1.0", "end-1c") if es_desc_activa else layer.text
                icon = self.v_icon.get() if es_desc_activa else layer.icon
                layers.append({"type": "desc", "key": layer.id, "text": text,
                                "icon": icon, "x": layer.x, "y": layer.y,
                                "w": layer.w, "h": layer.h, "fill": layer.fill,
                                "text_color": layer.text_color,
                                "size": layer.size, "opacity": layer.opacity})
            elif layer.type == "cta":
                layers.append({"type": "cta", "key": layer.id, "text": layer.text,
                                "x": layer.x, "y": layer.y, "w": layer.w, "h": layer.h,
                                "size": layer.size, "fill": layer.fill,
                                "text_color": layer.text_color, "opacity": layer.opacity})
            elif layer.type == "line":
                layers.append({"type": "line", "key": layer.id,
                                "x": layer.x, "y": layer.y,
                                "length": layer.length, "thickness": layer.thickness,
                                "color": layer.color, "gap": layer.gap,
                                "rotation": layer.rotation, "opacity": layer.opacity})
            elif layer.type == "dots":
                layers.append({"type": "dots", "key": layer.id,
                                "x": layer.x, "y": layer.y,
                                "count": len(self.project.slides),
                                "active": self.project.slides.index(slide),
                                "color": layer.color, "spacing": layer.spacing,
                                "opacity": layer.opacity})
        return layers

    def _build_layers(self):
        return self._build_layers_for(self.slide)

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
            self.slides_panel.refresh()
            self.v_status.set("Vista previa lista.")
        except Exception as e:
            self.v_status.set(f"Error: {e}")

    # ── Arrastre ───────────────────────────────────────────────
    def _canvas_to_img(self, ex, ey):
        ox, oy = getattr(self, "_img_origin", (0, 0))
        return ex - ox, ey - oy

    def _start_photo_pan(self, photo_layer, ix, iy):
        """Prepara el arrastre de encuadre (panear) sobre la capa foto."""
        from PIL import Image as _Image
        from .render import excess_for_zoom
        try:
            with _Image.open(photo_layer.src) as im:
                photo_wh = im.size
        except (FileNotFoundError, OSError):
            return
        iw, ih = self._img_wh
        if iw == 0 or ih == 0:
            return
        excess_x, excess_y = excess_for_zoom(photo_wh, (iw, ih), photo_layer.zoom)
        self._drag_elem = "__photo_pan__"
        self._photo_pan = {
            "layer": photo_layer,
            "excess": (excess_x, excess_y),
            "start_offset": (photo_layer.offset_x, photo_layer.offset_y),
            "start_point": (ix, iy),
        }

    def _apply_photo_pan(self, event):
        info = self._photo_pan
        if info is None:
            return
        ix, iy = self._canvas_to_img(event.x, event.y)
        sx, sy = info["start_point"]
        dx, dy = ix - sx, iy - sy
        excess_x, excess_y = info["excess"]
        d_ox, d_oy = _offset_delta_for_drag(dx, dy, excess_x, excess_y)
        start_ox, start_oy = info["start_offset"]
        layer = info["layer"]
        layer.offset_x = min(1.0, max(0.0, start_ox + d_ox))
        layer.offset_y = min(1.0, max(0.0, start_oy + d_oy))
        self._sync_sliders()
        self._render_now()

    def _on_press(self, event):
        self._guides = []
        if self._selected is not None:
            handle = self._handle_at(event.x, event.y)
            if handle is not None:
                self._start_resize(event)
                return

        ix, iy = self._canvas_to_img(event.x, event.y)
        for layer in sorted(self.slide.layers, key=lambda l: l.z, reverse=True):
            kind = self._kind_of(layer)
            if kind is None or kind == "photo" or layer.locked or not layer.visible:
                continue
            bb = self._last_bboxes.get(self._bbox_key_for_layer(layer))
            if bb and bb[0] <= ix <= bb[2] and bb[1] <= iy <= bb[3]:
                self._drag_elem = self._token_for_layer(layer)
                self._drag_off = (ix - bb[0], iy - bb[1])
                self._drag_start_xy = (layer.x, layer.y)
                self._set_selected(layer)
                return

        self._drag_elem = None
        photo_layer = self._layer_by_kind("photo")
        bb_photo = (self._last_bboxes.get(self._bbox_key_for_layer(photo_layer))
                    if photo_layer is not None else None)
        if (photo_layer is not None and not photo_layer.locked and bb_photo
                and bb_photo[0] <= ix <= bb_photo[2] and bb_photo[1] <= iy <= bb_photo[3]):
            self._set_selected(photo_layer)
            self._start_photo_pan(photo_layer, ix, iy)
            return
        self._set_selected(None)

    def _on_drag(self, event):
        if self._resize is not None:
            self._apply_resize(event)
            return
        if self._drag_elem == "__photo_pan__":
            self._apply_photo_pan(event)
            return
        if not self._drag_elem:
            return
        elem = self._drag_elem
        layer = self._layer_by_token(elem)
        kind = self._kind_of(layer)
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

        if kind == "sub":
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
        if self._drag_elem == "__photo_pan__" and self._photo_pan is not None:
            layer = self._photo_pan["layer"]
            start_ox, start_oy = self._photo_pan["start_offset"]
            if (layer.offset_x, layer.offset_y) != (start_ox, start_oy):
                from .commands import PropertyChangeCommand, CompositeCommand
                self.commands.push(CompositeCommand([
                    PropertyChangeCommand(layer, "offset_x", start_ox, layer.offset_x),
                    PropertyChangeCommand(layer, "offset_y", start_oy, layer.offset_y),
                ]))
            self._photo_pan = None
            self._drag_elem = None
            self._resize = None
            self._guides = []
            self._render_now()
            return
        if self._drag_elem and self._drag_start_xy is not None and self._selected is not None:
            old_x, old_y = self._drag_start_xy
            layer = self._selected
            if (layer.x, layer.y) != (old_x, old_y):
                from .commands import PropertyChangeCommand, CompositeCommand
                self.commands.push(CompositeCommand([
                    PropertyChangeCommand(layer, "x", old_x, layer.x),
                    PropertyChangeCommand(layer, "y", old_y, layer.y),
                ]))
                if self._kind_of(layer) == "logo":
                    self._sync_shared_logo_if_active()
        if self._resize is not None and self._selected is not None:
            kind = self._resize["kind"]
            token = self._resize["token"]
            layer = self._layer_by_token(token)
            old_value = self._resize["start_value"]
            if kind == "logo":
                new_w, new_h = layer.w, layer.h
                if (old_value, old_value) != (new_w, new_h):
                    from .commands import PropertyChangeCommand, CompositeCommand
                    self.commands.push(CompositeCommand([
                        PropertyChangeCommand(layer, "w", old_value, new_w),
                        PropertyChangeCommand(layer, "h", old_value, new_h),
                    ]))
                self._sync_shared_logo_if_active()
            else:
                param = self._resize.get("param", "size")
                new_value = self._get_layer_value(token, param)
                if old_value != new_value:
                    from .commands import PropertyChangeCommand
                    self.commands.push(PropertyChangeCommand(layer, param, old_value, new_value))
                    if self._kind_of(layer) == "logo":
                        self._sync_shared_logo_if_active()
        self._drag_elem = None
        self._drag_start_xy = None
        self._resize = None
        self._guides = []
        self._render_now()

    def _on_photo_wheel(self, event):
        photo_layer = self._layer_by_kind("photo")
        if photo_layer is None or photo_layer.locked:
            return
        bb_photo = self._last_bboxes.get(self._bbox_key_for_layer(photo_layer))
        if not bb_photo:
            return
        ix, iy = self._canvas_to_img(event.x, event.y)
        if not (bb_photo[0] <= ix <= bb_photo[2] and bb_photo[1] <= iy <= bb_photo[3]):
            return

        step = 0.1 if event.delta > 0 else -0.1
        old_zoom = photo_layer.zoom
        new_zoom = round(min(3.0, max(1.0, old_zoom + step)), 4)
        if new_zoom == old_zoom:
            return

        if self._wheel_zoom_start is None:
            self._wheel_zoom_start = old_zoom
        photo_layer.zoom = new_zoom
        self._sync_sliders()
        self._render_now()

        if self._wheel_zoom_job is not None:
            self.after_cancel(self._wheel_zoom_job)
        self._wheel_zoom_job = self.after(400, self._commit_wheel_zoom)

    def _commit_wheel_zoom(self):
        self._wheel_zoom_job = None
        if self._wheel_zoom_start is None:
            return
        photo_layer = self._layer_by_kind("photo")
        old_zoom = self._wheel_zoom_start
        self._wheel_zoom_start = None
        if photo_layer is not None and photo_layer.zoom != old_zoom:
            from .commands import PropertyChangeCommand
            self.commands.push(PropertyChangeCommand(photo_layer, "zoom", old_zoom, photo_layer.zoom))

    # ── Guardar / abrir proyecto ────────────────────────────────
    def _save_project(self):
        if self._project_path is None:
            return self._save_project_as()
        self._sync_text_to_layers()
        from .project_io import save_project
        save_project(self.project, self._project_path)
        self._set_dirty(False)
        self.v_status.set(f"✅ Proyecto guardado: {self._project_path.name}")
        return True

    def _save_project_as(self):
        path_str = filedialog.asksaveasfilename(
            title="Guardar proyecto", defaultextension=".json",
            filetypes=[("Proyecto", "*.json")], initialdir=str(SCRIPT_DIR))
        if not path_str:
            return False
        self._project_path = Path(path_str)
        self._sync_text_to_layers()
        from .project_io import save_project
        save_project(self.project, self._project_path)
        self._set_dirty(False)
        self.v_status.set(f"✅ Proyecto guardado: {self._project_path.name}")
        return True

    def _confirm_discard_changes(self):
        """Si hay cambios sin guardar, pregunta qué hacer. Devuelve True si se
        puede continuar con la acción (abrir/cerrar), False si se canceló."""
        if not self._dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Cambios sin guardar", "¿Guardar los cambios antes de continuar?")
        if answer is None:
            return False
        if answer:
            return bool(self._save_project())
        return True

    def _open_project(self):
        if not self._confirm_discard_changes():
            return
        path_str = filedialog.askopenfilename(
            title="Abrir proyecto", filetypes=[("Proyecto", "*.json")],
            initialdir=str(SCRIPT_DIR))
        if not path_str:
            return
        from .project_io import load_project
        loaded = load_project(Path(path_str))
        self.project = loaded
        self.slide = self.project.slides[0]
        self.current_slide_index = 0
        self._project_path = Path(path_str)
        self.commands.clear()
        self._selected = None

        self.v_logo_shared.set("logo" in self.project.shared)
        self._sync_widgets_from_slide()

        self._set_dirty(False)
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()
        self.v_status.set(f"✅ Proyecto abierto: {self._project_path.name}")

    def _import_batch(self):
        """Reemplaza el proyecto actual por un carrusel armado desde una
        carpeta con fotos + un único JSON de copys (dcpub.batch_import)."""
        if not self._confirm_discard_changes():
            return
        carpeta_str = filedialog.askdirectory(
            title="Elegir carpeta con fotos y JSON de copys", initialdir=str(SCRIPT_DIR))
        if not carpeta_str:
            return

        from .batch_import import importar_carrusel_por_lotes
        try:
            project, advertencias = importar_carrusel_por_lotes(
                Path(carpeta_str), dict(self.slide.format))
        except Exception as e:
            messagebox.showerror("Error al importar", str(e))
            return
        if not project.slides:
            messagebox.showerror(
                "Error al importar",
                "No se encontró ninguna foto con entrada correspondiente en el JSON.")
            return

        self.project = project
        self.slide = self.project.slides[0]
        self.current_slide_index = 0
        self._project_path = None
        self.commands.clear()
        self._selected = None

        self.v_logo_shared.set("logo" in self.project.shared)
        self._sync_widgets_from_slide()

        self._set_dirty(True)
        self._build_property_panel()
        self._refresh_layers_list()
        self._schedule_render()
        self.v_status.set(f"✅ Importadas {len(project.slides)} láminas.")

        if advertencias:
            messagebox.showwarning(
                "Importado con advertencias",
                f"{len(advertencias)} advertencia(s):\n\n" + "\n".join(advertencias))

    def _on_close(self):
        if self._confirm_discard_changes():
            self.destroy()

    # ── Exportar en alta resolución ────────────────────────────
    def _choose_export_dir(self):
        path = filedialog.askdirectory(title="Elegir carpeta de destino",
                                        initialdir=self.v_export_dir.get())
        if path:
            self.v_export_dir.set(path)

    def _export(self):
        path = self.v_photo.get().strip()
        if not path:
            messagebox.showerror("Error", "Selecciona una foto primero.")
            return
        if not Path(path).exists():
            messagebox.showerror("Error", f"No se encontró la foto:\n{path}")
            return

        self._sync_text_to_layers()
        self.v_status.set("Exportando imagen en alta resolución…")
        self.update()
        try:
            from .exporter import export_image
            dest_dir = Path(self.v_export_dir.get() or OUTPUT_DIR)
            out_path = export_image(
                self.project, self._build_layers(), self.font_manager,
                dest_dir, fmt=self.v_export_fmt.get())
            self.v_status.set(f"✅  Exportada: {out_path.name}")
            messagebox.showinfo("¡Listo!", f"Imagen exportada en:\n{out_path}")
        except Exception as e:
            self.v_status.set(f"Error: {e}")
            messagebox.showerror("Error al exportar", str(e))

    def _export_all(self):
        self._sync_text_to_layers()
        dest_dir = Path(self.v_export_dir.get() or OUTPUT_DIR)
        self.v_status.set("Exportando todas las láminas…")
        self.update()
        try:
            from .exporter import Exporter
            exporter = Exporter(self.font_manager)
            paths = exporter.exportar_todas(self.project, dest_dir)
            self.v_status.set(f"✅  {len(paths)} láminas exportadas en {dest_dir}")
            messagebox.showinfo("¡Listo!", f"{len(paths)} láminas exportadas en:\n{dest_dir}")
        except Exception as e:
            self.v_status.set(f"Error: {e}")
            messagebox.showerror("Error al exportar todas", str(e))
