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
