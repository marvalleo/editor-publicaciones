# Fase 2 — Carruseles: diseño

Fecha: 2026-07-09
Estado: aprobado por el usuario, pendiente de implementación

## Objetivo

Pasar de editar una sola lámina a editar un **carrusel completo de Instagram** (hasta 10
láminas) dentro del mismo proyecto: navegar entre láminas, reordenarlas, duplicarlas, copiar
estilo entre ellas, compartir logo/paleta/CTA/fuente en todo el carrusel, importar el carrusel
completo por lotes a partir de fotos numeradas + un JSON de copys generado externamente
(ChatGPT), y exportar todas las láminas de una vez.

El modelo de datos (`Project.slides: list[Slide]`, `Project.shared: dict`) ya soporta
multi-lámina desde Fase 1 — no requiere migración. El trabajo de Fase 2 es casi enteramente
UI/orquestación en `app.py` y `left_panel.py`, más un módulo nuevo de motor puro para el
importador por lotes.

## Fuera de alcance de esta fase

- Layouts prearmados A–E (Fase 5).
- `CTALayer` real con color/transparencia de caja (Fase 4). El CTA del JSON de import se
  guarda pero no se renderiza todavía.
- Reordenar miniaturas por arrastre (drag & drop) — se decide botones ↑/↓ para esta fase,
  drag queda como posible iteración futura aislada.

## Sección 1 — Estado de lámina activa

- `App` reemplaza las 3 asignaciones hardcodeadas `self.slide = self.project.slides[0]`
  (líneas 98, 787, 1281 de `dcpub/app.py`) por:
  - `self.current_slide_index: int = 0`
  - `switch_to_slide(index: int)`: reasigna `self.slide`, actualiza
    `current_slide_index`, dispara el mismo refresh que ya usa el flujo de carga de
    proyecto (canvas, panel de propiedades, panel de capas).
- El `CommandStack` (undo/redo) es **global al proyecto**, no por lámina. Deshacer un cambio
  hecho en otra lámina la revierte igual, aunque no sea visible hasta navegar a ella. Se elige
  así por simplicidad (YAGNI); navegación automática al deshacer queda para una iteración
  futura si resulta confuso en el uso real.

## Sección 2 — Panel de miniaturas (`left_panel.py`)

Nueva sección "Láminas" arriba del resto del panel izquierdo:

- Lista vertical scrolleable, una miniatura por `Slide`, renderizada con el `Renderer`
  existente a ~120px de ancho, cacheada igual que el preview grande.
- Click en miniatura → `switch_to_slide(index)`. La lámina activa se resalta con borde verde
  de marca.
- Botones bajo la lista: **+ Agregar** (lámina en blanco, layout default vía
  `crear_slide_por_defecto`), **Duplicar**, **Eliminar**, **↑ / ↓** (reordenar).
- Cada acción pasa por el `CommandStack` como comando reversible (mismo patrón que ya existe
  para capas: agregar/eliminar/duplicar/reordenar lámina).

## Sección 3 — Copiar entre láminas y "aplicar a todas"

Dos mecanismos distintos, no confundir:

**Copiar estilo →** (acción puntual, botón junto a la miniatura): clona posición, tamaño,
tipografía y color de cada capa de la lámina activa hacia una lámina destino elegida,
**preservando el texto que ya tenía la lámina destino**. Sirve para aplicar un layout ya
armado a las demás láminas sin pisar sus contenidos.

Si se necesita clonar todo incluido el texto, se usa **Duplicar** (Sección 2), no "Copiar
estilo".

**Aplicar a todas / `Project.shared`** (config persistente, no una acción puntual): un
checkbox "Usar en todo el carrusel" en la sección de Logo (y luego Paleta/CTA/Fuente) del
panel izquierdo escribe/borra la entrada correspondiente en `shared`. El `Renderer` resuelve:
si `shared` tiene valor para esa propiedad, pisa el de la capa individual de cada lámina; si
no, usa el de la capa. Cambiar el valor compartido una vez actualiza las 10 láminas.

## Sección 4 — Importador por lotes

Insumo: una carpeta con las fotos numeradas + un único archivo `.json` con este formato
(acordado con el usuario, para que se lo pida a su generador de GPT):

```json
[
  {
    "imagen": "01.jpg",
    "titulo": "...",
    "subtitulo": "...",
    "beneficios": ["...", "..."],
    "cta": "..."
  }
]
```

Reglas acordadas:

- Emparejamiento imagen↔entrada por el campo `"imagen"` (nombre de archivo exacto), no por
  posición en el array.
- Orden final de las láminas: alfanumérico por nombre de archivo (`01.jpg`, `02.jpg`, ...),
  no el orden del array JSON.
- Import parcial: si una imagen no tiene entrada o una entrada no tiene imagen, esa lámina se
  omite y se informa al final qué quedó afuera. No se aborta el import completo.
- `beneficios` (lista) se une en un solo texto con viñetas (`"• x\n• y"`) para el campo
  `BoxLayer.text` existente — no requiere cambios al modelo.
- `cta` se guarda en los datos parseados pero **no se renderiza** (no hay `CTALayer` todavía,
  Fase 4). No se pierde el dato, simplemente no tiene capa visual aún.
- El formato del lienzo (4:5, 3:4, 9:16, personalizado) se elige una vez en el diálogo de
  import, se aplica a todas las láminas generadas.
- El usuario puede elegir crear un proyecto nuevo con las láminas importadas, o agregarlas al
  proyecto actualmente abierto.

Arquitectura:

- `dcpub/batch_import.py` (motor puro, sin Tkinter, testeable headless):
  ```python
  def importar_carrusel_por_lotes(carpeta: Path, formato: dict) -> tuple[Project, list[str]]
  ```
  Busca el único `.json` de la carpeta, empareja por nombre, ordena alfanuméricamente, arma
  una `Slide` por match vía `crear_slide_por_defecto(...)`, devuelve `(project, advertencias)`.
- `app.py`: ítem de menú **"Archivo → Importar carrusel por lotes..."** → diálogo de carpeta +
  selector de formato → llama al motor → si hay advertencias, `messagebox` con el detalle →
  si ya hay un proyecto con contenido abierto, pregunta crear nuevo vs. agregar a las láminas
  existentes.

## Sección 5 — Exportación por lotes

- `Exporter` gana `exportar_todas(project, carpeta_destino)`, itera `project.slides` y
  exporta cada una a resolución real.
- Nombrado: `{nombre_proyecto}_{01..10}_{fecha}.png` (índice de lámina con cero a la
  izquierda, para que el orden de archivos en la carpeta coincida con el orden del carrusel).
- Menú: **"Archivo → Exportar carrusel completo..."**, adicional al export individual
  existente (no lo reemplaza).

## Testing

- `dcpub/batch_import.py`: tests headless con carpetas de fixture (fotos sintéticas + JSON de
  prueba) cubriendo: match exitoso completo, imagen sin entrada, entrada sin imagen, orden
  alfanumérico correcto, formato aplicado a todas las láminas resultantes.
- `Exporter.exportar_todas`: test headless verificando que se generan N archivos con el
  nombrado esperado para un proyecto de N láminas.
- Comandos nuevos de `CommandStack` (agregar/eliminar/duplicar/reordenar lámina, copiar
  estilo): tests de undo/redo siguiendo el patrón de `tests/test_commands.py`.
- Verificación headless de cierre de fase, mismo patrón que Fase 1: instanciar proyecto
  multi-lámina, renderizar preview y full-res de cada una, guardar/cargar, exportar todas.

## Reparto de trabajo (paralelo con Codex)

Motor puro, sin tocar `app.py`/`left_panel.py`/`canvas_editor.py`/`property_panel.py` →
candidato a Codex en paralelo:

- `dcpub/batch_import.py` completo (Sección 4).
- `Exporter.exportar_todas` (Sección 5).

UI/orquestación (`app.py`, `left_panel.py`, comandos de `CommandStack`) → sesión principal,
por el acoplamiento fuerte a `self.slide` y al ciclo de refresh existente.
