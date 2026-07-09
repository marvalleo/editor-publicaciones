"""Motor de render: compone la publicación a partir de una lista de capas."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE

_bg_cache = {"key": None, "img": None}

DEFAULT_ADJUST = {
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "warmth": 0.0,
    "sharpness": 1.0,
    "shadows": 0.0,
    "vignette": 0.0,
}

DEFAULT_OVERLAY = {
    "bottom_grad": False,
    "top_grad": False,
    "strength": 0.0,
}

DEFAULT_PALETTE = {
    "box": list(BOX_COLOR),
}


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


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _normalized_adjust(adjust):
    values = dict(DEFAULT_ADJUST)
    if adjust:
        values.update(adjust)
    return values


def _normalized_overlay(overlay):
    values = dict(DEFAULT_OVERLAY)
    if overlay:
        values.update(overlay)
    return values


def _adjust_cache_tuple(values):
    return (
        round(float(values["brightness"]), 4),
        round(float(values["contrast"]), 4),
        round(float(values["saturation"]), 4),
        round(float(values["warmth"]), 4),
        round(float(values["sharpness"]), 4),
        round(float(values["shadows"]), 4),
        round(float(values["vignette"]), 4),
    )


def _overlay_cache_tuple(values):
    return (
        bool(values["bottom_grad"]),
        bool(values["top_grad"]),
        round(float(values["strength"]), 4),
    )


def _overlay_color_from_palette(palette):
    values = palette or DEFAULT_PALETTE
    color = values.get("sombra") or values.get("box") or DEFAULT_PALETTE["box"]
    if len(color) == 3:
        r, g, b = color
        a = 255
    else:
        r, g, b, a = color
    return (int(r), int(g), int(b), int(a))


def _apply_warmth(photo, warmth):
    warmth = _clamp(float(warmth), -1.0, 1.0)
    if warmth == 0.0:
        return photo
    r, g, b, a = photo.split()
    shift = int(45 * warmth)
    r = r.point(lambda px, s=shift: _clamp(px + s, 0, 255))
    b = b.point(lambda px, s=shift: _clamp(px - s, 0, 255))
    return Image.merge("RGBA", (r, g, b, a))


def _apply_shadows(photo, amount):
    amount = _clamp(float(amount), -1.0, 1.0)
    if amount == 0.0:
        return photo
    rgb = photo.convert("RGB")
    gray = rgb.convert("L")
    mask = gray.point(lambda px: max(0, 180 - px))
    mask = ImageEnhance.Contrast(mask).enhance(1.8).filter(ImageFilter.GaussianBlur(2))
    if amount > 0:
        adjusted = ImageEnhance.Brightness(rgb).enhance(1.0 + amount)
    else:
        adjusted = ImageEnhance.Brightness(rgb).enhance(1.0 + amount * 0.5)
    blended = Image.composite(adjusted, rgb, mask)
    blended.putalpha(photo.getchannel("A"))
    return blended


def _apply_vignette(photo, amount):
    amount = _clamp(float(amount), 0.0, 1.0)
    if amount == 0.0:
        return photo
    w, h = photo.size
    cx, cy = w / 2, h / 2
    max_dist = (cx ** 2 + cy ** 2) ** 0.5
    alpha = Image.new("L", (w, h), 0)
    pixels = alpha.load()
    for y in range(h):
        for x in range(w):
            dist = (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / max_dist
            edge = max(0.0, (dist - 0.35) / 0.65)
            pixels[x, y] = int(210 * amount * edge)
    blur = max(1, int(min(w, h) * 0.03))
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dark.putalpha(alpha.filter(ImageFilter.GaussianBlur(blur)))
    return Image.alpha_composite(photo, dark)


def _apply_photo_adjustments(photo, adjust):
    values = _normalized_adjust(adjust)
    if values["brightness"] != 1.0:
        photo = ImageEnhance.Brightness(photo).enhance(float(values["brightness"]))
    if values["contrast"] != 1.0:
        photo = ImageEnhance.Contrast(photo).enhance(float(values["contrast"]))
    if values["saturation"] != 1.0:
        photo = ImageEnhance.Color(photo).enhance(float(values["saturation"]))
    photo = _apply_warmth(photo, values["warmth"])
    if values["sharpness"] != 1.0:
        photo = ImageEnhance.Sharpness(photo).enhance(float(values["sharpness"]))
    photo = _apply_shadows(photo, values["shadows"])
    photo = _apply_vignette(photo, values["vignette"])
    return photo


def _apply_photo_overlay(photo, overlay, palette=None):
    values = _normalized_overlay(overlay)
    strength = _clamp(float(values["strength"]), 0.0, 1.0)
    if strength == 0.0 or not (values["bottom_grad"] or values["top_grad"]):
        return photo
    w, h = photo.size
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(grad)
    r, g, b, base_alpha = _overlay_color_from_palette(palette)
    max_alpha = int(base_alpha * strength)
    if values["bottom_grad"]:
        start = int(h * 0.35)
        for y in range(start, h):
            alpha = int(max_alpha * ((y - start) / max(1, h - start)))
            draw.line([(0, y), (w, y)], fill=(r, g, b, alpha))
    if values["top_grad"]:
        end = int(h * 0.45)
        for y in range(0, end):
            alpha = int(max_alpha * (1.0 - y / max(1, end)))
            draw.line([(0, y), (w, y)], fill=(r, g, b, alpha))
    return Image.alpha_composite(photo, grad)


def excess_for_zoom(photo_wh, canvas_wh, zoom):
    """Devuelve (excess_x, excess_y): cuántos px de la foto escalada sobran
    más allá del lienzo para el zoom/tamaño dados. Misma matemática que usa
    _get_background al recortar tipo "cover", expuesta para que la UI pueda
    traducir un arrastre de mouse a un delta de offset_x/offset_y."""
    Wp, Hp = photo_wh
    Wc, Hc = canvas_wh
    base_scale = max(Wc / Wp, Hc / Hp)
    scale = base_scale * max(1.0, zoom)
    Ws = max(Wc, round(Wp * scale))
    Hs = max(Hc, round(Hp * scale))
    return (Ws - Wc, Hs - Hc)


def _get_background(photo_path, canvas_size, zoom=1.0, offset_x=0.5, offset_y=0.5,
                    adjust=None, overlay=None, palette=None):
    """Recorta la foto tipo "cover" al tamaño exacto del lienzo (sin deformar),
    aplicando zoom y posición de recorte, más el gradiente inferior. Cacheado."""
    Wc, Hc = canvas_size
    adjust_values = _normalized_adjust(adjust)
    overlay_values = _normalized_overlay(overlay)
    key = (
        str(photo_path), Wc, Hc, round(zoom, 4),
        round(offset_x, 4), round(offset_y, 4),
        _adjust_cache_tuple(adjust_values),
        _overlay_cache_tuple(overlay_values),
        _overlay_color_from_palette(palette),
    )
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
    photo = _apply_photo_adjustments(photo, adjust_values)
    photo = _apply_photo_overlay(photo, overlay_values, palette=palette)

    _bg_cache["key"] = key
    _bg_cache["img"] = photo
    return photo.copy()


def compose(layers, canvas_size, font_manager, palette=None):
    """
    Compone la publicación a partir de una lista de capas.

    layers : lista de dicts, cada uno con clave "type" y una clave opcional
             "opacity" (0.0-1.0, default 1.0) que se aplica a esa capa:
             - photo : src, zoom (≥1.0, default 1.0), offset_x, offset_y (fracciones
                       0..1, default 0.5) — capa de fondo, se recorta tipo "cover"
                       sin deformar y siempre cubre todo el lienzo.
             - logo  : x,y (esquina sup-izq, frac), size (diámetro, frac. ancho)
             - title : text, x,y (esquina sup-izq, frac), size (alto de fuente, frac. ancho)
             - sub   : text, x (centro horizontal, frac), y (tope, frac), size (fuente, frac)
             - desc  : text, icon, x,y (esquina sup-izq del recuadro, frac), size (fuente, frac)
    canvas_size : (ancho, alto) en px del lienzo final.
    font_manager : instancia de FontManager para cargar las fuentes por rol.

    Devuelve (imagen RGBA, bboxes) donde bboxes[key] = (x0,y0,x1,y1) en px.
    Si la capa no trae "key", se usa su "type" para mantener compatibilidad.
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
        bbox_key = layer.get("key", kind)
        opacity = layer.get("opacity", 1.0)

        if kind == "photo":
            bg = _get_background(
                layer["src"], (W, H),
                zoom=layer.get("zoom", 1.0),
                offset_x=layer.get("offset_x", 0.5),
                offset_y=layer.get("offset_y", 0.5),
                adjust=layer.get("adjust"),
                overlay=layer.get("overlay"),
                palette=palette,
            )
            if opacity < 1.0:
                r, g, b, a = bg.split()
                a = a.point(lambda px, op=opacity: int(px * max(0.0, min(1.0, op))))
                bg = Image.merge("RGBA", (r, g, b, a))
                canvas = Image.alpha_composite(canvas, bg)
            else:
                canvas = bg
            draw = ImageDraw.Draw(canvas)
            bboxes[bbox_key] = (0, 0, W, H)

        elif kind == "logo":
            logo_path = Path(layer.get("src") or LOGO_FILE)
            if not logo_path.exists():
                continue
            lsz = max(20, int(W * layer["size"]))
            try:
                logo = Image.open(str(logo_path)).convert("RGBA").resize((lsz, lsz), Image.LANCZOS)
                if opacity < 1.0:
                    r, g, b, a = logo.split()
                    a = a.point(lambda px, op=opacity: int(px * max(0.0, min(1.0, op))))
                    logo = Image.merge("RGBA", (r, g, b, a))
                lx = int(layer["x"] * W)
                ly = int(layer["y"] * H)
                canvas.alpha_composite(logo, (lx, ly))
                bboxes[bbox_key] = (lx, ly, lx + lsz, ly + lsz)
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
                shadow_color = _apply_opacity((0, 0, 0, 160), opacity)
                text_color = _apply_opacity(BLANCO + (255,), opacity)
                if opacity < 1.0:
                    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    text_draw = ImageDraw.Draw(text_layer)
                    for i, line in enumerate(lines):
                        yy = ty + i * lh
                        text_draw.text((tx + 3, yy + 3), line, font=font_t, fill=shadow_color)
                        text_draw.text((tx, yy), line, font=font_t, fill=text_color)
                        bb = draw.textbbox((tx, yy), line, font=font_t)
                        widest = max(widest, bb[2] - tx)
                    canvas = Image.alpha_composite(canvas, text_layer)
                    draw = ImageDraw.Draw(canvas)
                else:
                    for i, line in enumerate(lines):
                        yy = ty + i * lh
                        draw.text((tx + 3, yy + 3), line, font=font_t, fill=shadow_color)
                        draw.text((tx, yy), line, font=font_t, fill=text_color)
                        bb = draw.textbbox((tx, yy), line, font=font_t)
                        widest = max(widest, bb[2] - tx)
                bboxes[bbox_key] = (tx, ty, tx + max(widest, 10), ty + max(1, len(lines)) * lh)

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
                rx2 = min(W, sx + sw + gap + line_len)
                line_color = _apply_opacity(VERDE, opacity)
                deco_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                deco_draw = ImageDraw.Draw(deco_layer)
                deco_draw.line([(lx1, ly), (sx - gap, ly)], fill=line_color, width=lw_deco)
                deco_draw.line([(sx + sw + gap, ly), (rx2, ly)], fill=line_color, width=lw_deco)
                canvas = Image.alpha_composite(canvas, deco_layer)
                draw = ImageDraw.Draw(canvas)
                if opacity < 1.0:
                    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    text_draw = ImageDraw.Draw(text_layer)
                    text_draw.text((sx + 2, sy + 2), subtitle, font=font_s,
                                   fill=_apply_opacity((0, 0, 0, 130), opacity))
                    text_draw.text((sx, sy), subtitle, font=font_s, fill=line_color)
                    canvas = Image.alpha_composite(canvas, text_layer)
                    draw = ImageDraw.Draw(canvas)
                else:
                    draw.text((sx + 2, sy + 2), subtitle, font=font_s,
                              fill=_apply_opacity((0, 0, 0, 130), opacity))
                    draw.text((sx, sy), subtitle, font=font_s, fill=line_color)
                bboxes[bbox_key] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)

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
                box_fill = _apply_opacity(BOX_COLOR, opacity)
                bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                                     radius=corner_r, fill=box_fill)
                canvas = Image.alpha_composite(canvas, box_layer)
                draw = ImageDraw.Draw(canvas)

                icon_color = _apply_opacity(VERDE, opacity)
                text_color = _apply_opacity(BLANCO + (255,), opacity)
                if icon != "ninguno":
                    iy = by + (box_h - icon_sz) // 2
                    icon_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    icon_draw = ImageDraw.Draw(icon_layer)
                    draw_icon(icon_draw, bx + pad, iy, icon_sz, icon, icon_color)
                    canvas = Image.alpha_composite(canvas, icon_layer)
                    draw = ImageDraw.Draw(canvas)

                dy = by + (box_h - text_h) // 2
                text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                for i, l in enumerate(dlines):
                    text_draw.text((text_x, dy + i * dlh), l, font=font_b, fill=text_color)
                canvas = Image.alpha_composite(canvas, text_layer)
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)

    return canvas, bboxes
