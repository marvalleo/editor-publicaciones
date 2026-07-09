"""Tests de dcpub.commands (CommandStack y comandos concretos)."""

import unittest

from dcpub.commands import (
    CommandStack, PropertyChangeCommand, AddLayerCommand, DeleteLayerCommand,
    ReorderLayerCommand, CompositeCommand,
    AddSlideCommand, DeleteSlideCommand, ReorderSlideCommand,
)


class _Dummy:
    """Objeto simple con atributos, para no depender de dcpub.models en estos tests."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestPropertyChangeCommand(unittest.TestCase):
    def test_execute_sets_new_value(self):
        obj = _Dummy(x=0.1)
        cmd = PropertyChangeCommand(obj, "x", 0.1, 0.5)
        cmd.execute()
        self.assertEqual(obj.x, 0.5)

    def test_undo_restores_old_value(self):
        obj = _Dummy(x=0.1)
        cmd = PropertyChangeCommand(obj, "x", 0.1, 0.5)
        cmd.execute()
        cmd.undo()
        self.assertEqual(obj.x, 0.1)


class TestDictItemChangeCommand(unittest.TestCase):
    def test_execute_sets_new_value(self):
        from dcpub.commands import DictItemChangeCommand
        adjust = {"brightness": 1.0}
        cmd = DictItemChangeCommand(adjust, "brightness", 1.0, 1.4)
        cmd.execute()
        self.assertEqual(adjust["brightness"], 1.4)

    def test_undo_restores_old_value(self):
        from dcpub.commands import DictItemChangeCommand
        adjust = {"brightness": 1.0}
        cmd = DictItemChangeCommand(adjust, "brightness", 1.0, 1.4)
        cmd.execute()
        cmd.undo()
        self.assertEqual(adjust["brightness"], 1.0)

    def test_works_inside_composite_command(self):
        from dcpub.commands import DictItemChangeCommand, CompositeCommand
        overlay = {"bottom_grad": False, "top_grad": False}
        cmd = CompositeCommand([
            DictItemChangeCommand(overlay, "bottom_grad", False, True),
            DictItemChangeCommand(overlay, "top_grad", False, True),
        ])
        cmd.execute()
        self.assertEqual(overlay, {"bottom_grad": True, "top_grad": True})
        cmd.undo()
        self.assertEqual(overlay, {"bottom_grad": False, "top_grad": False})


class TestAddLayerCommand(unittest.TestCase):
    def test_execute_inserts_at_index(self):
        layers = [_Dummy(name="a"), _Dummy(name="c")]
        new = _Dummy(name="b")
        cmd = AddLayerCommand(layers, new, 1)
        cmd.execute()
        self.assertEqual([l.name for l in layers], ["a", "b", "c"])

    def test_undo_removes_it(self):
        layers = [_Dummy(name="a"), _Dummy(name="c")]
        new = _Dummy(name="b")
        cmd = AddLayerCommand(layers, new, 1)
        cmd.execute()
        cmd.undo()
        self.assertEqual([l.name for l in layers], ["a", "c"])


class TestDeleteLayerCommand(unittest.TestCase):
    def test_execute_removes_layer(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        layers = [a, b, c]
        cmd = DeleteLayerCommand(layers, b)
        cmd.execute()
        self.assertEqual([l.name for l in layers], ["a", "c"])

    def test_undo_reinserts_at_original_index(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        layers = [a, b, c]
        cmd = DeleteLayerCommand(layers, b)
        cmd.execute()
        cmd.undo()
        self.assertEqual([l.name for l in layers], ["a", "b", "c"])


class TestReorderLayerCommand(unittest.TestCase):
    def test_execute_swaps_z(self):
        a, b = _Dummy(z=1), _Dummy(z=2)
        cmd = ReorderLayerCommand(a, 1, 2, b, 2, 1)
        cmd.execute()
        self.assertEqual((a.z, b.z), (2, 1))

    def test_undo_restores_original_z(self):
        a, b = _Dummy(z=1), _Dummy(z=2)
        cmd = ReorderLayerCommand(a, 1, 2, b, 2, 1)
        cmd.execute()
        cmd.undo()
        self.assertEqual((a.z, b.z), (1, 2))


class TestAddSlideCommand(unittest.TestCase):
    def test_execute_inserts_at_index(self):
        slides = [_Dummy(name="a"), _Dummy(name="c")]
        new = _Dummy(name="b")
        cmd = AddSlideCommand(slides, new, 1)
        cmd.execute()
        self.assertEqual([s.name for s in slides], ["a", "b", "c"])

    def test_undo_removes_it(self):
        slides = [_Dummy(name="a"), _Dummy(name="c")]
        new = _Dummy(name="b")
        cmd = AddSlideCommand(slides, new, 1)
        cmd.execute()
        cmd.undo()
        self.assertEqual([s.name for s in slides], ["a", "c"])


class TestDeleteSlideCommand(unittest.TestCase):
    def test_execute_removes_slide(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = DeleteSlideCommand(slides, b)
        cmd.execute()
        self.assertEqual([s.name for s in slides], ["a", "c"])

    def test_undo_reinserts_at_original_index(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = DeleteSlideCommand(slides, b)
        cmd.execute()
        cmd.undo()
        self.assertEqual([s.name for s in slides], ["a", "b", "c"])


class TestReorderSlideCommand(unittest.TestCase):
    def test_execute_swaps_positions(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = ReorderSlideCommand(slides, 0, 2)
        cmd.execute()
        self.assertEqual([s.name for s in slides], ["c", "b", "a"])

    def test_undo_swaps_back(self):
        a, b, c = _Dummy(name="a"), _Dummy(name="b"), _Dummy(name="c")
        slides = [a, b, c]
        cmd = ReorderSlideCommand(slides, 0, 2)
        cmd.execute()
        cmd.undo()
        self.assertEqual([s.name for s in slides], ["a", "b", "c"])


class TestCompositeCommand(unittest.TestCase):
    def test_execute_applies_all_commands(self):
        obj = _Dummy(x=0.0, y=0.0)
        cmd = CompositeCommand([
            PropertyChangeCommand(obj, "x", 0.0, 1.0),
            PropertyChangeCommand(obj, "y", 0.0, 2.0),
        ])
        cmd.execute()
        self.assertEqual((obj.x, obj.y), (1.0, 2.0))

    def test_undo_reverts_all_commands(self):
        obj = _Dummy(x=0.0, y=0.0)
        cmd = CompositeCommand([
            PropertyChangeCommand(obj, "x", 0.0, 1.0),
            PropertyChangeCommand(obj, "y", 0.0, 2.0),
        ])
        cmd.execute()
        cmd.undo()
        self.assertEqual((obj.x, obj.y), (0.0, 0.0))


class TestCommandStack(unittest.TestCase):
    def test_push_executes_and_enables_undo(self):
        obj = _Dummy(x=0.1)
        stack = CommandStack()
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.9))
        self.assertEqual(obj.x, 0.9)

    def test_undo_reverts_last_command(self):
        obj = _Dummy(x=0.1)
        stack = CommandStack()
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.9))
        stack.undo()
        self.assertEqual(obj.x, 0.1)

    def test_redo_reapplies_undone_command(self):
        obj = _Dummy(x=0.1)
        stack = CommandStack()
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.9))
        stack.undo()
        stack.redo()
        self.assertEqual(obj.x, 0.9)

    def test_undo_on_empty_stack_returns_false(self):
        stack = CommandStack()
        self.assertFalse(stack.undo())

    def test_redo_on_empty_stack_returns_false(self):
        stack = CommandStack()
        self.assertFalse(stack.redo())

    def test_new_push_clears_redo_stack(self):
        obj = _Dummy(x=0.1)
        stack = CommandStack()
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.5))
        stack.undo()
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.9))
        self.assertFalse(stack.redo())
        self.assertEqual(obj.x, 0.9)

    def test_multiple_undo_redo_sequence(self):
        obj = _Dummy(x=0.0)
        stack = CommandStack()
        stack.push(PropertyChangeCommand(obj, "x", 0.0, 1.0))
        stack.push(PropertyChangeCommand(obj, "x", 1.0, 2.0))
        stack.undo()
        stack.undo()
        self.assertEqual(obj.x, 0.0)
        stack.redo()
        self.assertEqual(obj.x, 1.0)

    def test_clear_empties_both_stacks(self):
        obj = _Dummy(x=0.1)
        stack = CommandStack()
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.9))
        stack.clear()
        self.assertFalse(stack.undo())

    def test_on_change_callback_fires_on_push_undo_redo(self):
        obj = _Dummy(x=0.1)
        calls = []
        stack = CommandStack(on_change=lambda: calls.append(1))
        stack.push(PropertyChangeCommand(obj, "x", 0.1, 0.9))
        stack.undo()
        stack.redo()
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
