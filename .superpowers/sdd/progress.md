# Progreso — Tarea 1.5 (PropertyPanel dinámico)

Plan: docs/superpowers/plans/2026-07-08-fase1-tarea1.5-property-panel.md

- Task 1 (opacidad en render.py): complete (commits 08d445a..089fc20, review clean tras 2 rondas de fix)
  - Fix Round 1: tests no commiteados + blending roto en icono/lineas decorativas (draw.line/arc)
  - Fix Round 2: mismo bug de blending tambien en texto de titulo/subtitulo (draw.text)
- Task 2 (panel dinamico en app.py): complete (commits 3b803a1..5fe6555, review clean)
  - Minor sin resolver (no bloqueante, para revision final): _on_entry_commit no envuelve
    var.set() en self._updating, causa un _on_slider redundante inofensivo (app.py, ~linea 497)

Pendiente: revision final de toda la rama antes de mergear.
