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
