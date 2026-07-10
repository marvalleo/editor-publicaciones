# Fase 5 — Layouts A-E aplicables (diseño)

## Objetivo

Permitir que el usuario elija, para la lámina activa, uno de 5 layouts
predefinidos (A-E) que reposicionan/redimensionan las capas de texto y el
logo ya existentes en esa lámina, sin tocar su contenido (texto, fuente,
color) ni la foto de fondo. Es la primera pieza de Fase 5 del roadmap
(`presets de marca`); paleta y librería de copys quedan para sub-fases
posteriores.

## Alcance (decidido con el usuario)

- Un layout **solo reposiciona** capas que ya existen en la lámina
  (logo, título, subtítulo, caja de descripción). No agrega ni quita capas.
- Se aplica **solo a la lámina activa** (no hay "aplicar a todas" en esta
  sub-fase — ya existe un mecanismo separado de "copiar estilo" para eso).
- No se introduce control de alineación de texto (`align`) ni ningún campo
  nuevo en el modelo: los layouts trabajan únicamente con campos que ya
  existen y que la app ya sabe editar (`x`, `y`, `size`, `w` en la caja).
- La foto de fondo no forma parte de ningún layout: siempre es
  `x=0, y=0, w=1, h=1` (cover full-bleed), independiente del layout elegido.

## Por qué estos límites

- `TextLayer` no tiene campo `align` en el modelo actual (el render de
  título/subtítulo/texto libre siempre dibuja `align="left"` — confirmado
  en `render.py`). Agregarlo implicaría tocar el pipeline de render y las
  3 ramas título/subtítulo/texto-libre; fuera de alcance de "reposicionar".
  Un layout "centrado" se logra corriendo `x` hacia la derecha, no con
  alineación real.
- `w`/`h` en título/subtítulo **no afectan el ancho de wrap** del texto: el
  render calcula el ancho disponible como `W - x - margen` (ver
  `render.py` rama `title`, línea ~464). Por eso los layouts solo tocan
  `x`, `y`, `size` en capas de texto, y `x`, `y`, `w` en la caja de
  descripción (`h` se deja en `0.0` = auto-altura, como ya funciona hoy).

## Arquitectura

### Módulo nuevo: `dcpub/presets/layouts.py`

```python
LAYOUTS = {
    "A": {"nombre": "Actual", ...},
    "B": {"nombre": "Centrado", ...},
    "C": {"nombre": "Superior", ...},
    "D": {"nombre": "Minimalista", ...},
    "E": {"nombre": "Banda ancha", ...},
}
```

Cada entrada tiene `nombre` (para mostrar en la UI) y `campos`, un dict
keyed por `(tipo, rol)` — el mismo par que ya usa `_estilo_key` en
`models.py` para "copiar estilo" — con los valores a aplicar:

```python
"A": {
    "nombre": "Actual",
    "campos": {
        ("logo", None):       {"x": 0.40, "y": 0.022, "w": 0.20, "h": 0.20},
        ("text", "title"):    {"x": 0.055, "y": 0.42, "size": 0.087},
        ("text", "subtitle"): {"x": 0.50, "y": 0.55, "size": 0.050},
        ("box", None):        {"x": 0.05, "y": 0.808, "w": 0.90},
    },
},
```

Valores concretos de arranque para los 5 layouts (ver sección
"Layouts propuestos" más abajo); son puntos de partida razonables, no
mediciones exactas — se ajustan con la verificación visual del plan.

### Función nueva: `plan_aplicar_layout` en `dcpub/models.py`

Análoga a la ya existente `plan_copia_estilo` (mismo archivo, mismo
patrón), para reusar exactamente el mecanismo probado en vez de inventar
uno nuevo:

```python
def plan_aplicar_layout(slide: Slide, layout_id: str) -> list:
    """Compara las capas de `slide` con los campos definidos en
    LAYOUTS[layout_id] por tipo/rol y devuelve la lista de cambios a
    aplicar: tuplas (capa, atributo, valor_nuevo). Preserva el contenido
    de cada capa (texto/src) — solo cambia los campos listados en el
    layout. Capas de `slide` sin equivalente por tipo/rol en el layout no
    generan cambios. `layout_id` inexistente devuelve lista vacía."""
```

Firma y contrato calcados de `plan_copia_estilo`: misma forma de tupla de
salida, mismo criterio de matcheo por `(tipo, rol)`, mismo comportamiento
ante capas sin match (se ignoran, no es error).

### UI: `dcpub/app.py`

- Nuevo método `_apply_layout(layout_id)`, calcado de
  `_copy_style_to_slide` (línea ~1291): arma `plan_aplicar_layout`,
  construye una `CompositeCommand` de `PropertyChangeCommand` (undo/redo
  gratis, mismo patrón que ya existe), y además fija
  `slide.layout_tag = layout_id` (campo que ya existe en el modelo,
  documentado como "informativo", hoy sin uso — esta es su primera
  conexión real).
- Selector en el panel izquierdo (`left_panel.py` o el bloque donde vive
  el selector de formato en `app.py`): 5 botones rotulados "A".."E" con
  tooltip/label mostrando `LAYOUTS[id]["nombre"]`. Al hacer click, llama
  `self._apply_layout(id)` y re-renderiza.
- Si la lámina no tiene ninguna capa que matchee ninguna clave del layout
  (caso degenerado, no debería pasar con `crear_slide_por_defecto`), el
  botón simplemente no cambia nada — mismo comportamiento no-op que ya
  tiene "copiar estilo" cuando `cambios` está vacío.

## Layouts propuestos

Todos parten de la lámina por defecto (foto + logo + título + subtítulo +
caja). El logo se mantiene arriba-centro en todos los layouts salvo
Minimalista (D), por consistencia de marca.

**A — Actual** (los valores de `crear_slide_por_defecto` hoy): título en
franja media (y=0.42), subtítulo debajo (y=0.55), caja pegada abajo
(y=0.808). Sirve para volver al layout de fábrica tras probar otro.

**B — Centrado**: título y subtítulo corridos hacia el centro horizontal
(x=0.12) y agrupados verticalmente a media altura (y=0.44 / 0.535), caja
más angosta (w=0.76) también corrida a x=0.12. Efecto "bloque centrado".

**C — Superior**: título y subtítulo suben debajo del logo (y=0.26 /
0.335), caja de descripción baja y ocupa la franja inferior más amplia
(y=0.60, w=0.90 — con más alto disponible antes del borde).

**D — Minimalista**: logo más chico (w/h=0.16), título/subtítulo/caja
compactados en la esquina inferior-izquierda con tamaños reducidos
(`size` de título 0.055 en vez de 0.087, subtítulo 0.032), caja angosta
(w=0.55) pegada justo debajo. Deja la mayor parte del encuadre libre para
la foto.

**E — Banda ancha**: caja de descripción sube (y=0.58, w=0.90) y
título/subtítulo bajan a una franja ancha pegada abajo (y=0.74 / 0.815),
estilo "tarjeta apilada": caja arriba, texto grande abajo.

(Valores `x`/`y`/`w`/`size` exactos por capa quedan en la tabla del
código, `dcpub/presets/layouts.py` — este documento describe la intención
de cada uno, el archivo de plan de implementación tendrá los números
verbatim para copiar.)

## Testing

- `tests/test_models_layout.py` (nuevo): `plan_aplicar_layout` para cada
  uno de los 5 layouts sobre una lámina por defecto — verifica que
  título/subtítulo/logo/caja terminan con los `x`/`y`/`size`/`w` del
  layout, que el `text`/`src` de cada capa no cambia, y que un
  `layout_id` inexistente devuelve `[]`. Caso de capa faltante (lámina sin
  subtítulo): esa clave del layout se ignora sin error.
- `tests/test_app_slides.py`: `_apply_layout` empuja una `CompositeCommand`
  al `CommandStack` (undo revierte posiciones), fija `slide.layout_tag`, y
  re-renderiza solo si la lámina afectada es la activa.
- Verificación headless: renderizar la lámina por defecto con cada uno de
  los 5 layouts aplicados y guardar las 5 imágenes de control, para
  revisión visual manual (no hay assert de píxeles exactos: son posiciones
  de diseño, no un valor fijo a proteger con test).

## Fuera de alcance (explícitamente, para no repetir la duda en la
implementación)

- Alineación de texto (`align`) — requeriría tocar `render.py`.
- "Aplicar a todas las láminas" — ya existe "copiar estilo" para eso.
- Agregar/quitar capas por layout (p. ej. que Minimalista quite la caja en
  vez de achicarla) — decidido explícitamente que no en esta sub-fase.
- Paleta de colores y librería de copys — próximas sub-fases de Fase 5,
  specs separadas.
