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
