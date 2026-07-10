# Progreso — Tareas 1.6-1.9

Plan: docs/superpowers/plans/2026-07-08-fase1-tareas-1.6-1.9.md

- Tarea 1 (panel de capas): complete (commit 45b1eb4, review clean)
  - Nota para revision final (Important, no bloqueante): las capas duplicadas via
    boton de capas no son editables en el panel de propiedades derecho, porque
    _kind_of() solo reconoce una instancia canonica por tipo (logo/title/sub/desc).
    Limitacion arquitectonica preexistente al adaptador render<->modelo, expuesta
    por la nueva funcion de duplicar. No estaba pedida su resolucion en el plan.
- Tarea 2 (undo/redo): pendiente
- Tarea 3 (guardar/abrir proyecto): pendiente
- Tarea 4 (exportar): pendiente
- Tarea 2 (undo/redo): complete (commits ebb6544..a80b4ea, review clean, 19 tests en test_commands.py)
- Tarea 3 (guardar/abrir proyecto): complete (commits 31f6ddc..58ab31a, review clean)
  - Nota (Minor, no bloqueante): la ruta del logo nunca se sincroniza con la UI
    (no hay widget v_logo) — gap preexistente del brief, no del implementador.
- Tarea 4 (exportar): complete (commits 103a784..a6f1bda, review clean)

Revision final de rama completa: complete (commit de fix 9adac35).

- Tests: `python -m unittest discover -s tests -v` => 104/104 OK en entorno real
  Windows con Pillow instalado en user-site. En sandbox fallaba la importacion de PIL
  por aislamiento del site-packages de usuario.
- Hallazgo bloqueante corregido: los cambios directos de texto/icono/foto/formato
  no marcaban el proyecto como sucio, y confirmar "Guardar" antes de abrir/cerrar
  podia continuar aunque el usuario cancelara el dialogo de guardar. Corregido en
  `dcpub/app.py` y cubierto por `tests/test_app_save_flow.py`.
- Interacciones revisadas:
  - `_open_project()` llama `self.commands.clear()`; `CommandStack.clear()` no
    dispara `on_change`, por lo que el proyecto cargado no queda sucio por error.
  - `_after_history_change()` refresca sliders, panel de propiedades, panel de
    capas y render despues de undo/redo que toque `self.slide.layers`.
  - `_export()` sincroniza widgets a modelo con `_sync_text_to_layers()` y exporta
    desde `_build_layers()`, es decir, desde el estado en memoria actual.
  - Abrir proyecto resetea `self._selected`, refresca paneles y deja `_dirty=False`.
- Triage de notas Important:
  - Capas duplicadas no editables desde propiedades: deuda tecnica conocida, no
    bloquea este merge porque corresponde a la limitacion arquitectonica de una
    instancia canonica por tipo en `_kind_of()`/`_layer_by_kind()`.
  - Ruta del logo sin widget UI: deuda tecnica conocida, no bloquea este merge
    porque el flujo de usuario actual usa el logo fijo definido en constantes.

Veredicto: aprobada para merge a main.

# Progreso — Fase 2 carruseles

Plan: docs/superpowers/plans/2026-07-09-fase2-carruseles.md

- Tarea 1 (comandos de lista de laminas): complete (commit a88386d..73c0415, review clean)
- Tarea 2 (duplicar lamina y copiar estilo): complete (commit 73c0415..f8f30db, review clean)
  - Nota (Minor, no bloqueante): plan_copia_estilo usa shallow copy (dict()) para campos dict
    anidados como adjust, en vez de deepcopy. No es bug hoy (adjust solo tiene floats), pero si
    se agregan dicts anidados dentro de adjust en el futuro, podria compartir referencias.
- Tarea 3 (estado de lamina activa en App): complete (commit f8f30db..dff5e9b, review clean, 149 tests)
- Tarea 4 (acciones de lamina: add/duplicate/delete/move/copy-style): complete (commit dff5e9b..7c6b59e, review clean, 159 tests)
  - Notas Minor no bloqueantes: calculo de nuevo_index con -2 magico en _delete_slide (correcto,
    poco legible); imports locales repetidos por metodo (consistente con patron preexistente).
- Tarea 5 (generalizar capas por lamina + logo compartido): complete (commits 7c6b59e..474706a, fix a53cb5d, review clean, 172 tests)
  - Fix aplicado: checkbox de logo compartido no se resincronizaba al abrir un proyecto (riesgo
    de sobreescribir silenciosamente el logo compartido guardado). Corregido en _open_project.
- Tarea 6 (panel de miniaturas, dcpub/slides_panel.py): complete (commits a53cb5d..0f6ae58, fix bbeead8, review clean, 172 tests)
  - Desviaciones justificadas del implementador: orden de instanciacion de SlidesPanel movido al
    final de _build_left (pack before=lbl_textos) porque el brief literal rompia el arranque
    (widgets txt_title/txt_desc no existian aun); guard try/except en _thumbnail_for para foto
    ausente (compose() con src="" lanzaba FileNotFoundError). Fix post-revision: logging de la
    excepcion antes del placeholder gris.
- Tarea 7 (verificacion headless de cierre): complete (commit bbeead8..927e05b, review clean, 172 tests, HEADLESS_OK)
  - Desviacion justificada: compose() requiere FontManager real (no None), el brief tenia un
    error pasando None. Corregido instanciando FontManager en el script.

# Revision final de rama completa (Fase 2 carruseles)

Revision final: hallazgo Critical encontrado y corregido (undo/redo de operaciones de lamina
dejaba self.slide/current_slide_index desincronizados de project.slides tras Ctrl+Z de
agregar/eliminar/mover lamina) + 2 hallazgos Important (cache de miniaturas no invalidaba con
logo compartido; drag/resize/nudge/centrar del logo se revertian silenciosamente con logo
compartido activo). Los 3 corregidos en 2 commits de fix (4ad8f0f, aa18438), con tests que
reproducen los escenarios reales. Suite final: 179 tests OK. Headless: HEADLESS_OK.

Veredicto: aprobada para merge.

# Progreso — Fase 3 foto base

Plan: docs/superpowers/plans/2026-07-09-fase3-foto.md

- Tarea 1 (fix adjust/overlay no llegaban al render): complete (commit 5dd7835..e135b9e, review clean, 190 tests)
- Tarea 2 (rangos/etiquetas de ajuste): complete (commit 813d923..81603eb, review clean, 193 tests)
- Tarea 3 (DictItemChangeCommand): complete (commit 9cc639c..fe72361, review clean, 196 tests)
- Tarea 4 (params anidados en sliders/undo): complete (commit cd060d0..602edf4, review clean, 200 tests)
- Tarea 5 (seccion de UI Ajustes): complete (commit 243d6fc..8602f86, review clean, 203 tests)
- Tarea 6 (excess_for_zoom / offset_delta_for_drag): complete (commit 87f6efc..092c08b, review clean, 209 tests)
  - Nota (Minor, no bloqueante): tests de TestExcessForZoom/TestOffsetDeltaForDrag usan
    asserts direccionales (>0/<0) en vez de valores exactos calculables a mano, tal como
    los especifica el plan verbatim. No es negligencia del implementador.
- Tarea 7 (drag para panear en canvas): complete (commit 55889c5..45d4acc, review clean, 211 tests)
- Tarea 8 (zoom con rueda del mouse): complete (commit e9d8dba..60d20ea, fix aplicado y re-revisado,
  216 tests). Hallazgo Important corregido: faltaba test del colapso de undo en burst de rueda; se
  agrego test que llama _commit_wheel_zoom directo y verifica un solo PropertyChangeCommand.
- Tarea 9 (verificacion headless de cierre): complete (commit 008a231..f4a67d8, review clean,
  216 tests, HEADLESS_OK)

# Revision final de rama completa (Fase 3 foto base)

Revision final: sin hallazgos Critical ni Important. Confirmado que el fix de Tarea 1
(adjust/overlay llegan al render por referencia) sigue vigente tras Tareas 5/7/8; que
_on_press/_on_drag/_on_release discriminan correctamente entre resize, photo-pan y drag
normal sin fallthrough; que la regla "la foto nunca se deforma" se respeta en todo el
codigo nuevo (pan solo escribe offset_x/offset_y, wheel solo escribe zoom); y que
undo/redo refresca el panel de ajustes correctamente. Notas Minor no bloqueantes: parseo
de params con punto duplicado en 4 metodos (deuda aceptable, candidato a limpieza cuando
Fase 4 vuelva a tocar el panel de propiedades); pan+wheel simultaneo (no alcanzable en
desktop single-pointer). Suite final: 216 tests OK. Headless: HEADLESS_OK.

Veredicto: aprobada para merge.

# Progreso — Fase 4 sub-fase 1 (CTA + caja de descripcion configurable)

Plan: docs/superpowers/plans/2026-07-09-fase4-cta-caja.md

- Tarea 1 (modelo: BoxLayer.fill/text_color + CTALayer): complete (commit 162b434..578af3f, review clean, 218 tests)
- Tarea 2 (render desc configurable con fallback legado): complete (commit 4f26074..2508b15, review clean, 223 tests)
- Tarea 3 (render rama cta nueva): complete (commit 0a4fd80..cc38b76, review clean, 227 tests)
- Tarea 4 (adaptadores _build_layers_for / Exporter): complete (commit 478b1c7..2892922, review clean, 231 tests)
- Tarea 5 (migracion automatica de proyectos legado): complete (commit 5c26638..ca9841f, review clean, 235 tests)
- Tarea 6 (batch_import crea CTALayer real): complete (commit 828d331..3789b43, review clean, 236 tests)
- Tarea 7 (panel de propiedades reconoce cta + sliders w/h): complete (commit b5500ef..da1a014, review clean, 239 tests)
- Tarea 8 (selector de color fill/text_color): complete (commit fb412e0..ac7d8ef, review clean, 243 tests)
- Tarea 9 (boton Agregar CTA + campo de texto propio): complete (commit 5aba54b..c72ecb9, review clean,
  247 tests). Desviacion documentada y confirmada segura: _add_cta_layer no usa _set_selected (el brief
  original rompia el fixture headless al disparar _render_now via v_photo inexistente); se uso
  self._selected + _build_property_panel directo, con el mismo _refresh_layers_list/_schedule_render
  que ya traia el brief. Sin regresion de comportamiento en la app real.
- Tarea 10 (verificacion headless de cierre): complete (commit 33274a1..2bdde38, review clean, 247 tests, HEADLESS_OK)

# Revision final de rama completa (Fase 4 sub-fase 1: CTA + caja configurable)

Revision final: 1 hallazgo Important (no de implementacion, del propio diseno) — h=0.12 fijo
como default/migracion de BoxLayer rompia la paridad visual "se ve igual que antes" para
descripciones largas (4+ lineas, comunes en listas de beneficios importadas por lotes), porque
el render legado usaba auto-height y 0.12*H podia quedar mas chico. Presentado al usuario, quien
eligio h=0 (auto-height) en vez de mantener el fijo. Corregido en commit de fix b47d242: default
en crear_slide_por_defecto y _LEGACY_BOX_DEFAULT_H en project_io.py pasan de 0.12 a 0.0 (w se
mantiene en 0.90 sin cambios). 6 referencias a 0.12 encontradas y actualizadas (modelo, migracion,
2 tests, script de verificacion x2). Re-revision del fix: aprobada. Nota Minor no bloqueante:
test_partial_zero_w_h_box_layer_only_fixes_the_zero_dimension quedo tautologico en el eje h
(0.0 entra, 0.0 sale) — no prueba que la migracion realmente corrio, deuda de cobertura aceptada.

Otros hallazgos Minor de la revision final (no bloqueantes, no corregidos):
- corner_r fijo (~0.033*W) puede exceder la mitad del alto/ancho en cajas muy chicas (min del
  slider h=0.03) — cosmetico, Pillow no rompe, se corrige si se vuelve a tocar render.py.
- Rangos de sliders w/h inline en vez de centralizados en un dict tipo BOX_WH_RANGE.
- Desviacion de Tarea 9 (_add_cta_layer sin _set_selected) reconfirmada benigna en la revision final.

Suite final: 247 tests OK. Headless: HEADLESS_OK.

Veredicto: aprobada para merge.

# Progreso — Fase 4 sub-fase 2 (texto rico por elemento)

Plan: docs/superpowers/plans/2026-07-09-fase4-texto-rico.md

- Tarea 1 (modelo: campos nuevos en TextLayer): complete (commit c96809f, review clean, 248 tests)
- Tarea 2 (FontManager family + TEXT_STROKE_COLOR): complete (commit 423ee10, review clean, 251 tests)
- Tarea 3 (render: helpers puros tracking/stroke/subrayado): complete (commit 02c75b9, review clean, 258 tests)
- Tarea 4 (render: transformaciones italica y rotacion): complete (commit 6217417, review clean, 262 tests)
- Tarea 5 (render: rama title usa pipeline texto rico): complete (commit d6fe579, 270 tests). Desviacion del
  brief confirmada y aprobada por el usuario: el brief pedia reemplazar la rama title por UN pipeline unico
  que reproduce el render legado via defaults; se intento verbatim y rompio
  test_title_and_sub_opacity_one_matches_original_direct_draw por diferencia real de blending de Pillow entre
  draw.text() directo sobre canvas opaco (legado, opacity=1.0) vs dibujar en capa transparente + alpha_composite
  (requerido por el pipeline nuevo para soportar italica/rotacion). Causa raiz confirmada con git stash. El
  usuario eligio mantener el enfoque dual-path del implementador (rama legado intacta + rama nueva de texto
  rico via gate has_rich_text) en vez de tolerar la diferencia de pixeles. Aceptado como excepcion documentada
  al diseno original del plan para Tarea 5 y, por el mismo motivo tecnico, tambien aplica a Tarea 6 (rama sub).
- Tarea 6 (render: rama sub usa pipeline texto rico): complete (commit f4df729, review clean, 274 tests).
  Aplico el mismo patron dual-path pre-aprobado en Tarea 5 (instruido directamente al implementador, sin
  necesidad de ronda de fix): rama legado intacta byte a byte + rama nueva con formulas propias de sub
  (shadow offset (2,2) y alpha 130, distintas de title (3,3)/160; sin line_spacing en el gate porque sub
  es una sola linea). Lineas decorativas verificadas sobre geometria sin transformar.
- Tarea 7 (adaptadores app.py/_build_layers_for + exporter.py/_layers_from_slide): complete
  (commit 693dddc, review clean, 278 tests)
- Tarea 8 (panel de propiedades: dropdown fuente + bold/italic/underline/stroke + sliders
  interlineado/tracking/grosor/rotacion): complete (commit 38cb365, review clean, 282 tests).
  Nota Minor plan-mandated no bloqueante: _on_font_family_change llama _schedule_render() incluso
  cuando el valor no cambia (codigo verbatim del brief), desperdicia un render de mas en un no-op.
- Tarea 9 (verificacion headless de cierre): complete, HEADLESS_OK (282 tests)

# Revision final de rama completa (Fase 4 sub-fase 2: texto rico)

Revision final (modelo mas capaz): sin hallazgos Critical ni Important. Confirmado end-to-end el
encadenamiento de campos font_family/bold/stroke_width desde TextLayer (Tarea 1) pasando por los
adaptadores app.py/exporter.py (Tarea 7) hasta compose() (Tareas 5/6) con nombres de clave
consistentes; preview y export coinciden exactamente en los mismos 9 campos. Gates has_rich_text
de title y sub verificados completos (stroke_width es inerte sin stroke_on, que si esta gateado;
sub omite line_spacing legitimamente por ser una sola linea). Proyectos legado cargan bien via
defaults del dataclass. Geometria/pad de _render_text_lines_to_image confirmada suficiente para
que stroke/bold no se corten en los bordes.

5 hallazgos Minor no bloqueantes: (1) default de line_spacing=0.0 queda fuera del rango del
slider (0.8-2.5), cosmetico; (2) togglear "Contorno" no refresca el estado disabled del slider de
grosor hasta reabrir el panel; (3) checkboxes/combobox no reflejan undo/redo hasta reconstruir el
panel (patron preexistente, no regresion); (4) ~40-80 lineas duplicadas de dibujo legado en
title/sub bajo el gate has_rich_text quedan como candidato a extraccion en Fase 6 (decision
dual-path ya aprobada por el usuario, no se re-litiga); (5) _on_font_family_change dispara un
render de mas en no-op (ya registrado en Tarea 8).

Suite final: 282 tests OK. Headless: HEADLESS_OK.

Veredicto: aprobada para merge a main.

# Progreso — Fase 4: lineas decorativas + puntos de carrusel

Plan: docs/superpowers/plans/2026-07-10-fase4-lineas-puntos-tareas-codex.md

Implementado por Codex en una sesion externa (copia aislada por fallo de permisos de git
worktree en su sandbox), traido a este repo como rama `codex/fase4-lineas-puntos` a partir del
commit b5b7426 (un solo commit combinando Track A LineLayer + Track B DotsLayer, en vez de las
9+9 tareas separadas del listado original).

- LineLayer + DotsLayer en dcpub/models.py, ramas "line"/"dots" en compose(), botones agregar,
  sliders/color picker en panel de propiedades, resize por handle adaptado, adaptadores
  app.py/exporter.py, tests, verificacion headless. Las 6 decisiones de diseno del listado de
  tareas fueron seguidas correctamente (verificado en revision).

Hallazgos de revision (agente independiente, modelo mas capaz) y correccion:
- Hallazgo previo a la revision formal: corrupcion de encoding real (caracter '?' literal en vez
  de tildes/ene) en 11 strings de dcpub/app.py, tests y script de verificacion. Corregido en
  commit 7ffd6e7 antes de la revision.
- Important corregido (commit 47b0fd0): radios de DotsLayer eran fraccion fija de W (base ~74px,
  activo ~140px a W=1080), mayor que todo el rango del slider de spacing (5-129px), por lo que
  los puntos se fusionaban en una mancha a resolucion real. Ahora se recortan al spacing
  disponible. Cubierto por test nuevo a canvas realista (1080px) que verifica circulos discretos.
- Important corregido (commit 47b0fd0): _build_layers_for usaba self.current_slide_index para el
  punto activo en vez de self.project.slides.index(slide), por lo que SlidesPanel (que llama
  _build_layers_for por cada lamina del panel) resaltaba el punto activo equivocado en miniaturas
  de laminas no activas. El test original de Codex para este caso tenia el mismo defecto (seteaba
  current_slide_index sin mover app.slide, estado que no ocurre en la app real); se corrigio el
  test tambien.
- Minor corregido: cobertura de round-trip to_dict/from_dict para LineLayer/DotsLayer (pedida por
  las tareas A1/B1 originales, faltaba).
- Minor no corregido (diferido): boton "+ Agregar puntos" no tiene guard/aviso para proyectos de
  una sola lamina (pedido opcional del listado de tareas). No bloqueante: el render ya maneja
  count<=1 sin romper (dibuja un solo punto o nada).
- Minor no corregido (cosmetico, no bloqueante): reasignacion redundante de `draw` al final de las
  ramas "line"/"dots"; DotsLayer hereda `rotation` de Layer pero el render la ignora (intencional,
  el panel no expone rotacion para puntos, sin comentario explicito).

Suite final: 312 tests OK. Headless: HEADLESS_OK.

Veredicto: aprobada para merge a main.

# Progreso — Fase 4 (cierre): bloques de texto libre

Plan: docs/superpowers/plans/2026-07-10-fase4-texto-libre.md

- Tarea 1 (modelo: color en TextLayer): complete (commits b1299ea..23ad92e, review clean, 313 tests).
  Hallazgo corregido en el momento (no llego a revision, se detecto antes): el brief tenia un dato
  erroneo (asumia que BLANCO ya era el crema de marca #F7F1E8 sin verificar el valor real en
  constants.py, que era blanco puro). El implementador seteo BLANCO=(247,241,232) siguiendo el
  brief al pie de la letra, lo cual habria cambiado el color de titulo/subtitulo/caja/CTA en toda
  la app (BLANCO se usa globalmente en render.py). Revertido en un segundo commit: constants.py y
  palette.py vuelven a su estado exacto original (diff neto cero verificado), TextLayer.color
  queda en list(BLANCO)+[255] = [255,255,255,255], el blanco real que usa hoy el titulo. El crema
  de PALETA_PRINCIPAL es data de paleta para la futura Fase 5, todavia no esta cableada a compose().
- Tarea 2 (render: rama free con pipeline unico): complete (commit 4d6ba25, review clean, 318 tests).
  Desviacion justificada del implementador: el test de color del brief muestreaba el pixel exacto
  del centro geometrico del bbox, que para el texto "Bloque de prueba" en Lato-Regular caia en un
  hueco entre letras (transparente) por coincidencia de fuente/texto, no por un bug de render.
  Corregido a buscar el primer pixel opaco de la fila (verificado por el revisor que sigue
  distinguiendo color propio vs. color de marca correctamente). Nota Minor no bloqueante: el
  comentario del test dice "mas cercano al centro" pero en realidad es "primero de izquierda a
  derecha" — cosmetico, no afecta la cobertura.
- Tarea 3 (adaptadores app.py/_build_layers_for + exporter.py/_layers_from_slide): complete
  (commit 11609bb, review clean, 320 tests)
- Tarea 4 (boton "+ Agregar texto" + _add_text_layer): complete (commit b5667b2, review clean, 321 tests)
- Tarea 5 (panel de propiedades: reconoce free, texto multilinea + color picker, reusa
  _build_text_style_section y _on_cta_text_commit sin duplicar): complete (commit 623e421,
  review clean, 325 tests). Nota Minor no bloqueante: tk.Text sin wrap="word" (podria cortar
  palabras a la mitad en el editor), omision del propio brief, no del implementador.
- Tarea 6 (verificacion headless de cierre): complete, HEADLESS_OK (325 tests)

Veredicto: pendiente de revision final de rama completa.
