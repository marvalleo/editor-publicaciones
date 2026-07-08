"""Motor de render: compone la publicación a partir de una lista de capas."""

from PIL import Image, ImageDraw

from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE

_bg_cache = {"key": None, "img": None}


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


def _apply_opacity(rgba_color, opacity):
    """Multiplica el canal alfa de un color RGB/RGBA por `opacity` (0.0-1.0,
    se recorta a ese rango). Si el color viene sin canal alfa, se asume 255."""
    if len(rgba_color) == 3:
        r, g, b = rgba_color
        a = 255
    else:
        r, g, b, a = rgba_color
    opacity = max(0.0, min(1.0, opacity))
    a = max(0, min(255, round(a * opacity)))
    return (r, g, b, a)


def _get_background(photo_path, canvas_size, zoom=1.0, offset_x=0.5, offset_y=0.5):
    """Recorta la foto tipo "cover" al tamaño exacto del lienzo (sin deformar),
    aplicando zoom y posición de recorte, más el gradiente inferior. Cacheado."""
    Wc, Hc = canvas_size
    key = (str(photo_path), Wc, Hc, round(zoom, 4), round(offset_x, 4), round(offset_y, 4))
    if _bg_cache["key"] == key:
        return _bg_cache["img"].copy()

    photo = Image.open(photo_path).convert("RGBA")
    Wp, Hp = photo.size
    base_scale = max(Wc / Wp, Hc / Hp)
    scale = base_scale * max(1.0, zoom)
    Ws = max(Wc, round(Wp * scale))
    Hs = max(Hc, round(Hp * scale))
    photo = photo.resize((Ws, Hs), Image.LANCZOS)

    excess_x = Ws - Wc
    excess_y = Hs - Hc
    crop_x = int(excess_x * min(1.0, max(0.0, offset_x)))
    crop_y = int(excess_y * min(1.0, max(0.0, offset_y)))
    photo = photo.crop((crop_x, crop_y, crop_x + Wc, crop_y + Hc))

    grad = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    start = int(Hc * 0.34)
    for y in range(start, Hc):
        a = int(150 * min(1.0, (y - start) / max(1, (Hc - start))))
        gd.line([(0, y), (Wc, y)], fill=(0, 0, 0, a))
    photo = Image.alpha_composite(photo, grad)

    _bg_cache["key"] = key
    _bg_cache["img"] = photo
    return photo.copy()


def compose(layers, canvas_size, font_manager):
    """
    Compone la publicación a partir de una lista de capas.

    layers : lista de dicts, cada uno con clave "type":
             - photo : src, zoom (≥1.0, default 1.0), offset_x, offset_y (fracciones
                       0..1, default 0.5) — capa de fondo, se recorta tipo "cover"
                       sin deformar y siempre cubre todo el lienzo.
             - logo  : x,y (esquina sup-izq, frac), size (diámetro, frac. ancho)
             - title : text, x,y (esquina sup-izq, frac), size (alto de fuente, frac. ancho)
             - sub   : text, x (centro horizontal, frac), y (tope, frac), size (fuente, frac)
             - desc  : text, icon, x,y (esquina sup-izq del recuadro, frac), size (fuente, frac)
    canvas_size : (ancho, alto) en px del lienzo final.
    font_manager : instancia de FontManager para cargar las fuentes por rol.

    Devuelve (imagen RGBA, bboxes) donde bboxes[type] = (x0,y0,x1,y1) en px.
    Las capas con texto vacío/blanco no producen bbox. Si no hay capa "photo",
    el lienzo queda transparente (del tamaño pedido) en vez de fallar.
    """
    W, H = canvas_size
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    bboxes = {}

    margin = int(W * 0.055)

    for layer in layers:
        kind = layer["type"]

        if kind == "photo":
            canvas = _get_background(
                layer["src"], (W, H),
                zoom=layer.get("zoom", 1.0),
                offset_x=layer.get("offset_x", 0.5),
                offset_y=layer.get("offset_y", 0.5),
            )
            draw = ImageDraw.Draw(canvas)
            bboxes["photo"] = (0, 0, W, H)

        elif kind == "logo":
            if not LOGO_FILE.exists():
                continue
            lsz = max(20, int(W * layer["size"]))
            try:
                logo = Image.open(str(LOGO_FILE)).convert("RGBA").resize((lsz, lsz), Image.LANCZOS)
                lx = int(layer["x"] * W)
                ly = int(layer["y"] * H)
                canvas.alpha_composite(logo, (lx, ly))
                bboxes["logo"] = (lx, ly, lx + lsz, ly + lsz)
            except Exception:
                pass

        elif kind == "title":
            title = layer["text"]
            if title.strip():
                tsz = max(10, int(W * layer["size"]))
                font_t = font_manager.load("title", tsz)
                tx = int(layer["x"] * W)
                ty = int(layer["y"] * H)
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
                    draw.text((tx + 3, yy + 3), line, font=font_t, fill=(0, 0, 0, 160))
                    draw.text((tx, yy), line, font=font_t, fill=BLANCO + (255,))
                    bb = draw.textbbox((tx, yy), line, font=font_t)
                    widest = max(widest, bb[2] - tx)
                bboxes["title"] = (tx, ty, tx + max(widest, 10), ty + max(1, len(lines)) * lh)

        elif kind == "sub":
            subtitle = layer["text"]
            if subtitle.strip():
                ssz = max(8, int(W * layer["size"]))
                font_s = font_manager.load("subtitle", ssz)
                cx = int(layer["x"] * W)
                sy = int(layer["y"] * H)
                bb = draw.textbbox((0, 0), subtitle, font=font_s)
                sw, sh = bb[2] - bb[0], bb[3] - bb[1]
                sx = cx - sw // 2
                ly = sy + sh // 2
                lw_deco = max(2, int(W * 0.003))
                line_len = int(W * 0.11)
                gap = int(W * 0.03)
                lx1 = max(0, sx - gap - line_len)
                draw.line([(lx1, ly), (sx - gap, ly)], fill=VERDE, width=lw_deco)
                rx2 = min(W, sx + sw + gap + line_len)
                draw.line([(sx + sw + gap, ly), (rx2, ly)], fill=VERDE, width=lw_deco)
                draw.text((sx + 2, sy + 2), subtitle, font=font_s, fill=(0, 0, 0, 130))
                draw.text((sx, sy), subtitle, font=font_s, fill=VERDE)
                bboxes["sub"] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)

        elif kind == "desc":
            description = layer["text"]
            if description.strip():
                bsz = max(8, int(W * layer["size"]))
                font_b = font_manager.load("body", bsz)
                box_w = int(W * 0.90)
                bx = int(layer["x"] * W)
                by = int(layer["y"] * H)
                bx = max(0, min(bx, W - box_w))
                corner_r = int(W * 0.033)
                pad = int(W * 0.04)

                icon = layer["icon"]
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
