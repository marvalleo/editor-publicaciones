# Plan Maestro — Editor Visual de Publicaciones · Cabañas Don Cristóbal

> Documento guía para desarrollar con **Codex**.
> Colócalo en la raíz del proyecto y renómbralo a `AGENTS.md` si quieres que Codex lo tome como contexto permanente.
> Se desarrolla **por fases**. No pases a la siguiente fase hasta que la actual cumpla sus **criterios de aceptación** y pase su verificación headless.

---

## 1. Objetivo

Convertir `generar_publicacion.py` (hoy un generador de una sola imagen) en un **editor visual de publicaciones e carruseles de Instagram**: vista previa grande, elementos como capas seleccionables/arrastrables/redimensionables, propiedades editables por capa, edición de la foto base, formatos múltiples, presets de marca, guardado de proyecto y exportación en alta resolución.

**Enfoque:** *evolucionar* el script actual, reutilizando su motor de render (`compose()`) y su gestor de fuentes, que ya están probados y producen el estilo de marca correcto. No se tira nada de v2.0; se refactoriza dentro de una arquitectura que pueda crecer.

---

## 2. Restricciones técnicas

- **Python 3**, **tkinter** (UI) y **Pillow** (render). Solo módulos estándar aparte de Pillow.
- Instalar Pillow automáticamente si falta. Nunca romper si una fuente no se puede descargar (usar fallback del sistema).
- **Lanzador único:** `python generar_publicacion.py` sigue siendo el punto de entrada.
- **Estructura modular** (paquete `dcpub/`), no un solo archivo gigante. El lanzador es delgado e importa el paquete.
- La **vista previa** trabaja con una imagen escalada; la **exportación** se renderiza a resolución real. Todas las posiciones/tamaños de capa se guardan como **fracciones (0.0–1.0)** del lienzo para que preview y export escalen sin distorsión (así ya funciona v2.0).
- La foto base **nunca se deforma**: se ajusta por *cover/contain* + zoom + offset, manteniendo proporción.

---

## 3. Arquitectura objetivo

```
generar_publicacion.py         # lanzador delgado: instala deps, crea App, mainloop
dcpub/
  __init__.py
  constants.py                 # colores de marca, formatos, defaults, rutas
  fonts.py                     # FontManager  (PORTAR de v2.0: descarga + fallback + listar fuentes del sistema)
  models.py                    # Project, Slide, Layer y subclases (dataclasses) + (de)serialización
  render.py                    # Renderer   (PORTAR/adaptar compose() de v2.0) -> (PIL.Image, {layer_id: bbox})
  canvas_editor.py             # CanvasEditor: tk.Canvas, dibuja preview, selección, handles, drag/resize, teclado, snap
  property_panel.py            # PropertyPanel: propiedades de la capa seleccionada (derecha)
  left_panel.py                # Proyecto, foto, logo, textos, lista de capas, (luego) láminas y presets
  commands.py                  # CommandStack: undo/redo (patrón Command)
  project_io.py                # ProjectManager: guardar/abrir JSON, rutas relativas, "cambios sin guardar"
  exporter.py                  # Exporter: render full-res, PNG/JPG, nombrado, carpeta destino
  presets/
    __init__.py
    palette.py                 # paletas de marca (principal + alternativa)
    layouts.py                 # (Fase 5) Layout A–E
    copys.py                   # (Fase 5) títulos/frases/beneficios/CTA sugeridos
app.py  ->  dcpub/app.py       # App(tk.Tk): arma menú/toolbar + 3 paneles, orquesta todo
```

**Clases principales**

- `App(tk.Tk)` — ventana, menú/toolbar, layout de 3 paneles, mantiene el `Project` activo y el `CommandStack`.
- `FontManager` — descarga Playfair/Dancing Script/Lato, fallback a fuentes del sistema, y expone la lista de fuentes instaladas para los dropdowns.
- `Renderer` — dado un `Slide` + escala, devuelve la imagen PIL y un diccionario `{layer_id: (x0,y0,x1,y1)}` en píxeles para hit-testing y handles.
- `CanvasEditor` — todo lo interactivo del canvas central.
- `PropertyPanel` — panel derecho, se reconstruye según el **tipo** de capa seleccionada.
- `CommandStack` — pila de comandos reversibles para undo/redo.
- `ProjectManager` / `Exporter` — persistencia y salida.

---

## 4. Modelo de datos

Posiciones y tamaños **en fracciones del lienzo**. Colores como `"#RRGGBB"` o `[r,g,b,a]`. Todo serializable a JSON.

### Layer (base)
```
id: str                # uuid corto
name: str              # editable ("Título", "Logo", ...)
type: str              # "photo" | "logo" | "text" | "box" | "line" | "cta" | "dots"
visible: bool = True
locked: bool  = False
z: int                 # orden de dibujo (mayor = encima)
x: float               # esquina sup-izq, fracción del ancho
y: float               # fracción del alto
w: float               # ancho, fracción (según tipo puede derivarse del contenido)
h: float               # alto, fracción
rotation: float = 0.0  # grados
opacity: float = 1.0   # 0..1
```

### Subtipos (props adicionales)
```
PhotoLayer:  src, fit("cover"), zoom=1.0, offset_x=0, offset_y=0,
             adjust{brightness,contrast,saturation,warmth,sharpness,shadows,vignette},
             overlay{bottom_grad:bool, top_grad:bool, strength}
LogoLayer:   src, keep_ratio=True
TextLayer:   text, role("title"|"subtitle"|"body"|"cta"|"free"),
             font_family, size(frac), color, bold, italic, underline,
             align("left"|"center"|"right"), line_spacing, letter_spacing,
             max_width(frac), shadow{on,dx,dy,color}, stroke{on,width,color}
BoxLayer:    fill(rgba), radius(frac), border{on,width,color}, padding(frac)
LineLayer:   length(frac), thickness(px|frac), color, gap(frac)
CTALayer:    (Box + Text combinados) fill, radius, text, font_family, size, color
DotsLayer:   count, active, color, spacing
```

### Slide
```
format: {name, w, h}    # p.ej. {"name":"feed_4x5","w":1080,"h":1350}
layout_tag: str|None    # "A".."E" (informativo)
layers: [Layer, ...]    # incluye la PhotoLayer de fondo
```

### Project
```
version: int
name: str
default_format: {...}
palette: {...}          # ver presets/palette.py
shared: {logo, palette, cta, base_font, box_style, gradient}  # políticas "aplicar a todas" (Fase 2)
slides: [Slide, ...]    # en Fase 1 hay 1 sola
```

**Guardado:** un `.json` (formato propio, legible). Rutas de imágenes **relativas** al archivo de proyecto cuando sea posible; si no, absolutas.

---

## 5. Estrategia de evolución desde v2.0

1. Crear el paquete `dcpub/` y mover el **motor de render** (`compose`, `_get_background`, `wrap_text`, `draw_icon`) a `render.py`, adaptándolo para recibir un `Slide`/lista de capas en vez de parámetros sueltos.
2. Mover `load_font` / `download_fonts` / búsqueda de fuentes a `fonts.py` como `FontManager`.
3. Envolver las 4 "piezas" actuales (logo, título, subtítulo, caja) como **capas** del nuevo modelo, con los mismos defaults de v2.0. Resultado: en Fase 1 el programa hace **lo mismo que hoy** pero sobre la arquitectura nueva → punto de control seguro antes de añadir features.
4. A partir de ahí, cada fase añade capacidades sin reescribir el render base.

**Paleta:** v2.0 usa solo `#8DC26F`. La nueva paleta principal de marca pasa a ser la default, dejando la de v2.0 como preset "alternativo/legacy":
- Verde principal `#9FB842`, verde oliva `#6F7F32`, verde profundo `#4F5E26`
- Blanco crema `#F7F1E8`, café translúcido `rgba(43,30,24,0.62)`, sombra `rgba(20,12,8,0.45)`
- Preset alternativo: verde lima `#8DC26F`

---

## 6. Roadmap por fases

| Fase | Nombre | Entregable |
|------|--------|------------|
| **1** | **Núcleo del editor** | Capas + selección visual con handles + formatos + guardar/abrir + export + undo/redo |
| 2 | Carruseles | Multi-lámina, miniaturas, reordenar, copiar estilo/textos/posiciones, "aplicar a todas", exportar todas |
| 3 | Edición de foto base | Zoom, recorte/encuadre, brillo, contraste, saturación, calidez, nitidez, sombras, viñeta, overlays |
| 4 | Texto rico + capas nuevas | Fuente por elemento (dropdown), bold/italic/underline, interlineado, tracking, stroke, rotación; capas CTA, líneas decorativas, puntos de carrusel, bloques de texto extra |
| 5 | Presets de marca | Layouts A–E aplicables + librería de copys + presets de paleta |
| 6 | Pulido | Atajos de teclado, snap/guías finas, rendimiento, manejo de errores, aviso de cambios sin guardar |

---

## 7. FASE 1 — Núcleo del editor (detalle)

Objetivo: convertir la app en un editor de **una sola lámina** con capas totalmente manipulables. Es la base de todo lo demás.

### Tareas

**1.1 Esqueleto del paquete + port del render**
- Crear `dcpub/` y el lanzador delgado.
- Portar render y fuentes de v2.0. La app abre y muestra la misma composición que hoy, ahora vía `Slide` + capas.

**1.2 Modelo de datos**
- `models.py` con `Project`, `Slide`, `Layer` y subclases (dataclasses), más `to_dict`/`from_dict`.
- Factory que crea el proyecto por defecto (foto + logo + título + subtítulo + caja) con los valores de v2.0.

**1.3 Formatos**
- Selector de formato: `1080×1350 (4:5)`, `1080×1440 (3:4)`, `1080×1920 (9:16)`, y **personalizado**.
- El lienzo pasa a tener el tamaño del formato; la **foto** es una `PhotoLayer` de fondo tipo *cover* movible/escalable dentro del marco (sin deformar). *(Los ajustes fotográficos avanzados llegan en Fase 3; en Fase 1 basta con cover + zoom + offset.)*
- Cambiar de formato reencuadra sin romper las posiciones fraccionales de las demás capas.

**1.4 CanvasEditor con selección y handles**
- Vista previa grande (≥70% del ancho), centrada, escalada al canvas.
- **Click** selecciona la capa superior bajo el cursor (usa los bbox del `Renderer`).
- **Bounding box** visible en la capa seleccionada + **8 handles** de resize.
- **Drag** mueve; **arrastrar handle** redimensiona (con `mantener proporción` para logo/imágenes).
- **Flechas** del teclado mueven 1 paso; **Shift** = paso grande, **Alt** = paso fino.
- **Snap** a centro horizontal/vertical y a márgenes, con guías visibles.
- Mostrar en pantalla **coordenadas y tamaño** de la capa seleccionada.
- Respeta `locked` (no se selecciona/mueve) y `visible`.

**1.5 PropertyPanel (derecha)**
- Se arma según el tipo de capa: X, Y, W, H (numérico), tamaño/escala, opacidad, bloquear, mostrar/ocultar, alinear/centrar rápido.
- Edición bidireccional: cambiar en el panel actualiza el canvas y viceversa. *(Tipografía/color/estilos ricos = Fase 4; en Fase 1, lo mínimo de texto: contenido y tamaño.)*

**1.6 Panel de capas (izquierda)**
- Lista de capas con toggles de **visible** y **bloqueo**, **subir/bajar** (orden z), **duplicar**, **eliminar**, **renombrar**.

**1.7 Undo/Redo**
- `CommandStack` para mover, redimensionar, cambios de propiedad, agregar/eliminar/duplicar/reordenar capa. Atajos `Ctrl+Z` / `Ctrl+Y`.

**1.8 Guardar / abrir proyecto**
- `ProjectManager` guarda/carga `.json` con rutas relativas. Aviso al salir si hay **cambios sin guardar**.

**1.9 Exportar**
- Exportar la lámina a **PNG** (y JPG opcional) en **resolución real** del formato.
- Elegir carpeta destino; crear `publicaciones/` si no existe; nombrado por proyecto + fecha/hora.

### Criterios de aceptación (Fase 1)
- Al abrir, la app muestra la composición de marca correcta sobre un formato seleccionable.
- Puedo seleccionar cualquier capa con click, verla resaltada con handles, moverla y redimensionarla con mouse y teclado, y verlo reflejado en tiempo real.
- Puedo ocultar, bloquear, reordenar, duplicar, renombrar y eliminar capas.
- Puedo deshacer y rehacer cualquier acción de edición.
- Puedo guardar el proyecto, cerrarlo, reabrirlo y continuar exactamente donde quedé.
- Puedo exportar un PNG a resolución real (p.ej. 1080×1350) idéntico a la vista previa.
- La foto base nunca se deforma al cambiar de formato ni al escalar.

---

## 8. Convenciones de código

- Nombres y comentarios en español; código limpio y modular.
- Sin pseudocódigo ni partes "por completar" dentro de una fase entregada.
- Cada módulo con responsabilidad única; evitar clases-Dios.
- La UI **no** recalcula todo en cada evento: el `Renderer` cachea el fondo (foto + overlay) y las fuentes por `(rol,tamaño)`, como ya hace v2.0.
- Mantener dos caminos de render: **preview** (escalado, rápido) y **export** (resolución real).

---

## 9. Verificación por fase

- Tras cada fase, ejecutar una **prueba headless** que instancie el modelo, renderice a preview y a resolución real, y guarde una imagen de control — sin abrir la GUI (evita depender de tkinter en entornos sin display).
- Comprobar el ciclo **guardar → cargar → re-renderizar** produce el mismo resultado.
- Revisar visualmente la imagen exportada contra el estilo de marca.

> Nota de entorno: al verificar, escribir/leer con las herramientas de archivo directamente. Si un sandbox Linux muestra el archivo truncado o con bytes nulos, es un problema de sincronización del montaje, no del código; validar la lógica con una copia creada dentro del propio sandbox.

---

## 10. Cómo trabajar esto con Codex

1. Coloca este archivo como `AGENTS.md` en la raíz del proyecto (junto a `generar_publicacion.py`, `logo-sin-fondo.png`, `fonts/` y tus fotos).
2. Inicializa git (`git init`) para poder deshacer a nivel de proyecto y revisar diffs.
3. Pídele a Codex **una tarea de la Fase 1 a la vez** (1.1, luego 1.2, …), y que haga commit al cerrar cada una.
4. No avances a la Fase 2 hasta cumplir los criterios de aceptación de la Fase 1 y pasar la verificación headless.
5. Reutiliza siempre el motor de render y fuentes de v2.0; no lo reescribas desde cero.
