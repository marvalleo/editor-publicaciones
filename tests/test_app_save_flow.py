"""Tests de flujo de guardado/cambios pendientes en dcpub.app sin abrir Tk."""

import unittest
from unittest.mock import patch

from dcpub.app import App


class TestConfirmDiscardChanges(unittest.TestCase):
    def test_no_dirty_continues_without_prompt(self):
        app = App.__new__(App)
        app._dirty = False

        with patch("dcpub.app.messagebox.askyesnocancel") as ask:
            self.assertTrue(App._confirm_discard_changes(app))
            ask.assert_not_called()

    def test_cancel_in_prompt_stops_action(self):
        app = App.__new__(App)
        app._dirty = True

        with patch("dcpub.app.messagebox.askyesnocancel", return_value=None):
            self.assertFalse(App._confirm_discard_changes(app))

    def test_declining_save_continues_action(self):
        app = App.__new__(App)
        app._dirty = True

        with patch("dcpub.app.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(App._confirm_discard_changes(app))

    def test_cancelled_save_stops_action(self):
        app = App.__new__(App)
        app._dirty = True
        app._save_project = lambda: False

        with patch("dcpub.app.messagebox.askyesnocancel", return_value=True):
            self.assertFalse(App._confirm_discard_changes(app))

    def test_successful_save_continues_action(self):
        app = App.__new__(App)
        app._dirty = True
        app._save_project = lambda: True

        with patch("dcpub.app.messagebox.askyesnocancel", return_value=True):
            self.assertTrue(App._confirm_discard_changes(app))


class TestDirectEdit(unittest.TestCase):
    def test_marks_dirty_and_schedules_render(self):
        app = App.__new__(App)
        calls = []
        app._set_dirty = lambda value: calls.append(("dirty", value))
        app._schedule_render = lambda: calls.append(("render", True))

        App._on_direct_edit(app)

        self.assertEqual(calls, [("dirty", True), ("render", True)])


if __name__ == "__main__":
    unittest.main()
