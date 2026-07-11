"""Motor de render: compone la publicación a partir de una lista de capas."""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE, TEXT_STROKE_COLOR

_bg_cache = {"key": None, "img": None}

ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"

ICON_IMAGE_FILES = {
    "planta": "planta.png",
    "montaña": "montana.png",
    "corazón": "corazon.png",
    "cabaña": "cabana.png",
    "fuego": "fuego.png",
    "río": "rio.png",
    "estrella": "estrella.png",
    "sol": "sol.png",
    "árbol": "arbol.png",
    "taza": "taza.png",
    "tinaja": "tinaja.png",
    "cama": "cama.png",
    "familia": "familia.png",
    "cubiertos": "cubiertos.png",
    "mapa": "mapa.png",
    "nieve": "nieve.png",
}

_icon_mask_cache = {}


def _icon_mask(name):
    """Carga y cachea el canal alfa (silueta pura, sin color horneado) del
    ícono de imagen `name`, para poder recolorearlo dinámicamente igual
    que los íconos dibujados a mano."""
    cached = _icon_mask_cache.get(name)
    if cached is not None:
        return cached
    mask = Image.open(ICONS_DIR / ICON_IMAGE_FILES[name]).convert("RGBA").split()[-1]
    _icon_mask_cache[name] = mask
    return mask


def _fit_mask(mask, size):
    """Reescala `mask` para que quepa dentro de un lienzo size x size
    preservando su relación de aspecto original (las imágenes fuente no
    son cuadradas), centrado, con relleno transparente alrededor."""
    src_w, src_h = mask.size
    scale = min(size / src_w, size / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    resized = mask.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(resized, ((size - new_w) // 2, (size - new_h) // 2))
    return canvas

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


def draw_icon(size, icon_type, color):
    """Devuelve un ícono de marca de `size`x`size`, listo para componer
    con `canvas.alpha_composite(img, (x, y))`: recolorea dinámicamente
    con `color` la silueta (canal alfa) de la imagen fuente del ícono en
    ICON_IMAGE_FILES."""
    mask = _fit_mask(_icon_mask(icon_type), size)
    img = Image.new("RGBA", (size, size), color)
    img.putalpha(ImageChops.multiply(img.split()[-1], mask))
    return img


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


BOLD_STROKE_FRACTION = 0.06  # grosor sintetico extra cuando bold=True, fraccion del tamaño de fuente


def _measure_line_width(draw_ctx, text, font, letter_spacing_px):
    """Ancho en px de `text` con `font`, sumando `letter_spacing_px` entre
    cada caracter. Con letter_spacing_px=0 equivale a textbbox normal."""
    if letter_spacing_px == 0:
        bbox = draw_ctx.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    total = 0
    for ch in text:
        bbox = draw_ctx.textbbox((0, 0), ch, font=font)
        total += (bbox[2] - bbox[0]) + letter_spacing_px
    return max(0, total - letter_spacing_px)


def _draw_tracked_line(draw_ctx, xy, text, font, fill, letter_spacing_px,
                        stroke_width=0, stroke_fill=None):
    """Dibuja `text` en `xy` con tracking manual si letter_spacing_px != 0
    (caracter por caracter); si es 0, usa draw.text normal (camino rapido,
    sin cambio de comportamiento respecto al codigo legado)."""
    if letter_spacing_px == 0:
        draw_ctx.text(xy, text, font=font, fill=fill,
                       stroke_width=stroke_width, stroke_fill=stroke_fill)
        return
    x, y = xy
    for ch in text:
        draw_ctx.text((x, y), ch, font=font, fill=fill,
                       stroke_width=stroke_width, stroke_fill=stroke_fill)
        bbox = draw_ctx.textbbox((0, 0), ch, font=font)
        x += (bbox[2] - bbox[0]) + letter_spacing_px


def _render_text_lines_to_image(lines, font, *, fill, line_height,
                                 letter_spacing_px=0, stroke_width=0,
                                 stroke_fill=None, underline=False,
                                 shadow_offset=None, shadow_fill=None,
                                 align="left"):
    """Renderiza `lines` (lista de strings, una por linea) a una imagen RGBA
    ajustada al contenido, con tracking/stroke/subrayado/sombra ya
    horneados. No aplica italica ni rotacion (eso se hace despues, sobre la
    imagen devuelta). Devuelve (imagen, pad), donde `pad` es el margen
    interno agregado a cada lado (necesario para que el stroke no se corte
    en los bordes) — quien llama debe restar `pad` de la posicion de anclaje
    original al pegar la imagen resultante en el lienzo."""
    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe)
    widths = [_measure_line_width(probe_draw, line, font, letter_spacing_px)
              for line in lines]
    block_w = max(widths, default=0)
    pad = max(4, stroke_width * 2 + 4)
    block_h = max(1, len(lines)) * line_height

    img = Image.new("RGBA", (block_w + pad * 2, block_h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (line, lw) in enumerate(zip(lines, widths)):
        ly = pad + i * line_height
        lx = pad if align == "left" else pad + (block_w - lw) // 2
        if shadow_offset:
            dx, dy = shadow_offset
            _draw_tracked_line(d, (lx + dx, ly + dy), line, font,
                                shadow_fill, letter_spacing_px)
        _draw_tracked_line(d, (lx, ly), line, font, fill, letter_spacing_px,
                            stroke_width=stroke_width, stroke_fill=stroke_fill)
        if underline:
            uy = ly + line_height - max(1, int(line_height * 0.08))
            d.line([(lx, uy), (lx + lw, uy)], fill=fill,
                   width=max(1, int(line_height * 0.05)))
    return img, pad


def _apply_italic_shear(img, factor=0.22):
    """Inclina `img` horizontalmente (shear) para simular itálica. `factor`
    es la pendiente del corte (positivo = inclina hacia la derecha arriba)."""
    w, h = img.size
    xshift = int(round(abs(factor) * h))
    new_w = w + xshift
    coeffs = (1, factor, -xshift if factor > 0 else 0, 0, 1, 0)
    return img.transform((new_w, h), Image.AFFINE, coeffs, resample=Image.BICUBIC)


def _apply_rotation(img, degrees):
    """Rota `img` `degrees` grados (sentido horario positivo), expandiendo
    el lienzo para no recortar contenido. Sin cambios si degrees es 0."""
    if not degrees:
        return img
    return img.rotate(-degrees, expand=True, resample=Image.BICUBIC)


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
             - cta   : text, x,y (esquina sup-izq, frac), w,h (frac), size (fuente, frac),
                       fill (rgba), text_color (rgba) — sin ícono, texto centrado
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
                has_rich_text = any(layer.get(k) for k in ["font_family", "bold", "italic", "underline", "letter_spacing", "stroke_on", "rotation"]) or layer.get("line_spacing", 0)

                if has_rich_text:
                    # Nuevo pipeline de texto rico
                    font_t = font_manager.load("title", tsz, family=layer.get("font_family", ""))
                    tx = int(layer["x"] * W)
                    ty = int(layer["y"] * H)
                    max_w = W - tx - margin
                    lines = []
                    for part in title.split("\n"):
                        part = part.strip()
                        if part:
                            lines += wrap_text(part, font_t, max_w, draw)
                    line_spacing = layer.get("line_spacing", 0) or 1.22
                    lh = int(tsz * line_spacing)
                    letter_spacing_px = int(tsz * layer.get("letter_spacing", 0))
                    bold = layer.get("bold", False)
                    stroke_on = layer.get("stroke_on", False)
                    border_px = int(tsz * layer.get("stroke_width", 0)) if stroke_on else 0
                    bold_px = int(tsz * BOLD_STROKE_FRACTION) if bold else 0
                    stroke_width_total = border_px + bold_px

                    shadow_color = _apply_opacity((0, 0, 0, 160), opacity)
                    text_color = _apply_opacity(BLANCO + (255,), opacity)
                    stroke_fill = (_apply_opacity(TEXT_STROKE_COLOR, opacity)
                                   if stroke_on else text_color)

                    block, pad = _render_text_lines_to_image(
                        lines, font_t, fill=text_color, line_height=lh,
                        letter_spacing_px=letter_spacing_px,
                        stroke_width=stroke_width_total, stroke_fill=stroke_fill,
                        underline=layer.get("underline", False),
                        shadow_offset=(3, 3), shadow_fill=shadow_color, align="left")

                    pre_w, pre_h = block.size
                    center_x = (tx - pad) + pre_w / 2
                    center_y = (ty - pad) + pre_h / 2

                    if layer.get("italic", False):
                        block = _apply_italic_shear(block)
                    rotation = layer.get("rotation", 0.0)
                    if rotation:
                        block = _apply_rotation(block, rotation)

                    paste_x = int(center_x - block.width / 2)
                    paste_y = int(center_y - block.height / 2)
                    canvas.alpha_composite(block, (paste_x, paste_y))
                    draw = ImageDraw.Draw(canvas)

                    widest = pre_w - 2 * pad
                    bboxes[bbox_key] = (tx, ty, tx + max(widest, 10), ty + max(pre_h - 2 * pad, 1))
                else:
                    # Legacy fast path: mantiene pixel-identical behavior cuando todos los campos de rich text están en default
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
                has_rich_text = any(layer.get(k) for k in ["font_family", "bold", "italic", "underline", "letter_spacing", "stroke_on", "rotation"])

                if has_rich_text:
                    # Nuevo pipeline de texto rico
                    font_s = font_manager.load("subtitle", ssz, family=layer.get("font_family", ""))
                    cx = int(layer["x"] * W)
                    sy = int(layer["y"] * H)
                    letter_spacing_px = int(ssz * layer.get("letter_spacing", 0))
                    probe_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
                    sw = _measure_line_width(probe_draw, subtitle, font_s, letter_spacing_px)
                    bb = draw.textbbox((0, 0), subtitle, font=font_s)
                    sh = bb[3] - bb[1]
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

                    bold = layer.get("bold", False)
                    stroke_on = layer.get("stroke_on", False)
                    border_px = int(ssz * layer.get("stroke_width", 0)) if stroke_on else 0
                    bold_px = int(ssz * BOLD_STROKE_FRACTION) if bold else 0
                    stroke_width_total = border_px + bold_px
                    stroke_fill = (_apply_opacity(TEXT_STROKE_COLOR, opacity)
                                   if stroke_on else line_color)

                    block, pad = _render_text_lines_to_image(
                        [subtitle], font_s, fill=line_color, line_height=sh,
                        letter_spacing_px=letter_spacing_px,
                        stroke_width=stroke_width_total, stroke_fill=stroke_fill,
                        underline=layer.get("underline", False),
                        shadow_offset=(2, 2),
                        shadow_fill=_apply_opacity((0, 0, 0, 130), opacity), align="left")

                    pre_w, pre_h = block.size
                    center_x = (sx - pad) + pre_w / 2
                    center_y = (sy - pad) + pre_h / 2

                    if layer.get("italic", False):
                        block = _apply_italic_shear(block)
                    rotation = layer.get("rotation", 0.0)
                    if rotation:
                        block = _apply_rotation(block, rotation)

                    paste_x = int(center_x - block.width / 2)
                    paste_y = int(center_y - block.height / 2)
                    canvas.alpha_composite(block, (paste_x, paste_y))
                    draw = ImageDraw.Draw(canvas)

                    bboxes[bbox_key] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)
                else:
                    # Legacy fast path: mantiene pixel-identical behavior cuando todos los campos de rich text están en default
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

        elif kind == "line":
            cx = int(layer.get("x", 0.5) * W)
            cy = int(layer.get("y", 0.5) * H)
            length_px = max(1, int(W * layer.get("length", 0.22)))
            thickness_px = max(1, int(W * layer.get("thickness", 0.003)))
            gap_px = max(0, int(W * layer.get("gap", 0.0)))
            line_color = _apply_opacity(layer.get("color", VERDE + (255,)), opacity)

            line_w = length_px
            line_h = thickness_px
            if gap_px > 0:
                line_w = max(length_px, gap_px + 2)
            line_img = Image.new("RGBA", (line_w, line_h), (0, 0, 0, 0))
            line_draw = ImageDraw.Draw(line_img)
            y_mid = line_h // 2
            if gap_px > 0:
                left_end = max(0, (line_w - gap_px) // 2)
                right_start = min(line_w, left_end + gap_px)
                if left_end > 0:
                    line_draw.line([(0, y_mid), (left_end, y_mid)], fill=line_color, width=thickness_px)
                if right_start < line_w:
                    line_draw.line([(right_start, y_mid), (line_w, y_mid)], fill=line_color, width=thickness_px)
            else:
                line_draw.line([(0, y_mid), (line_w, y_mid)], fill=line_color, width=thickness_px)

            rotation = layer.get("rotation", 0.0)
            rotated = _apply_rotation(line_img, rotation)
            px = int(cx - rotated.width / 2)
            py = int(cy - rotated.height / 2)
            canvas.alpha_composite(rotated, (px, py))
            draw = ImageDraw.Draw(canvas)
            bboxes[bbox_key] = (px, py, px + rotated.width, py + rotated.height)

        elif kind == "dots":
            count = max(0, int(layer.get("count", 0)))
            if count <= 0:
                continue
            active = int(layer.get("active", 0))
            cx = int(layer.get("x", 0.5) * W)
            cy = int(layer.get("y", 0.5) * H)
            spacing_px = max(1, int(W * layer.get("spacing", 0.025)))
            # El radio de marca (fraccion de W) es el tamaño preferido, pero
            # se recorta al spacing disponible para que los puntos nunca se
            # superpongan entre si, sea cual sea el spacing elegido.
            base_r = max(2, min(int(W * 0.035), int(spacing_px * 0.28)))
            active_r = max(base_r + 1, min(int(W * 0.065), int(spacing_px * 0.45)))
            if count > 1:
                active_r = min(active_r, max(base_r + 1, spacing_px - base_r))
            total_w = spacing_px * (count - 1) + active_r * 2
            total_h = active_r * 2
            dots_layer = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
            dots_draw = ImageDraw.Draw(dots_layer)
            dot_color = _apply_opacity(layer.get("color", VERDE + (255,)), opacity)
            start_x = active_r
            center_y = total_h // 2
            for i in range(count):
                radius = active_r if i == active else base_r
                dx = start_x + i * spacing_px
                dots_draw.ellipse(
                    [(dx - radius, center_y - radius), (dx + radius, center_y + radius)],
                    fill=dot_color,
                )
            px = int(cx - total_w / 2)
            py = int(cy - total_h / 2)
            canvas.alpha_composite(dots_layer, (px, py))
            draw = ImageDraw.Draw(canvas)
            bboxes[bbox_key] = (px, py, px + total_w, py + total_h)

        elif kind == "free":
            text = layer["text"]
            if text.strip():
                tsz = max(8, int(W * layer.get("size", 0.05)))
                font_f = font_manager.load("body", tsz, family=layer.get("font_family", ""))
                tx = int(layer["x"] * W)
                ty = int(layer["y"] * H)
                max_w = W - tx - margin
                lines = []
                for part in text.split("\n"):
                    part = part.strip()
                    if part:
                        lines += wrap_text(part, font_f, max_w, draw)
                line_spacing = layer.get("line_spacing", 0) or 1.22
                lh = int(tsz * line_spacing)
                letter_spacing_px = int(tsz * layer.get("letter_spacing", 0))
                bold = layer.get("bold", False)
                stroke_on = layer.get("stroke_on", False)
                border_px = int(tsz * layer.get("stroke_width", 0)) if stroke_on else 0
                bold_px = int(tsz * BOLD_STROKE_FRACTION) if bold else 0
                stroke_width_total = border_px + bold_px

                text_color_value = layer.get("color", BLANCO + (255,))
                text_color = _apply_opacity(text_color_value, opacity)
                stroke_fill = (_apply_opacity(TEXT_STROKE_COLOR, opacity)
                               if stroke_on else text_color)

                block, pad = _render_text_lines_to_image(
                    lines, font_f, fill=text_color, line_height=lh,
                    letter_spacing_px=letter_spacing_px,
                    stroke_width=stroke_width_total, stroke_fill=stroke_fill,
                    underline=layer.get("underline", False), align="left")

                pre_w, pre_h = block.size
                center_x = (tx - pad) + pre_w / 2
                center_y = (ty - pad) + pre_h / 2

                if layer.get("italic", False):
                    block = _apply_italic_shear(block)
                rotation = layer.get("rotation", 0.0)
                if rotation:
                    block = _apply_rotation(block, rotation)

                paste_x = int(center_x - block.width / 2)
                paste_y = int(center_y - block.height / 2)
                canvas.alpha_composite(block, (paste_x, paste_y))
                draw = ImageDraw.Draw(canvas)

                widest = pre_w - 2 * pad
                bboxes[bbox_key] = (tx, ty, tx + max(widest, 10), ty + max(pre_h - 2 * pad, 1))

        elif kind == "desc":
            description = layer["text"]
            if description.strip():
                bsz = max(8, int(W * layer["size"]))
                font_b = font_manager.load("body", bsz)
                box_w = int(W * layer.get("w", 0)) or int(W * 0.90)
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
                auto_box_h = max(text_h + pad, icon_sz + pad) + int(H * 0.010)
                box_h = int(H * layer.get("h", 0)) or auto_box_h

                box_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bd = ImageDraw.Draw(box_layer)
                fill_color = layer.get("fill", BOX_COLOR)
                box_fill = _apply_opacity(fill_color, opacity)
                bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                                     radius=corner_r, fill=box_fill)
                canvas = Image.alpha_composite(canvas, box_layer)
                draw = ImageDraw.Draw(canvas)

                icon_color = _apply_opacity(VERDE, opacity)
                text_color_value = layer.get("text_color", BLANCO + (255,))
                text_color = _apply_opacity(text_color_value, opacity)
                if icon != "ninguno":
                    iy = by + (box_h - icon_sz) // 2
                    icon_img = draw_icon(icon_sz, icon, icon_color)
                    canvas.alpha_composite(icon_img, (bx + pad, iy))
                    draw = ImageDraw.Draw(canvas)

                dy = by + (box_h - text_h) // 2
                text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                for i, l in enumerate(dlines):
                    text_draw.text((text_x, dy + i * dlh), l, font=font_b, fill=text_color)
                canvas = Image.alpha_composite(canvas, text_layer)
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)

        elif kind == "cta":
            cta_text = layer["text"]
            if cta_text.strip():
                bsz = max(8, int(W * layer["size"]))
                font_b = font_manager.load("body", bsz)
                box_w = max(1, int(W * layer.get("w", 0.30)))
                box_h = max(1, int(H * layer.get("h", 0.08)))
                bx = int(layer["x"] * W)
                by = int(layer["y"] * H)
                corner_r = int(W * 0.033)
                pad = int(W * 0.04)

                box_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bd = ImageDraw.Draw(box_layer)
                fill_color = layer.get("fill", BOX_COLOR)
                box_fill = _apply_opacity(fill_color, opacity)
                bd.rounded_rectangle([(bx, by), (bx + box_w, by + box_h)],
                                     radius=corner_r, fill=box_fill)
                canvas = Image.alpha_composite(canvas, box_layer)
                draw = ImageDraw.Draw(canvas)

                text_color_value = layer.get("text_color", BLANCO + (255,))
                text_color = _apply_opacity(text_color_value, opacity)
                max_text_w = max(10, box_w - pad * 2)
                dlines = wrap_text(cta_text, font_b, max_text_w, draw)
                dlh = int(bsz * 1.48)
                text_h = len(dlines) * dlh
                dy = by + (box_h - text_h) // 2

                text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_layer)
                for i, l in enumerate(dlines):
                    lbbox = text_draw.textbbox((0, 0), l, font=font_b)
                    lw = lbbox[2] - lbbox[0]
                    lx = bx + max(pad, (box_w - lw) // 2)
                    text_draw.text((lx, dy + i * dlh), l, font=font_b, fill=text_color)
                canvas = Image.alpha_composite(canvas, text_layer)
                draw = ImageDraw.Draw(canvas)

                bboxes[bbox_key] = (bx, by, bx + box_w, by + box_h)

    return canvas, bboxes
