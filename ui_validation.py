"""Exercise visible button states and export main/settings/about screenshots."""
import importlib
import subprocess
import sys
import tempfile
from pathlib import Path

from ui_widgets import ActionButton


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def capture(widget, path):
    widget.update()
    widget.attributes("-topmost", True)
    widget.lift()
    widget.update()
    # Let the desktop compositor present the newly raised window.
    import tkinter as tk
    presented = tk.BooleanVar(widget, value=False)
    widget.after(400, lambda: presented.set(True))
    widget.wait_variable(presented)
    bbox = (widget.winfo_rootx(), widget.winfo_rooty(), widget.winfo_width(), widget.winfo_height())
    if sys.platform == "darwin":
        region = ",".join(str(value) for value in bbox)
        subprocess.run(["screencapture", "-x", "-R"+region, str(path)], check=True, timeout=15)
    elif sys.platform == "win32":
        grab = importlib.import_module("PIL.ImageGrab").grab
        x, y, w, h = bbox
        grab(bbox=(x, y, x+w, y+h)).save(path)
    if not path.is_file():
        raise RuntimeError(f"Screenshot was not produced: {path}")
    widget.attributes("-topmost", False)


def run_visual_checks(App, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = App(open_dialog=False)
    try:
        width = max(960, min(1400, app.winfo_screenwidth()-40))
        height = max(600, min(820, app.winfo_screenheight()-100))
        app.geometry(f"{width}x{height}+20+30")
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "Lucide_UI_Demo.txt"
            lines = []
            for name in ("Reading 朗诵", "Answer 回答", "Pickup 补录"):
                lines.append(f"TRACK NAME: {name}")
                for i in range(1, 25):
                    minute, second = divmod(i*3, 60)
                    lines.append(f"1 {i} {name} / Clip {i:02}  00:{minute:02}:{second:02}:00 00:{minute:02}:{second+1:02}:12 00:00:01:12")
            sample.write_text("\n".join(lines)+"\n", encoding="utf-8")
            app._load_path(str(sample))
            app._select_view(0)
            app.update()
            slot = app._slot_widgets[0]
            app._slot_add_current(slot["data"], slot["listbox"])
            app.update()
            buttons = [w for w in descendants(app) if isinstance(w, ActionButton)]
            assert len(buttons) >= 20
            assert all(w._text_label.winfo_class() == "Label" for w in buttons)
            assert all(w._check_photo.width() == 18 for w in descendants(app) if hasattr(w, "_check_photo"))
            assert not [w for w in descendants(app) if w.winfo_class() == "Button"]
            assert slot["undo_btn"].cget("state") == "normal"
            assert slot["redo_btn"].cget("state") == "disabled"
            count = len(slot["data"]["clips"])
            slot["undo_btn"].invoke()
            assert slot["data"]["clips"] == []
            slot["redo_btn"].invoke()
            assert len(slot["data"]["clips"]) == count
            triggered = []
            original = slot["redo_btn"].cget("command")
            slot["redo_btn"].config(command=lambda: triggered.append(1))
            slot["redo_btn"].invoke()
            assert not triggered, "Disabled button invoked a command"
            slot["redo_btn"]._text_label.event_generate("<ButtonPress-1>", x=2, y=2)
            slot["redo_btn"]._text_label.event_generate("<ButtonRelease-1>", x=2, y=2)
            assert not triggered, "Disabled label invoked a command"
            slot["redo_btn"].config(command=original)
            app.copy_single_btn._text_label.event_generate("<ButtonPress-1>", x=2, y=2)
            app.copy_single_btn._text_label.event_generate("<ButtonRelease-1>", x=2, y=2)
            assert "00:00:03:00-00:00:04:12" in app.clipboard_get()
            assert app.copy_single_btn._icon == "check"
            app.copy_single_btn.focus_set()
            capture(app, output / "main.png")
            app._show_settings()
            app.update()
            dialogs = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"]
            assert dialogs
            capture(dialogs[-1], output / "settings.png")
            dialogs[-1].destroy()
            print("PASS: rendered dark buttons; enabled/disabled commands, undo/redo, copy and dialogs.")
    finally:
        app.destroy()


if __name__ == "__main__":
    from pt_clip_viewer import App
    run_visual_checks(App, sys.argv[1])
