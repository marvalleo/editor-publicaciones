"""Patrón Command para undo/redo: CommandStack y comandos concretos sobre
capas del proyecto."""


class PropertyChangeCommand:
    """Cambia un único atributo de `target` de `old_value` a `new_value`,
    reversible. Cubre mover, redimensionar, opacidad, zoom/offset de foto,
    toggle visible/locked, renombrar y centrar rápido: todos son, en el fondo,
    "restaurar un valor anterior a un atributo"."""

    def __init__(self, target, attr, old_value, new_value):
        self.target = target
        self.attr = attr
        self.old_value = old_value
        self.new_value = new_value

    def execute(self):
        setattr(self.target, self.attr, self.new_value)

    def undo(self):
        setattr(self.target, self.attr, self.old_value)


class DictItemChangeCommand:
    """Como PropertyChangeCommand pero para un valor dentro de un dict
    anidado (adjust/overlay de PhotoLayer), reversible igual."""

    def __init__(self, target_dict, key, old_value, new_value):
        self.target_dict = target_dict
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

    def execute(self):
        self.target_dict[self.key] = self.new_value

    def undo(self):
        self.target_dict[self.key] = self.old_value


class AddLayerCommand:
    """Inserta `layer` en `layers_list` en la posición `index`."""

    def __init__(self, layers_list, layer, index):
        self.layers_list = layers_list
        self.layer = layer
        self.index = index

    def execute(self):
        self.layers_list.insert(self.index, self.layer)

    def undo(self):
        self.layers_list.remove(self.layer)


class DeleteLayerCommand:
    """Quita `layer` de `layers_list`, recordando su índice original para
    poder reinsertarlo en el mismo lugar al deshacer."""

    def __init__(self, layers_list, layer):
        self.layers_list = layers_list
        self.layer = layer
        self.index = None

    def execute(self):
        self.index = self.layers_list.index(self.layer)
        self.layers_list.remove(self.layer)

    def undo(self):
        self.layers_list.insert(self.index, self.layer)


class ReorderLayerCommand:
    """Intercambia el `z` de dos capas."""

    def __init__(self, layer_a, z_a_old, z_a_new, layer_b, z_b_old, z_b_new):
        self.layer_a = layer_a
        self.z_a_old = z_a_old
        self.z_a_new = z_a_new
        self.layer_b = layer_b
        self.z_b_old = z_b_old
        self.z_b_new = z_b_new

    def execute(self):
        self.layer_a.z = self.z_a_new
        self.layer_b.z = self.z_b_new

    def undo(self):
        self.layer_a.z = self.z_a_old
        self.layer_b.z = self.z_b_old


class AddSlideCommand:
    """Inserta `slide` en `slides_list` en la posición `index`."""

    def __init__(self, slides_list, slide, index):
        self.slides_list = slides_list
        self.slide = slide
        self.index = index

    def execute(self):
        self.slides_list.insert(self.index, self.slide)

    def undo(self):
        self.slides_list.remove(self.slide)


class DeleteSlideCommand:
    """Quita `slide` de `slides_list`, recordando su índice original para
    poder reinsertarlo en el mismo lugar al deshacer."""

    def __init__(self, slides_list, slide):
        self.slides_list = slides_list
        self.slide = slide
        self.index = None

    def execute(self):
        self.index = self.slides_list.index(self.slide)
        self.slides_list.remove(self.slide)

    def undo(self):
        self.slides_list.insert(self.index, self.slide)


class ReorderSlideCommand:
    """Intercambia la posición de dos láminas en `slides_list`. El intercambio
    es su propia operación inversa, así que undo() reusa execute()."""

    def __init__(self, slides_list, index_a, index_b):
        self.slides_list = slides_list
        self.index_a = index_a
        self.index_b = index_b

    def execute(self):
        self.slides_list[self.index_a], self.slides_list[self.index_b] = (
            self.slides_list[self.index_b], self.slides_list[self.index_a])

    def undo(self):
        self.execute()


class CompositeCommand:
    """Agrupa varios comandos para que undo/redo los trate como una sola
    unidad (ej.: mover x e y de un drag diagonal es UN gesto del usuario)."""

    def __init__(self, commands):
        self.commands = commands

    def execute(self):
        for cmd in self.commands:
            cmd.execute()

    def undo(self):
        for cmd in reversed(self.commands):
            cmd.undo()


class CommandStack:
    """Pila de comandos reversibles con undo/redo. `push()` ya ejecuta el
    comando — quien llama no debe ejecutarlo por su cuenta antes."""

    def __init__(self, on_change=None):
        self._undo_stack = []
        self._redo_stack = []
        self._on_change = on_change

    def push(self, command):
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        if self._on_change:
            self._on_change()

    def undo(self):
        if not self._undo_stack:
            return False
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        if self._on_change:
            self._on_change()
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        if self._on_change:
            self._on_change()
        return True

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
