# Fase 4 — Hallazgos de exploración (código actual)

Este documento registra hechos verificados en el código actual. No incluye decisiones de diseño ni cambios de implementación.

## 1. TextLayer — campos existentes vs. pedidos

`TextLayer` existe en `dcpub/models.py` como subclase de `Layer`. La clase base aporta los campos comunes, incluyendo posición, tamaño, rotación y opacidad (`dcpub/models.py:45-58`). `TextLayer` solo agrega `type`, `text`, `role` y `size` (`dcpub/models.py:84-88`).

Campos pedidos por Fase 4 que hoy no existen como campos propios de `TextLayer`:

- `font_family` / fuente por elemento.
- `bold`, `italic`, `underline`.
- `line_spacing`.
- `letter_spacing` / tracking.
- `stroke`.
- `align`.
- `color`.
- `shadow` configurable.

`rotation` sí existe, pero heredado desde `Layer`, no específico de `TextLayer` (`dcpub/models.py:57`).

En el render, el título se dibuja en la rama `elif kind == "title"` (`dcpub/render.py:362-397`). Usa `layer["text"]` (`dcpub/render.py:363`), `layer["size"]` (`dcpub/render.py:365`), fuente fija por rol con `font_manager.load("title", tsz)` (`dcpub/render.py:366`), sombra hardcodeada (`dcpub/render.py:377`, `dcpub/render.py:393-394`) y color fijo `BLANCO` (`dcpub/render.py:378`).

El subtítulo se dibuja en la rama `elif kind == "sub"` (`dcpub/render.py:399-434`). Usa `layer["text"]` (`dcpub/render.py:400`), `layer["size"]` (`dcpub/render.py:402`), fuente fija por rol con `font_manager.load("subtitle", ssz)` (`dcpub/render.py:403`), color `VERDE` (`dcpub/render.py:415`) y líneas decorativas calculadas en el propio render (`dcpub/render.py:410-419`).

El adaptador de UI a render tampoco pasa atributos tipográficos avanzados: para título solo entrega `type`, `key`, `text`, `x`, `y`, `size` y `opacity` (`dcpub/app.py:1371-1376`); para subtítulo entrega los mismos equivalentes (`dcpub/app.py:1377-1382`). El exportador hace lo mismo para título (`dcpub/exporter.py:58-67`) y subtítulo (`dcpub/exporter.py:68-77`).

Conclusión: hoy el render de texto solo contempla contenido, rol visual, posición, tamaño y opacidad. No aplica fuente por elemento, estilos, tracking, stroke, alineación configurable, color propio ni line spacing configurable.

## 2. rotation — campo fantasma

`rotation` existe en la clase base `Layer` (`dcpub/models.py:57`). Se serializa automáticamente porque `Layer.to_dict()` retorna `asdict(self)` (`dcpub/models.py:60-61`) y se reconstruye con `cls(**data)` en `layer_from_dict()` (`dcpub/models.py:107-110`).

También aparece en los campos de copia de estilo para photo, logo, text/title, text/subtitle y box (`dcpub/models.py:213-220`).

Pero `dcpub/render.py` no contiene ninguna referencia a `rotation`. Además, `_build_layers_for()` no lo pasa al diccionario plano de render para photo (`dcpub/app.py:1355-1358`), logo (`dcpub/app.py:1361-1370`), título (`dcpub/app.py:1374-1376`), subtítulo (`dcpub/app.py:1380-1382`) ni descripción (`dcpub/app.py:1387-1389`). El exportador tampoco lo pasa en `_layers_from_slide()` (`dcpub/exporter.py:36-88`).

Conclusión: `rotation` se guarda y se copia como estilo, pero actualmente no se aplica visualmente en el render.

## 3. BoxLayer — hardcodes

`BoxLayer` existe en `dcpub/models.py` con `type = "box"`, `text`, `icon` y `size` (`dcpub/models.py:91-96`). Hereda de `Layer` los campos comunes `x`, `y`, `w`, `h`, `rotation` y `opacity` (`dcpub/models.py:45-58`).

En el render, el recuadro de descripción corresponde a la rama `elif kind == "desc"` (`dcpub/render.py:436`). El ancho está hardcodeado al 90% del lienzo con `box_w = int(W * 0.90)` (`dcpub/render.py:441`). El alto se calcula desde el texto, ícono y padding (`dcpub/render.py:455-458`), no desde `layer["h"]`.

El color de caja se toma directo de la constante `BOX_COLOR`: se importa en `dcpub/render.py:7`, tiene default de paleta en `dcpub/render.py:27-29`, y el recuadro usa `box_fill = _apply_opacity(BOX_COLOR, opacity)` (`dcpub/render.py:462`). `BOX_COLOR` está definido en `dcpub/constants.py:7`.

El color del texto dentro del recuadro también está hardcodeado: `text_color = _apply_opacity(BLANCO + (255,), opacity)` (`dcpub/render.py:469`). `BLANCO` se importa en `dcpub/render.py:7` y se define en `dcpub/constants.py:6`.

El adaptador de UI a render pasa para descripción `type`, `key`, `text`, `icon`, `x`, `y`, `size` y `opacity` (`dcpub/app.py:1383-1389`). El exportador pasa los mismos campos equivalentes (`dcpub/exporter.py:78-88`). No se pasa `w`, `h`, color de caja, transparencia de caja separada de `opacity`, color de texto ni radio configurable.

Campos faltantes para soportar ancho/alto/color/transparencia por capa: al menos valores propios para ancho renderizado, alto renderizado o política de alto, fill/color de caja, alpha/transparencia de caja independiente si no se quiere reutilizar `opacity`, y color de texto. Esto queda como brecha factual, no como decisión de diseño.

## 4. CTALayer — estado de preparación

`CTALayer` no existe como clase en `dcpub/models.py`. El registro `LAYER_CLASSES` solo incluye `photo`, `logo`, `text` y `box` (`dcpub/models.py:99-104`).

La única mención explícita a CTA en el paquete está en el importador por lotes: el docstring indica que el CTA se preserva en `slide.extra["cta"]` y no se convierte en capa visual porque todavía no existe `CTALayer` en modelo/render (`dcpub/batch_import.py:33-38`).

La forma exacta del dato importado hoy es un string simple: `slide.extra["cta"] = str(entrada.get("cta", ""))` (`dcpub/batch_import.py:75`). `Slide.extra` se serializa y deserializa como diccionario (`dcpub/models.py:114-125`, `dcpub/models.py:128-135`).

Pregunta abierta factual para la etapa de diseño: como el pedido de CTA requiere caja, transparencia de caja y color de texto configurables, hay que decidir si eso generaliza `BoxLayer` o si amerita una clase separada `CTALayer`. Este documento no toma esa decisión.

## 5. Fuentes por elemento

`FontManager` carga fuentes por rol fijo. `_ROLE_MAP` define solamente `title`, `subtitle` y `body` (`dcpub/fonts.py:22-26`). `load(role, size)` usa `(role, size)` como clave de cache (`dcpub/fonts.py:31-35`) y resuelve `preferred, fallbacks = self._ROLE_MAP[role]` (`dcpub/fonts.py:38`). No acepta `font_family`, nombre de fuente, path arbitrario ni variante por elemento.

Fuentes de marca descargables hoy:

- `PlayfairDisplay-Bold.ttf` (`dcpub/constants.py:15-17`).
- `DancingScript-Regular.ttf` (`dcpub/constants.py:18-19`).
- `Lato-Regular.ttf` (`dcpub/constants.py:20-21`).

Fallbacks por rol:

- `title`: `georgiab.ttf`, `Georgia Bold.ttf`, `DejaVuSerif-Bold.ttf`, `LiberationSerif-Bold.ttf` (`dcpub/constants.py:24-25`).
- `subtitle`: `segoesc.ttf`, `Brush Script MT.ttf`, `Comic Sans MS.ttf`, `DejaVuSerif-Italic.ttf` (`dcpub/constants.py:26`).
- `body`: `calibri.ttf`, `Helvetica.ttf`, `Arial.ttf`, `DejaVuSans.ttf` (`dcpub/constants.py:27`).

`find_system_font()` busca archivos candidatos en `SYSTEM_FONT_DIRS` (`dcpub/fonts.py:10-16`), y esos directorios están definidos en `dcpub/constants.py:30-35`. Esto sirve como fallback por rol, pero no como listado de fuentes seleccionables por elemento.

## 6. LineLayer / DotsLayer

`LineLayer` y `DotsLayer` no existen en `dcpub/models.py` ni están registrados en `LAYER_CLASSES`, que solo incluye `photo`, `logo`, `text` y `box` (`dcpub/models.py:99-104`).

En `dcpub/render.py` no hay ramas de render para tipos `line` ni `dots`; `compose()` solo documenta y maneja `photo`, `logo`, `title`, `sub` y `desc` (`dcpub/render.py:291-310`, `dcpub/render.py:324-486`).

Hay líneas decorativas dibujadas dentro del subtítulo, pero son parte hardcodeada de la rama `sub`, no una `LineLayer` independiente (`dcpub/render.py:410-419`).

Conclusión: `LineLayer` y `DotsLayer` arrancan desde cero como capas de modelo/render. La única funcionalidad parecida existente son líneas decorativas internas del subtítulo.

## Preguntas abiertas para el brainstorming

- ¿El CTA debe ser una especialización/generalización de `BoxLayer` o una `CTALayer` separada?
- ¿La rotación debe aplicarse a todas las capas existentes desde el primer slice de Fase 4 o conviene empezar por texto/logo?
- ¿El selector de fuentes debe exponer solo fuentes de marca y fallbacks conocidos, o también fuentes instaladas del sistema?
- ¿La opacidad actual de `Layer.opacity` alcanza para la transparencia de caja, o el color de caja necesita alpha propio independiente del contenido/texto?
- ¿`BoxLayer.w` y `BoxLayer.h` deben pasar a controlar el tamaño visual real del recuadro o conviene mantener alto automático con ancho configurable?
