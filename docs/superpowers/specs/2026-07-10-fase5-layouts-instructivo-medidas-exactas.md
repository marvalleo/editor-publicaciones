# Instructivo de layouts con medidas exactas (fuente: usuario, vía GPT)

> Pegado tal cual lo entregó el usuario, para no perder detalle. Sirve como
> fuente de verdad para futuras mejoras de Fase 5 (Layouts). Las medidas
> están en **px sobre un lienzo de 1080×1350** (feed 4:5).
>
> **Estado de aplicación (2026-07-10):** los valores de posición/tamaño de
> Layouts A, B (solo variante B1, texto a la izquierda), C y D ya se
> aplicaron a `dcpub/presets/layouts.py`, convertidos de px a fracciones
> del lienzo. Lo que este instructivo pide y el editor **todavía no
> soporta** — y por lo tanto NO se aplicó — queda documentado en
> `docs/superpowers/specs/2026-07-10-fase5-layouts-design.md` (sección
> "Fuera de alcance") más esta lista:
>
> - **Alineación de texto** (centrado en A, izquierda/derecha en B1/B2):
>   el render de dcpub siempre dibuja título/subtítulo/texto libre alineados
>   a la izquierda (`align="left"` fijo en `render.py`). Layout A quedó
>   posicionado con los X del instructivo pero el texto NO se centra
>   visualmente — requiere agregar un campo `align` al modelo `TextLayer`
>   y tocar las 3 ramas de render (title/sub/free).
>   B2 (variante derecha) no se aplicó por el mismo motivo: con alineación
>   izquierda fija, el texto invadiría el lado equivocado del lienzo.
> - **Fondo degradado inferior** (Layout D): no existe ningún mecanismo
>   para agregar un degradado independiente de la foto de fondo. La
>   `PhotoLayer` sí tiene `overlay{bottom_grad, top_grad, strength}` pero
>   es una propiedad de la foto, no algo que un layout pueda "agregar".
> - **Caja de precio/promoción + sello** (Layout E completo): son
>   elementos nuevos (no existe ningún layer de "precio" ni "sello"), por
>   eso Layout E no se tocó en esta pasada — sigue con los valores
>   anteriores ("Banda ancha").
> - **Variantes B1/B2 como layouts separados**: hoy cada botón de layout
>   (A-E) es una sola configuración. Elegir cuál variante mostrar (o
>   agregar botones B1/B2 separados) es una decisión de diseño pendiente.
> - **Íconos/sellos opcionales, líneas decorativas propias de cada
>   layout**: `LineLayer`/ícono de la caja ya existen como capas, pero un
>   layout hoy solo puede reposicionar capas que YA existen en la lámina
>   (decisión explícita de Fase 5: "sin agregar/quitar capas"). Layouts A
>   y B piden líneas decorativas — no se agregaron automáticamente.

---

## Instructivo original (texto completo del usuario)

Todas las medidas están definidas para piezas de **1080 × 1350 px**,
relación **4:5**, formato feed de Instagram.

Las coordenadas se expresan así:

- **X:** distancia desde el borde izquierdo.
- **Y:** distancia desde el borde superior.
- **W:** ancho del elemento.
- **H:** alto del elemento.

### Reglas generales para todos los layouts

#### Área segura

Mantener todos los textos y elementos importantes dentro de esta zona:

- Margen izquierdo: **72 px**
- Margen derecho: **72 px**
- Margen superior: **60 px**
- Margen inferior: **70 px**

Área útil aproximada: X: 72 a 1008 px · Y: 60 a 1280 px. No colocar
textos esenciales demasiado cerca de los bordes.

#### Logo oficial

Tamaño recomendado: entre 150 y 190 px de diámetro. Tamaño estándar:
170 × 170 px. No deformarlo, recortarlo ni modificar su estructura.

#### Jerarquía tipográfica

**Título:** serif elegante, 76-100px, interlineado 0.92-1.05, color
`#F7F1E8`, sombra suave `rgba(20,12,8,0.45)`.

**Frase emocional:** script elegante, 46-62px, color `#9FB842`,
interlineado 1.0-1.1.

**Beneficio:** sans limpia o serif legible, 34-42px, color `#F7F1E8`,
interlineado 1.15-1.3.

**Frase inferior:** serif o sans limpia, 30-38px.

**CTA:** 32-38px, botón verde oliva, altura 74-86px.

### Layout A — Romántico central

Dormitorios, camas matrimoniales, tinajas, descanso, escapadas
románticas, escenas emocionales.

- Logo: X455 Y55 W170 H170 (centrado horizontalmente)
- Título: X100 Y245 W880 H125 — centrada, máx 2 líneas, 88-98px
- Frase emocional: X170 Y372 W740 H80 — centrada
- Línea izquierda: X95 Y410 W145 H4; línea derecha: X840 Y410 W145 H4;
  color `#9FB842`
- Caja de beneficio: X180 Y490 W720 H145, radio 28px, fondo
  `rgba(43,30,24,0.62)`, padding 46px horiz / 28px vert. Texto interno
  aprox X226 Y520 W628 H88
- Frase inferior opcional: caja X205 Y1115 W670 H82, radio 24px, texto
  centrado
- CTA cuando corresponda: X300 Y1210 W480 H82, radio 41px (zona libre si
  no hay CTA)
- Indicador de carrusel: centro horizontal 540px, Y1285, diámetro 14px,
  separación 18px

Visualmente: composición simétrica, alto peso emocional, texto
concentrado en el eje central; la foto debe tener espacio libre en el
centro o arriba; evitar si el sujeto principal está detrás del título.

### Layout B — Editorial lateral

Fachadas, pasarelas, caminos, ventanales, fotos con espacio libre a un
lado. Existe en versión izquierda (B1) o derecha (B2).

**B1 — texto a la izquierda:**
- Logo: X78 Y62 W150 H150
- Título: X80 Y255 W500 H220 — izquierda, 78-92px, máx 3 líneas
- Frase emocional: X82 Y480 W500 H90 — izquierda
- Línea decorativa: X82 Y575 W180 H4
- Caja de beneficio: X72 Y625 W500 H185, radio 24px, padding 36px horiz
  / 30px vert
- Frase inferior opcional: X78 Y1125 W500 H80
- CTA: X78 Y1212 W420 H80

**B2 — texto a la derecha** (medidas equivalentes invertidas):
- Logo: X852 Y62 W150 H150
- Título: X500 Y255 W500 H220 — derecha
- Frase emocional: X500 Y480 W500 H90 — derecha
- Línea decorativa: X820 Y575 W180 H4
- Caja de beneficio: X508 Y625 W500 H185
- Frase inferior opcional: X500 Y1125 W500 H80
- CTA: X582 Y1212 W420 H80

Visualmente: el lado opuesto al texto es para la foto; el bloque de
texto nunca supera 48% del ancho; sensación editorial y con aire; caja
de beneficio vertical o rectangular; ideal con foto de dirección clara
(camino, mirada hacia el fondo).

### Layout C — Funcional familiar

Living, cocina, comedor, baño, dormitorio múltiple, terraza, espacios
comunes.

- Logo centrada: X465 Y55 W150 H150 · o lateral: X80 Y65 W145 H145
- Título: X85 Y245 W910 H105 — izquierda o centrada según la foto,
  72-86px
- Frase emocional: X85 Y355 W760 H72 — 42-52px
- Caja de beneficio: X80 Y450 W920 H130, radio 22px, padding 40px horiz
  / 28px vert
- Ícono opcional: X112 Y486 W54 H54 (hoja, casa, cama, utensilio)
- Texto del beneficio con ícono: X190 Y475 W750 H82 · sin ícono: X125
  Y475 W830 H82
- Frase inferior opcional: X95 Y1135 W890 H76
- CTA: X295 Y1220 W490 H80

Visualmente: mensaje directo, mayor peso al beneficio concreto, menos
ornamentos que A; título funcional ("Cocina equipada", "Living
familiar", "Baño completo"); texto claro, no romántico.

### Layout D — Minimal premium

Cuando la foto es muy buena y puede vender casi por sí sola.

- Logo: X80 Y65 W145 H145 · o centrado: X467 Y60 W146 H146
- Título: X85 Y965 W910 H110 — izquierda o centrada, 74-90px
- Frase emocional o beneficio: X88 Y1080 W850 H80 — 38-48px
- Fondo degradado inferior: X0 Y850 W1080 H500, desde transparente hasta
  `rgba(20,12,8,0.68)`
- CTA opcional: X80 Y1208 W430 H78 (si no hay CTA, dejar como respiración
  visual)

Visualmente: máximo 2 bloques de texto; sin caja de beneficio grande;
sin varios íconos; sin muchas líneas decorativas; la foto debe ocupar
~75% de la atención visual; ideal para dormitorios limpios, fachadas
atractivas o paisajes.

### Layout E — Promoción o precio

Solo cuando existe precio, descuento, promoción o fecha especial.

- Logo: X455 Y55 W170 H170
- Título: X100 Y245 W880 H110 — centrada
- Caja de precio o promoción: X220 Y390 W640 H200, radio 30px, fondo
  verde profundo `#4F5E26` o café oscuro translúcido
- Precio principal: X260 Y415 W560 H100, 90-120px, blanco crema
- Texto auxiliar de precio: X270 Y520 W540 H50 (ej. "por noche", "para 2
  personas", "temporada baja")
- Beneficio: X170 Y635 W740 H120 (puede ir en caja café translúcida)
- CTA: X270 Y1185 W540 H88
- Sello opcional: X790 Y270 W170 H170 (solo si hay promoción real)

Visualmente: el precio es el segundo elemento más importante después de
la foto; debe entenderse en <3s; no usar más de un sello; evitar rojo,
amarillo fosforescente o estética de descuento masivo; mantener
elegancia de marca.

### Aplicación recomendada al carrusel actual (8 fotos Cabañas Don Cristóbal)

1. Pasarela y acceso → B1 o D. Logo X80 Y60 W150 H150 · Título X80 Y250
   W540 H170 · Subtítulo X82 Y430 W580 H82 · Beneficio X75 Y535 W540
   H145 · sin CTA · dejar libre zona central e inferior de la pasarela.
2. Living familiar → C. Logo X465 Y55 W150 H150 · Título X85 Y250 W910
   H100 · Subtítulo X85 Y355 W760 H70 · Beneficio X80 Y455 W920 H130 ·
   sin CTA · no tapar sillones ni mesa central.
3. Salón con plantas → D o B2. Logo X850 Y65 W145 H145 · Título X500
   Y850 W500 H120 · Subtítulo X500 Y980 W500 H75 · Beneficio X500 Y1065
   W500 H130 · sin CTA · mantener libres las plantas centrales.
4. Terraza → C. Logo X80 Y65 W145 H145 · Título X80 Y240 W620 H100 ·
   Subtítulo X80 Y345 W620 H70 · Beneficio X80 Y445 W780 H135 · sin CTA ·
   no cubrir parrilla ni puerta.
5. Cocina → C funcional. Logo X465 Y55 W150 H150 · Título X85 Y245 W910
   H95 · Subtítulo X85 Y345 W820 H65 · Beneficio X80 Y440 W920 H130 ·
   sin CTA · evitar cubrir lavaplatos, cocina y muebles.
6. Baño → C minimal. Logo X80 Y65 W140 H140 · Título X80 Y250 W600 H95 ·
   Subtítulo X80 Y350 W650 H65 · Beneficio X80 Y445 W700 H125 · sin CTA ·
   caja estrecha para no cubrir el lavamanos.
7. Dormitorio matrimonial → A. Logo X455 Y55 W170 H170 · Título X100
   Y250 W880 H115 · Subtítulo X170 Y375 W740 H78 · Beneficio X180 Y490
   W720 H140 · sin CTA · cama visible en la mitad inferior.
8. Dormitorio amplio → C con tratamiento cálido. Logo X465 Y55 W150 H150
   · Título X85 Y245 W910 H105 · Subtítulo X85 Y355 W760 H72 ·
   Beneficio X80 Y450 W920 H135 · sin CTA · no cubrir ninguna de las dos
   camas.

### Regla final de consistencia

Aunque cambie la distribución, todas las piezas deben conservar: mismo
tamaño de logo (o variación máxima de 20px), mismo color de título,
mismo verde para subtítulos, mismo estilo de cajas translúcidas,
márgenes mínimos de 72px, máximo 3 niveles jerárquicos visibles, sin CTA
en este carrusel, sin inventar frases adicionales fuera del JSON o del
copy aprobado.
