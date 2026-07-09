# Resumen Tareas 1.6-1.9

## Que se implemento

- Panel de capas en el lateral izquierdo: visible/bloqueo, seleccionar, renombrar, subir/bajar, duplicar y eliminar.
- Undo/redo con `CommandStack` para cambios de propiedades, drag/resize, nudges, toggles, reordenar, duplicar y eliminar.
- Guardar/abrir proyecto JSON con rutas relativas cuando es posible y seguimiento de cambios sin guardar.
- Exportar imagen a PNG/JPG desde el estado actual en memoria, con carpeta configurable y nombre por proyecto/fecha.

## Revision final

La revision de rama completa detecto un bloqueo antes del merge: algunos cambios directos de UI (texto, icono, foto, formato y reset) no marcaban el proyecto como sucio, y el flujo "Guardar antes de continuar" seguia adelante aunque el usuario cancelara el dialogo de guardado. Se corrigio en `dcpub/app.py` y se agrego `tests/test_app_save_flow.py`.

Tambien se confirmo que:

- `_open_project()` limpia el historial con `CommandStack.clear()` sin disparar `on_change`.
- `_after_history_change()` refresca sliders, propiedades, lista de capas y render despues de undo/redo.
- `_export()` usa `_sync_text_to_layers()` y `_build_layers()`, por lo que exporta el estado actual en memoria.
- Abrir proyecto resetea seleccion, refresca paneles y deja el proyecto cargado sin marca de cambios pendientes.

## Triage de notas Important

- Capas duplicadas no editables desde el panel de propiedades: queda como deuda tecnica conocida. No bloquea este merge porque viene de la limitacion arquitectonica actual de `_kind_of()`/`_layer_by_kind()`, que reconoce una instancia canonica por tipo.
- Ruta del logo sin widget UI: queda como deuda tecnica conocida. No bloquea este merge porque el flujo actual usa el logo fijo desde constantes.

## Verificacion

- Worktree de revision: `python -m unittest discover -s tests -v` => 104/104 OK.
- `main` tras merge fast-forward: `python -m unittest discover -s tests -v` => 104/104 OK.
- El sandbox no ve el Pillow instalado en user-site; las verificaciones se ejecutaron en el entorno real de Windows.

## Estado final

- Rama `worktree-fase1-tareas-1.6-1.9` mergeada a `main` por fast-forward.
- `main` pusheado a `origin/main`.
- Worktree temporal desregistrado de Git y rama local `worktree-fase1-tareas-1.6-1.9` eliminada.
- Quedo una carpeta fisica residual en `.claude/worktrees/fase1-tareas-1.6-1.9` que Windows no permitio borrar porque esta en uso por otro proceso. `git worktree list` ya no la registra como worktree activo.
