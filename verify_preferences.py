"""Startup preference, settings interaction and window restore regression checks."""
import configparser
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import pt_clip_viewer as viewer
from ui_widgets import ActionButton
from window_geometry import choose_bounds, current_bounds, geometry_string


def run_packaged_preference_checks(App):
    """Run against the real frozen entry point, with isolated user preferences."""
    import sys
    module = sys.modules[App.__module__]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'preferences.ini'
        path.write_text('[settings]\nopen_file_on_start=true\n', encoding='utf-8')
        with patch.object(module, '_get_config_path', return_value=path), \
                patch.object(module, 'legacy_config_path', return_value=path), \
                patch.object(module.filedialog, 'askopenfilename', return_value='') as picker:
            apps = []
            try:
                app = App()
                apps.append(app)
                ready = tk.BooleanVar(app, False)
                app.after(380, lambda: ready.set(True))
                app.wait_variable(ready)
                if picker.call_count != 1:
                    raise RuntimeError('Enabled startup picker did not open exactly once')
                app.geometry('960x600+20+60')
                app.update()
                before = app._last_window_bounds
                app.destroy()

                app = App(open_dialog=False)
                apps.append(app)
                app.update()
                after = app._last_window_bounds
                if before[:2] != after[:2] or abs(before[2]-after[2]) > 8 or abs(before[3]-after[3]) > 8:
                    raise RuntimeError('Frozen app did not restore normal window bounds')
                app._show_settings()
                dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
                next(w for w in descendants(dialog) if w.winfo_class() == 'Checkbutton').invoke()
                next(w for w in descendants(dialog) if isinstance(w, ActionButton) and w.cget('text') == '保存并关闭').invoke()
                app.destroy()

                picker.reset_mock()
                app = App()
                apps.append(app)
                ready = tk.BooleanVar(app, False)
                app.after(380, lambda: ready.set(True))
                app.wait_variable(ready)
                if picker.called or app._open_file_on_start.get():
                    raise RuntimeError('Disabled startup preference did not survive reopening')
            finally:
                for app in apps:
                    app.destroy()
    print('PASS: packaged startup switch, settings persistence and window restore.')


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


class GeometryTests(unittest.TestCase):
    def test_titlebar_offsets_do_not_accumulate(self):
        from types import SimpleNamespace
        root = SimpleNamespace(winfo_width=lambda: 960, winfo_height=lambda: 600,
                               winfo_x=lambda: 28, winfo_y=lambda: 90,
                               geometry=lambda: '960x600+20+60')
        self.assertEqual(current_bounds(root), (960, 600, 20, 60))

    def test_first_start_is_centered(self):
        self.assertEqual(choose_bounds(None, [(0, 0, 1920, 1080)]), (1400, 800, 260, 124))

    def test_saved_bounds_are_restored(self):
        saved = (1100, 650, 320, 210)
        self.assertEqual(choose_bounds(saved, [(0, 0, 1920, 1080)]), saved)

    def test_removed_display_recenters_and_oversized_window_fits(self):
        self.assertEqual(choose_bounds((1200, 700, 4000, 500), [(0, 0, 1920, 1080)]),
                         (1200, 700, 360, 174))
        width, height, x, y = choose_bounds((4000, 3000, 0, 0), [(0, 32, 1024, 672)])
        self.assertLessEqual(x+width, 1024)
        self.assertGreaterEqual(y, 32)
        self.assertLessEqual(y+height+32, 704)

    def test_negative_monitor_coordinates_are_absolute(self):
        saved = (1100, 650, -1600, 130)
        self.assertEqual(choose_bounds(saved, [(0, 0, 1920, 1080), (-1920, 0, 1920, 1080)]), saved)
        self.assertEqual(geometry_string(saved), "1100x650+-1600+130")

    def test_invalid_preferences_recenter(self):
        for saved in ((-1, 650, 20, 20), (1100, 650, 'bad', 20), (100,)):
            self.assertEqual(choose_bounds(saved, [(0, 0, 1920, 1080)]), (1400, 800, 260, 124))


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'preferences.ini'
        for name, value in (('_get_config_path', self.path), ('legacy_config_path', self.path)):
            p = patch.object(viewer, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(viewer.filedialog, 'askopenfilename', return_value='')
        self.file_dialog = p.start()
        self.addCleanup(p.stop)

    def app(self, **kwargs):
        app = viewer.App(**kwargs)
        self.addCleanup(app.destroy)
        app.update()
        return app

    def wait_startup(self, app):
        done = tk.BooleanVar(app, False)
        app.after(380, lambda: done.set(True))
        app.wait_variable(done)

    def test_startup_switch_on_off_and_explicit_test_override(self):
        for setting, override, expected in ((False, None, 0), (True, None, 1), (True, False, 0)):
            with self.subTest(setting=setting, override=override):
                self.path.write_text(f'[settings]\nopen_file_on_start = {setting}\n', encoding='utf-8')
                self.file_dialog.reset_mock()
                app = self.app(open_dialog=override)
                self.wait_startup(app)
                self.assertEqual(self.file_dialog.call_count, expected)
                app.destroy()

    def test_settings_save_and_cancel(self):
        app = self.app(open_dialog=False)
        self.assertFalse(app._open_file_on_start.get())
        app._show_settings()
        dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        checkbox = next(w for w in descendants(dialog) if w.winfo_class() == 'Checkbutton')
        checkbox.invoke()
        next(w for w in descendants(dialog) if isinstance(w, ActionButton) and w.cget('text') == '保存并关闭').invoke()
        self.assertTrue(viewer.load_config().getboolean('settings', 'open_file_on_start'))
        app._show_settings()
        dialog = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        next(w for w in descendants(dialog) if w.winfo_class() == 'Checkbutton').invoke()
        next(w for w in descendants(dialog) if isinstance(w, ActionButton) and w.cget('text') == '取消').invoke()
        self.assertTrue(app._open_file_on_start.get())
        self.assertTrue(viewer.load_config().getboolean('settings', 'open_file_on_start'))
        app.destroy()
        reopened = self.app(open_dialog=False)
        self.assertTrue(reopened._open_file_on_start.get())

    def test_normal_close_restores_geometry_on_reopen(self):
        app = self.app(open_dialog=False)
        app.geometry('960x600+20+60')
        app.update()
        before = app._last_window_bounds
        app.destroy()
        self.assertTrue(viewer.load_config().has_section('window'))
        reopened = self.app(open_dialog=False)
        after = reopened._last_window_bounds
        self.assertEqual(before[:2], after[:2])
        self.assertLessEqual(abs(before[2]-after[2]), 8)
        self.assertLessEqual(abs(before[3]-after[3]), 8)

    def test_invalid_window_config_and_preview_do_not_overwrite_user_bounds(self):
        self.path.write_text('[settings]\n[window]\nwidth=bad\nheight=600\nx=0\ny=0\n', encoding='utf-8')
        original = self.path.read_bytes()
        app = self.app(open_dialog=False, remember_window=False)
        app.destroy()
        self.assertEqual(self.path.read_bytes(), original)

    def test_loaded_file_suppresses_delayed_picker(self):
        self.path.write_text('[settings]\nopen_file_on_start=true\n', encoding='utf-8')
        app = self.app()
        app.tracks = [{'track_name': 'Already opened', 'clips': []}]
        self.wait_startup(app)
        self.file_dialog.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
