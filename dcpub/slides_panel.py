"""Panel de miniaturas de láminas del carrusel (panel izquierdo)."""

import tkinter as tk
from tkinter import simpledialog

from PIL import Image, ImageTk

from .render import compose

THUMB_MAX_SIDE = 120


class SlidesPanel(tk.Frame):
    """Lista vertical scrolleable de miniaturas de las láminas del proyecto
    activo, con acciones de agregar/duplicar/eliminar/reordenar/copiar
    estilo. Depende de `app` únicamente a través de su interfaz pública:
    app.project, app.current_slide_index, app.font_manager,
    app.switch_to_slide(index), app._add_slide(), app._duplicate_slide(),
    app._delete_slide(), app._move_slide(direction),
    app._copy_style_to_slide(origen_slide, destino_index),
    app._build_layers_for(slide), app._canvas_size_for(max_side, fmt)."""

    def __init__(self, parent, app, bg, panel_bg, accent, text_color, muted_color):
        super().__init__(parent, bg=panel_bg)
        self.app = app
        self._bg = panel_bg
        self._accent = accent
        self._text = text_color
        self._muted = muted_color
        self._thumb_cache = {}  # id(slide) -> (firma, ImageTk.PhotoImage)
        self._build()

    def _build(self):
        tk.Label(self, text="🎞  Láminas", bg=self._bg, fg=self._text,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 2))

        list_container = tk.Frame(self, bg=self._bg)
        list_container.pack(fill=tk.X)
        scroll_canvas = tk.Canvas(list_container, bg=self._bg, highlightthickness=0, height=260)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=scroll_canvas.yview)
        self._rows_frame = tk.Frame(scroll_canvas, bg=self._bg)
        rows_window = scroll_canvas.create_window((0, 0), window=self._rows_frame, anchor="nw")
        self._rows_frame.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind(
            "<Configure>", lambda e: scroll_canvas.itemconfig(rows_window, width=e.width))
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions = tk.Frame(self, bg=self._bg)
        actions.pack(fill=tk.X, pady=(4, 4))
        tk.Button(actions, text="+ Agregar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=self.app._add_slide).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(actions, text="⧉ Duplicar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=self.app._duplicate_slide).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        tk.Button(actions, text="🗑 Eliminar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=self.app._delete_slide).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        order_row = tk.Frame(self, bg=self._bg)
        order_row.pack(fill=tk.X, pady=(0, 6))
        tk.Button(order_row, text="▲ Subir", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=lambda: self.app._move_slide(-1)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        tk.Button(order_row, text="▼ Bajar", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 8), command=lambda: self.app._move_slide(1)).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        self.refresh()

    def refresh(self):
        """Reconstruye la lista de miniaturas a partir de app.project.slides."""
        for w in self._rows_frame.winfo_children():
            w.destroy()
        for index, slide in enumerate(self.app.project.slides):
            self._build_row(index, slide)

    def _build_row(self, index, slide):
        is_active = index == self.app.current_slide_index
        row_bg = "#3a4a2f" if is_active else self._bg
        row = tk.Frame(self._rows_frame, bg=row_bg,
                        highlightbackground=self._accent if is_active else row_bg,
                        highlightthickness=2)
        row.pack(fill=tk.X, pady=2, padx=2)

        thumb = self._thumbnail_for(slide)
        label = tk.Label(row, image=thumb, bg=row_bg)
        label.image = thumb  # evita que el GC se lleve la imagen
        label.pack(side=tk.LEFT, padx=4, pady=4)
        label.bind("<Button-1>", lambda e, i=index: self.app.switch_to_slide(i))

        info = tk.Frame(row, bg=row_bg)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(info, text=f"Lámina {index + 1}", bg=row_bg, fg=self._text,
                 font=("Segoe UI", 8)).pack(anchor="w")
        tk.Button(info, text="Copiar estilo →", bg="#3d3d3d", fg=self._text, relief="flat",
                  font=("Segoe UI", 7), command=lambda i=index: self._copy_style_dialog(i)).pack(
            anchor="w")

    def _copy_style_dialog(self, origen_index):
        total = len(self.app.project.slides)
        destino = simpledialog.askinteger(
            "Copiar estilo", f"Lámina destino (1-{total}):",
            minvalue=1, maxvalue=total, parent=self)
        if destino is None:
            return
        origen_slide = self.app.project.slides[origen_index]
        self.app._copy_style_to_slide(origen_slide, destino - 1)
        self.refresh()

    def _thumbnail_for(self, slide):
        firma = (slide.to_dict(), self.app.project.shared.get("logo"))
        cache_key = id(slide)
        cached = self._thumb_cache.get(cache_key)
        if cached is not None and cached[0] == firma:
            return cached[1]
        canvas_size = self.app._canvas_size_for(THUMB_MAX_SIDE, slide.format)
        try:
            img, _ = compose(self.app._build_layers_for(slide), canvas_size, self.app.font_manager)
            img = img.convert("RGB")
        except Exception as e:
            # Todavía no hay foto válida (p.ej. recién abierta la app, sin
            # elegir imagen): mostrar un placeholder en vez de romper la UI.
            print(f"Advertencia: no se pudo componer miniatura de lámina: {e}")
            img = Image.new("RGB", canvas_size, "#3d3d3d")
        imgtk = ImageTk.PhotoImage(img)
        self._thumb_cache[cache_key] = (firma, imgtk)
        return imgtk
