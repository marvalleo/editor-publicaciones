# Diseño — Fase 4 (sub-fase 2): Texto rico por elemento

Fecha: 2026-07-09
Roadmap: `AGENTS.md`/`CLAUDE.md` sección 6, Fase 4 — "Texto rico + capas nuevas"
(segunda sub-entrega de Fase 4, después de CTA + caja de descripción configurable;
líneas decorativas y puntos de carrusel quedan para sub-fases posteriores)

## Contexto

El plan maestro pide, para título y subtítulo: fuente por elemento (dropdown),
bold/italic/underline, interlineado, tracking, stroke, y rotación. La
exploración de código previa (`docs/superpowers/specs/2026-07-09-fase4-hallazgos.md`)
confirmó que:

- `TextLayer` (models.py) solo tiene `text`/`role`/`size` — nada de lo anterior existe.
- `rotation` existe en `Layer` base pero **nunca se aplica** en el render (campo fantasma).
- `render.py` dibuja título y subtítulo con `draw.text()` directo sobre el
  canvas, con color y sombra hardcodeados (título: blanco + sombra; subtítulo:
  verde de marca + sombra + líneas decorativas a los costados).
- `FontManager.load(role, size)` solo soporta 3 roles fijos, sin variantes
  bold/italic reales (`_ROLE_MAP` mapea cada rol a un único archivo `.ttf` de
  peso fijo).

## Alcance

**Incluye**, solo para capas `title`/`subtitle` (los dos `TextLayer` existentes):
- Selector de fuente entre las 3 fuentes de marca ya descargadas (Playfair
  Display, Dancing Script, Lato), independiente del rol.
- Bold/italic sintetizados (sin descargar variantes de fuente nuevas):
  bold vía `stroke_width`/`stroke_fill` del mismo color que el relleno;
  italic vía shear (inclinación) de la imagen renderizada.
- Underline: línea dibujada bajo cada línea de texto.
- Interlineado (`line_spacing`) y tracking (`letter_spacing`) configurables.
- Stroke (contorno) on/off + grosor, color fijo (no configurable).
- Rotación aplicada de verdad (el campo ya existe, hoy ignorado por el render).
- Control desde la UI: dropdown, checkboxes y sliders en el panel de
  propiedades; rotación con slider numérico (sin handle de arrastre en canvas).

**No incluye (fuera de alcance, otras sub-fases):**
- Color de texto ni sombra configurables — quedan fijos como están hoy
  (decisión explícita: no estaban en el pedido original de esta pieza).
- Color de stroke configurable — queda fijo, mismo tono oscuro que ya usa la
  sombra existente.
- Aplicar estos controles a `BoxLayer` (descripción) o `CTALayer` — decisión
  explícita de mantener el alcance en título/subtítulo únicamente.
- `LineLayer`/`DotsLayer` — sub-fases separadas.
- Descarga de variantes de fuente reales (Bold/Italic/BoldItalic por familia).
- Handle de arrastre para rotar visualmente en el canvas — solo slider numérico.
- Hit-testing/selección que siga la rotación visual — el bbox de selección
  sigue siendo el rectángulo sin rotar (aproximación ya usada en el proyecto
  para otras simplificaciones).

## Modelo de datos (`dcpub/models.py`)

```python
@dataclass
class TextLayer(Layer):
    type: str = "text"
    text: str = ""
    role: str = "free"
    size: float = 0.05
    font_family: str = ""       # "" = fuente de marca según rol (legado);
                                 # "playfair" | "dancing" | "lato"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    line_spacing: float = 0.0   # 0 = usa el valor legado por rol (1.22 en título)
    letter_spacing: float = 0.0 # tracking, fracción del tamaño de fuente
    stroke_on: bool = False
    stroke_width: float = 0.0   # fracción del tamaño de fuente
```

Todos los defaults preservan el render actual exacto — mismo patrón de
fallback-a-legado que `BoxLayer.w`/`h` de la sub-fase anterior. `rotation`
ya existe en `Layer` (heredado), esta sub-fase lo empieza a *aplicar*.

`LAYER_STYLE_FIELDS[("text", "title")]` y `[("text", "subtitle")]` suman los
8 campos nuevos a su tupla existente.

## Motor de render (`dcpub/render.py`)

**Cambio estructural:** se reemplaza la lógica separada de `"title"`/`"sub"`
por una función compartida `_draw_text_block(canvas, layer_data, font, ...)`
que ambas ramas invocan, para no duplicar la síntesis de bold/italic/tracking/
underline/rotación en dos lugares.

Pipeline de `_draw_text_block`:

1. **Fuente**: `font_manager.load(role, size, family=layer.get("font_family", ""))`.
2. **Tracking**: si `letter_spacing != 0`, cada línea se dibuja carácter por
   carácter (en vez de `draw.text` de la línea completa), avanzando
   `ancho_char + letter_spacing_px` entre cada uno. Si `letter_spacing == 0`,
   se usa el camino rápido actual (`draw.text` de la línea entera) — sin
   cambio de comportamiento ni de performance para el caso por defecto.
3. **Bold + stroke real**: un solo `stroke_width` total combinado
   (`stroke_width_total = ancho_borde_si_stroke_on + ancho_extra_si_bold`),
   con `stroke_fill` = color de borde si `stroke_on` está activo, o el mismo
   color de relleno del texto si solo `bold` está activo (sin borde real).
   Cuando ambos están activos a la vez, el borde real "gana" el color del
   grosor combinado — simplificación aceptada, no dos contornos de color
   distinto superpuestos.
4. **Underline**: después de dibujar cada línea, una línea horizontal bajo
   el baseline, de ancho igual al texto de esa línea.
5. Todo el bloque (todas las líneas) se compone en una imagen RGBA chica,
   ajustada al contenido (no del tamaño completo del lienzo).
6. **Italic**: si está activo, se aplica un shear a esa imagen con
   `Image.transform` (`Image.AFFINE`, matriz de corte horizontal).
7. **Rotación**: si `layer.get("rotation", 0) != 0`, se rota esa imagen con
   `.rotate(angle, expand=True, resample=Image.BICUBIC)`.
8. Se pega el resultado en el canvas en la posición final, recalculando el
   offset de pegado para que el punto de anclaje original (esquina o centro,
   según el rol) se mantenga tras el `expand=True` del rotate.
9. El bbox reportado para hit-testing/selección es el rectángulo **sin
   rotar** del layout original (paso 5), no el de la imagen rotada — mismo
   criterio ya usado en otras simplificaciones del proyecto.

El interlineado (`line_spacing`) solo es relevante para título, que ya es
multilínea (envuelve texto con `wrap_text`); si viene en `0`, se usa el
`1.22` legado. El subtítulo hoy es de una sola línea — el campo queda
disponible en el modelo por si en el futuro se habilita wrap, pero esta
sub-fase no cambia ese comportamiento (subtítulo sigue sin wrap).

## `FontManager` (`dcpub/fonts.py`)

```python
_FAMILY_MAP = {
    "playfair": "PlayfairDisplay-Bold.ttf",
    "dancing":  "DancingScript-Regular.ttf",
    "lato":     "Lato-Regular.ttf",
}

def load(self, role, size, family=""):
    """Si family viene vacío, usa la fuente de marca del rol (legado,
    _ROLE_MAP). Si viene seteado, usa _FAMILY_MAP y cae al mismo
    fallback de sistema por rol si el archivo de marca no está disponible."""
```

Bold/italic **no** se resuelven acá — `FontManager` sigue devolviendo el
mismo `ImageFont` sin variantes reales; la síntesis ocurre en el paso de
dibujo (`_draw_text_block`), no en la carga de fuente. No se descargan
archivos nuevos.

## UI (panel de propiedades)

Para `kind in ("title", "sub")`, después de los controles existentes
(x/y/size/opacidad/centrar), se suma una sección:

- Dropdown de fuente: "Playfair Display" / "Dancing Script" / "Lato"
  (mapea a `font_family`).
- Checkboxes: Negrita, Cursiva, Subrayado (`bold`/`italic`/`underline`).
- Slider de interlineado (`line_spacing`).
- Slider de tracking (`letter_spacing`).
- Checkbox "Contorno" (`stroke_on`) + slider de grosor (`stroke_width`,
  deshabilitado si `stroke_on` es falso).
- Slider de rotación, `-45` a `45` grados (`rotation`, campo ya existente).

Todos los controles nuevos son atributos planos (no dicts anidados), así
que usan `PropertyChangeCommand` para undo — mismo patrón que `fill`/
`text_color` de la sub-fase anterior, no `DictItemChangeCommand`.

## Adaptadores UI↔render

`App._build_layers_for()` y `Exporter._layers_from_slide()` suman los 8
campos nuevos + `rotation` a los dicts que arman para `title`/`sub` (hoy
`rotation` no se pasa en ningún lado — hallazgo ya confirmado por Codex).

## Testing

- Modelo: round-trip de serialización de los campos nuevos.
- Render: cada control probado en aislamiento (bold cambia píxeles,
  italic cambia geometría del bbox, underline agrega píxeles bajo el
  texto, tracking cambia el ancho total, rotación cambia el bbox reportado
  de forma predecible, stroke cambia píxeles en los bordes de las letras).
- Render: con todos los campos en su default, el resultado es
  pixel-idéntico al render actual (test de no-regresión, mismo criterio
  que el fallback legado de `BoxLayer`).
- `FontManager.load` con `family=""` devuelve la misma fuente que antes
  (comportamiento legado); con `family` seteado, devuelve la fuente
  correcta de `_FAMILY_MAP`.
- Verificación headless de cierre con una lámina que use varias
  combinaciones (título rotado + bold, subtítulo con tracking + fuente
  distinta), comparada contra un render neutro.

## Riesgos / decisiones registradas

- Bold+stroke simultáneos comparten un solo `stroke_width` combinado con
  el color del borde ganando — no es visualmente "perfecto" (un purista
  esperaría el bold en el color del texto y el borde encima, en dos
  colores), pero evita una segunda pasada de dibujo y mantiene el pipeline
  de una sola llamada a `draw.text`. Revisar si en el uso real esto
  molesta antes de invertir en una implementación de dos pasadas.
- El bbox de selección no sigue la rotación visual — un texto rotado 30°
  seguirá mostrando handles de selección en su rectángulo original sin
  rotar. Aceptado explícitamente para no abrir el trabajo de hit-testing
  rotado en esta sub-fase.
- El interlineado configurable no tiene efecto visible en el subtítulo
  hoy (no es multilínea) — el campo existe en el modelo por consistencia
  y para no tener que migrar de nuevo si el subtítulo gana wrap en el
  futuro.
