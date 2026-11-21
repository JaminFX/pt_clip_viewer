"""Plug-in listing and group clipboard regressions, also run inside frozen UI."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import pt_clip_viewer as viewer
from edl_parser import parse_plugins, parse_export
from ui_widgets import ActionButton

NAMES = ["EQ3 7-Band", "Trim", "Dyn3 Compressor/Limiter", "PhoenixVerb", "Stratus",
         "FabFilter Pro-C 2", "FabFilter Pro-C 2", "FabFilter Pro-L", "FabFilter Pro-R",
         "FabFilter Pro-DS", "FabFilter Pro-Q 2", "FabFilter Pro-Q 2", "FabFilter Pro-Q 4",
         "FabFilter Pro-Q 4", "Fresh Air", "Oxford SuprEsser", "Insight 2", "soothe2"]
LISTING = ("P L U G - I N S  L I S T I N G\n"
           "MANUFACTURER\tPLUG-IN NAME\tVERSION\tFORMAT\tSTEMS\tNUMBER OF INSTANCES\n" +
           "\n".join(f"{'Example' if i == 0 else ''}\t{name}\t1.0\tAAX Native\tMono / Mono\t1 active"
                     for i, name in enumerate(NAMES)))
TRACKS = ("\n\nT R A C K  L I S T I N G\nTRACK NAME:\tTest\nPLUG-INS:\tIgnore (mono)\n"
          "1\t1\tClip\t00:00:01:00\t00:00:02:00\t00:00:01:00\tUnmuted\n")
TIME_A, TIME_B = "00:00:01:00-00:00:02:00", "00:00:03:00-00:00:04:00"


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def settings_dialog(app):
    app._show_settings()
    return next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))


def click(dialog, text):
    next(w for w in descendants(dialog) if isinstance(w, ActionButton) and w.cget("text") == text).invoke()


def run_plugin_checks(app):
    """Use real load/copy routes and isolate dialog notifications."""
    old_mode, old_name = app._unnamed_group_mode.get(), app._unnamed_group_name.get()
    with tempfile.TemporaryDirectory() as tmp, patch.object(viewer.messagebox, "showinfo") as notice:
        sample = Path(tmp) / "plugins.txt"
        try:
            app.clipboard_clear()
            app.clipboard_append("keep clipboard")
            app._copy_plugins()
            if not notice.called or app.clipboard_get() != "keep clipboard":
                raise RuntimeError("No-file notice must preserve clipboard")
            notice.reset_mock()
            sample.write_text(LISTING + TRACKS, encoding="utf-8")
            app._load_path(str(sample))
            app.copy_plugins_btn.invoke()
            if app.clipboard_get() != "工程使用插件：\n" + "\n".join(NAMES):
                raise RuntimeError("Plug-in clipboard names, order or duplicate rows changed")
            if notice.called or not app.tracks:
                raise RuntimeError("Valid plug-in export should load tracks without notice")
            sample.write_text(TRACKS, encoding="utf-8")
            app._load_path(str(sample))
            app._copy_plugins()
            if app.plugins or not notice.called or "勾选" not in notice.call_args.args[1]:
                raise RuntimeError("Missing plug-ins must clear old names and explain export option")
            sample.write_text(LISTING, encoding="utf-8")
            app._load_path(str(sample))
            app._copy_plugins()
            if app.tracks or app.copy_single_btn.cget("state") != "disabled" or app.preview.get("1.0", "end").strip():
                raise RuntimeError("Plug-in-only export retained stale track state")
            with patch.object(app, "load_file") as picker:
                app._open_startup_file()
                if picker.called:
                    raise RuntimeError("Loaded plug-in-only export must suppress delayed startup picker")
            for slot in app._slots:
                slot["enabled"].set(False)
            first, second = app._slots[:2]
            for slot, title, times in ((first, "命名分组", [TIME_A]), (second, "", [TIME_B, TIME_B])):
                slot["enabled"].set(True)
                slot["label"].set(title)
                slot["clips"][:] = times
            app._unnamed_group_mode.set("name")
            app._unnamed_group_name.set("未命名分组")
            app._edit_copy_all()
            if app.clipboard_get() != f"命名分组：\n{TIME_A}\n\n未命名分组：\n{TIME_B}":
                raise RuntimeError("Named fallback group copy or per-group dedup failed")
            app._unnamed_group_mode.set("blank")
            app._edit_copy_all()
            if app.clipboard_get() != f"命名分组：\n{TIME_A}\n\n{TIME_B}":
                raise RuntimeError("Blank group must keep an empty separating line")
            first["label"].set("")
            app._edit_copy_all()
            if app.clipboard_get() != f"{TIME_A}\n\n{TIME_B}":
                raise RuntimeError("Consecutive unnamed groups ran together")
            app._unnamed_group_mode.set("name")
            app._unnamed_group_name.set("自定名称")
            app._edit_copy_all()
            if app.clipboard_get().count("自定名称：") != 2:
                raise RuntimeError("Custom unnamed group label was ignored")
        finally:
            app._unnamed_group_mode.set(old_mode)
            app._unnamed_group_name.set(old_name)
            app.tracks, app.plugins, app.view_idx, app.selected_set = [], [], None, set()
            app._export_loaded = False
            app.tree.delete(*app.tree.get_children())
            app.copy_single_btn.config(state="disabled")
            app.copy_all_btn.config(state="disabled")
            app._update_copy_sel_btn()
            for index, slot in enumerate(app._slot_widgets):
                data = slot["data"]
                app._slot_restore(data, slot["listbox"], [])
                data["label"].set(app._DEFAULT_SLOT_NAMES[index][0])
                data["enabled"].set(index == 0)
                data["undo"].clear()
                data["redo"].clear()
                app._slot_refresh_ur_buttons(data)
                app._refresh_slot_action_btns(data)
    print("PASS: plug-in listing/copy/missing notice and named/blank group separation.")


class PluginParsingTests(unittest.TestCase):
    def test_listing_order_duplicates_and_boundary(self):
        self.assertEqual(parse_plugins(LISTING + TRACKS), NAMES)

    def test_no_listing_and_empty_listing(self):
        self.assertEqual(parse_plugins(TRACKS), [])
        self.assertEqual(parse_plugins(LISTING.split("Example")[0] + TRACKS), [])

    def test_fixed_width_export(self):
        text = "P L U G - I N S  L I S T I N G\n"
        text += f"{'MANUFACTURER':24}{'PLUG-IN NAME':30}{'VERSION':16}FORMAT\n"
        text += f"{'Avid':24}{'EQ3 7-Band':30}{'1.0':16}AAX Native\n"
        text += f"{'':24}{'Trim':30}{'1.0':16}AAX Native\n" + TRACKS
        self.assertEqual(parse_plugins(text), NAMES[:2])

    def test_supported_encodings_and_tracks(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.txt"
            for encoding in ("utf-8-sig", "utf-16", "gbk"):
                with self.subTest(encoding=encoding):
                    sample.write_bytes((LISTING + TRACKS).encode(encoding))
                    tracks, names = parse_export(sample)
                    self.assertEqual(names, NAMES)
                    self.assertEqual(tracks[0]["clips"][0]["start"], "00:00:01:00")


class PluginIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "preferences.ini"
        for target in ("_get_config_path", "legacy_config_path"):
            patcher = patch.object(viewer, target, return_value=self.path)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self):
        app = viewer.App(open_dialog=False, remember_window=False)
        self.addCleanup(app.destroy)
        app.update()
        return app

    def test_clipboard_and_missing_notices(self):
        run_plugin_checks(self.app())

    def test_settings_save_cancel_and_reopen(self):
        app = self.app()
        self.assertEqual(app._unnamed_group_mode.get(), "name")
        dialog = settings_dialog(app)
        radio = next(w for w in descendants(dialog) if w.winfo_class() == "Radiobutton" and w.cget("text") == "不加名称，用空行分隔")
        radio.invoke()
        entry = next(w for w in descendants(dialog) if w.winfo_class() == "Entry")
        entry.delete(0, "end")
        entry.insert(0, "待定 100%")
        click(dialog, "保存并关闭")
        app.destroy()
        app = self.app()
        self.assertEqual(app._unnamed_group_mode.get(), "blank")
        self.assertEqual(app._unnamed_group_name.get(), "待定 100%")
        dialog = settings_dialog(app)
        next(w for w in descendants(dialog) if w.winfo_class() == "Radiobutton" and w.cget("text") == "使用下方默认名称").invoke()
        click(dialog, "取消")
        self.assertEqual(app._unnamed_group_mode.get(), "blank")
        self.assertEqual(viewer.load_config()["settings"]["unnamed_group_mode"], "blank")

    def test_empty_custom_label_falls_back(self):
        app = self.app()
        dialog = settings_dialog(app)
        entry = next(w for w in descendants(dialog) if w.winfo_class() == "Entry")
        entry.delete(0, "end")
        click(dialog, "保存并关闭")
        self.assertEqual(app._unnamed_group_name.get(), "未命名分组")


if __name__ == "__main__":
    unittest.main(verbosity=2)
