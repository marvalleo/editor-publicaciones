# Fase 4 — Hallazgos de exploración: líneas decorativas + puntos de carrusel

## 1. Confirmación de ausencia de LineLayer/DotsLayer

- Búsqueda ejecutada: `Select-String -Path 'dcpub\\*.py' -Pattern 'LineLayer|DotsLayer' -CaseSensitive`. Resultado actual: sin coincidencias en `dcpub/`.
- `dcpub/models.py:110-116` define `LAYER_CLASSES` únicamente con claves `"photo"`, `"logo"`, `"text"`, `"box"` y `"cta"`; no incluye `"line"` ni `"dots"`.
- `dcpub/models.py:121-122` reconstruye capas con `cls = LAYER_CLASSES[data["type"]]` y `return cls(**data)`, por lo que un tipo no registrado en ese diccionario no tendría clase de modelo disponible hoy.

## 2. Líneas decorativas existentes (subtítulo)

- La lógica actual está dentro de la rama del render `elif kind == "sub":` en `dcpub/render.py:401`.
- El subtítulo se lee desde `layer["text"]` en `dcpub/render.py:402`; si no está vacío, el tamaño de fuente se calcula como `max(8, int(W * layer["size"]))` en `dcpub/render.py:404`.
- La posición base del subtítulo usa `cx = int(layer["x"] * W)` y `sy = int(layer["y"] * H)` en `dcpub/render.py:406-407`; luego calcula ancho/alto del texto en `dcpub/render.py:408-410` y la línea horizontal queda centrada verticalmente con `ly = sy + sh // 2` en `dcpub/render.py:411`.
- El grosor decorativo actual es `lw_deco = max(2, int(W * 0.003))` en `dcpub/render.py:412`, o sea depende del ancho del lienzo `W` con mínimo de 2 px.
- El largo de cada línea es `line_len = int(W * 0.11)` en `dcpub/render.py:413`, una fracción fija del ancho del lienzo `W`.
- El espacio entre texto y línea es `gap = int(W * 0.03)` en `dcpub/render.py:414`, también fracción fija del ancho del lienzo `W`.
- Los extremos se recortan al lienzo con `lx1 = max(0, sx - gap - line_len)` y `rx2 = min(W, sx + sw + gap + line_len)` en `dcpub/render.py:415-416`.
- El color sale de `line_color = _apply_opacity(VERDE, opacity)` en `dcpub/render.py:417`; `VERDE` está definido como `(141, 194, 111)` / `#8DC26F` en `dcpub/constants.py:5`.
- Las líneas se dibujan en una capa RGBA temporal: `deco_layer = Image.new(...)` y `deco_draw = ImageDraw.Draw(deco_layer)` en `dcpub/render.py:418-419`; luego se trazan dos líneas en `dcpub/render.py:420-421` y se componen sobre el canvas en `dcpub/render.py:422`.
- La caja de selección del subtítulo incluye las líneas decorativas: `bboxes[bbox_key] = (lx1, min(ly - lw_deco, sy), rx2, sy + sh + 6)` en `dcpub/render.py:436`.
- No hay función separada para reutilizar esta decoración como capa independiente: el bloque vive dentro de `elif kind == "sub"` (`dcpub/render.py:401`) y usa variables locales del subtítulo (`subtitle`, `font_s`, `sx`, `sw`, `sy`, `sh`, `ly`) entre `dcpub/render.py:402-436`.

## 3. LineLayer segun el plan maestro vs. lo que ya existe

- El plan maestro define `LineLayer` como: `LineLayer:   length(frac), thickness(px|frac), color, gap(frac)` en `AGENTS.md:95` y la misma entrada aparece en `CLAUDE.md:95`.
- `length`: existe hoy como valor calculado/fijo `line_len = int(W * 0.11)` en `dcpub/render.py:413`; no es configurable ni está en el modelo.
- `thickness`: existe hoy como valor calculado/fijo `lw_deco = max(2, int(W * 0.003))` en `dcpub/render.py:412`; no es configurable ni está en el modelo.
- `color`: existe hoy como `line_color = _apply_opacity(VERDE, opacity)` en `dcpub/render.py:417`, con `VERDE` definido en `dcpub/constants.py:5`; no es configurable por una capa de línea.
- `gap`: existe hoy como valor calculado/fijo `gap = int(W * 0.03)` en `dcpub/render.py:414`; no es configurable ni está en el modelo.
- Lo que no existe: una clase `LineLayer`, un tipo `"line"` en `LAYER_CLASSES` (`dcpub/models.py:110-116`), ni una rama independiente de render para líneas; la implementación actual está acoplada al subtítulo en `dcpub/render.py:401-436`.

## 4. DotsLayer segun el plan maestro vs. API de láminas disponible

- El plan maestro define `DotsLayer` como: `DotsLayer:   count, active, color, spacing` en `AGENTS.md:97` y la misma entrada aparece en `CLAUDE.md:97`.
- No hay `DotsLayer` ni tipo `"dots"` registrado en `LAYER_CLASSES`; el diccionario actual lista `"photo"`, `"logo"`, `"text"`, `"box"` y `"cta"` en `dcpub/models.py:110-116`.
- El modelo sí tiene una colección de láminas: `Project.slides` está declarado en `dcpub/models.py:161`, se serializa en `dcpub/models.py:170` y se reconstruye en `dcpub/models.py:181`.
- Cada `Slide` tiene `format`, `layout_tag`, `layers` y `extra` en `dcpub/models.py:126-130`.
- La app mantiene la lámina activa con `self.slide = self.project.slides[0]` y `self.current_slide_index = 0` en `dcpub/app.py:138-139`.
- El cambio de lámina valida el índice contra `len(self.project.slides)` en `dcpub/app.py:1076`, actualiza `self.current_slide_index = index` y `self.slide = self.project.slides[index]` en `dcpub/app.py:1078-1079`.
- Las operaciones de carrusel ya usan el índice activo: agregar y duplicar insertan después de `self.current_slide_index + 1` en `dcpub/app.py:1092` y `dcpub/app.py:1102`; eliminar usa `len(self.project.slides)` en `dcpub/app.py:1108` y calcula `nuevo_index` con `self.current_slide_index` en `dcpub/app.py:1113`; mover usa `idx = self.current_slide_index` en `dcpub/app.py:1120` y valida contra `len(self.project.slides)` en `dcpub/app.py:1122`.
- `SlidesPanel` declara que depende de `app.project` y `app.current_slide_index` en `dcpub/slides_panel.py:16-18`; reconstruye miniaturas iterando `for index, slide in enumerate(self.app.project.slides)` en `dcpub/slides_panel.py:79`, detecta la activa con `is_active = index == self.app.current_slide_index` en `dcpub/slides_panel.py:83`, y muestra `Lámina {index + 1}` en `dcpub/slides_panel.py:98`.
- Para una futura capa de puntos, los datos existentes que podrían informar `count` y `active` son `len(project.slides)` / iteración de `project.slides` y `current_slide_index`; no hay campo de modelo específico para `count`, `active`, `color` o `spacing` de puntos.

## 5. Patrón de capas puramente decorativas

- El panel de propiedades obtiene un `kind` con `_kind_of(layer)` en `dcpub/app.py:574`; si `kind` es `None`, retorna sin armar controles en `dcpub/app.py:575-576`.
- `_kind_of` solo reconoce `photo`, `logo`, `text` con roles `title`/`subtitle`, `box` y `cta` en `dcpub/app.py:878-889`; cualquier otro tipo retorna `None` en `dcpub/app.py:890`.
- Para capas no foto, `_build_property_panel` busca rango de tamaño con `smin, smax = SIZE_RANGE[kind]` en `dcpub/app.py:611`. `SIZE_RANGE` solo contiene `logo`, `title`, `sub`, `desc` y `cta` en `dcpub/app.py:25-31`.
- La etiqueta del slider se arma como `"Tamaño del logo" if kind == "logo" else "Tamaño de fuente"` en `dcpub/app.py:612`, y el slider siempre se crea sobre la propiedad `"size"` en `dcpub/app.py:637`.
- Pregunta abierta: ¿una capa puramente geométrica debería usar el mismo concepto `size`, mapearlo a `length`/`thickness`, o tener controles propios para evitar que el panel muestre “Tamaño de fuente” en una capa sin texto?

## Preguntas abiertas para el brainstorming

- ¿Las líneas decorativas deben seguir siendo un detalle interno del subtítulo, o convertirse en una `LineLayer` independiente reutilizable?
- Si existe `LineLayer`, ¿`gap` representa separación respecto a otro elemento/texto, separación interna entre segmentos, o margen visual propio de la capa?
- ¿`LineLayer.thickness` debe expresarse como fracción del ancho del lienzo, píxeles absolutos de exportación, o aceptar ambos como sugiere el plan maestro?
- ¿`DotsLayer.count` y `DotsLayer.active` deberían ser valores manuales editables, o derivarse siempre de `len(project.slides)` y `current_slide_index`?
- ¿`DotsLayer` vive como capa por lámina, como elemento compartido del carrusel, o como overlay generado por la app/exportador?
- ¿El panel de propiedades debe agregar un camino explícito para capas geométricas sin `size` de fuente?
