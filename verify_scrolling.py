"""Exercise actual Tk event routing; shared by Windows and native Mac release checks."""
import math
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

import pt_clip_viewer as viewer
from aa_graphics import rounded_pixels, rgb


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def send_scroll(app, widget, precise=False, down=True):
    # Tk 9 packs two signed 16-bit deltas into %D. Pure vertical = low word.
    sequence = "<TouchpadScroll>" if precise else "<MouseWheel>"
    delta = ((-1 if down else 1) & 0xffff) if precise else (-120 if down else 120)
    widget.event_generate(sequence, delta=delta)
    app.update()


def run_scroll_checks(app):
    """Also run inside the packaged app on both native Mac CI architectures."""
    app.update()
    precise_available = int(app.tk.call("package", "provide", "Tk").split(".")[0]) >= 9
    # Keep the fixture scrollable even on a tall desktop / native Mac runner.
    temporary_slots = []
    for _ in range(2):
        app._add_slot(default_name="滚动验证", scroll_to="top")
        temporary_slots.append(app._slot_widgets[-1])
    app.update()
    for precise in ([False, True] if precise_available else [False]):
        # Native treeview: do not discard 4 of every 5 touchpad events.
        for item in app.tree.get_children():
            app.tree.delete(item)
        for i in range(120):
            app.tree.insert("", "end", values=(i, f"片段 {i}", "00:00:01:00", "00:00:02:00", "00:00:01:00"))
        app.update()
        app.tree.yview_moveto(0)
        send_scroll(app, app.tree, precise)
        require(app.tree.yview()[0] > 0, "Clip table did not scroll")
        send_scroll(app, app.tree, precise, down=False)
        require(app.tree.yview()[0] == 0, "Clip table did not scroll upwards")

        # About labels, readonly command entry, button label and scrollbar.
        viewer.show_about(app)
        app.update()
        win = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel))
        try:
            canvas = win._scroll_region.target
            targets = [w for w in descendants(canvas) if w.winfo_class() in ("Label", "Entry")]
            targets.append(next(w for w in win.winfo_children() if w.winfo_class() == "TScrollbar"))
            require(bool(targets), "About page has no test targets")
            for target in targets:
                if not target.winfo_ismapped():
                    continue
                canvas.yview_moveto(0)
                app.update()
                send_scroll(app, target, precise)
                require(canvas.yview()[0] > 0, f"About page did not scroll over {target}")
            require(app._slot_canvas.yview()[0] == 0, "About scroll moved the main drawer")
        finally:
            tag = win._scroll_region.tag
            win.destroy()
            app.update()
            require(not app.bind_class(tag), "Destroyed about page leaked scroll bindings")

        # A listbox consumes a gesture once, then yields to the drawer at its edge.
        slot = app._slot_widgets[0]
        lb = slot["listbox"]
        lb.delete(0, "end")
        for i in range(100):
            lb.insert("end", f"片段 {i}")
        app.update()
        app._slot_canvas.yview_moveto(0)
        lb.yview_moveto(0)
        send_scroll(app, lb, precise)
        require(abs(lb.yview()[0] - .01) < .001, "Nested listbox scrolled twice or not at all")
        require(app._slot_canvas.yview()[0] == 0, "Listbox also scrolled the drawer")
        lb.yview_moveto(1)
        send_scroll(app, lb, precise)
        require(app._slot_canvas.yview()[0] > 0, "Listbox boundary did not yield to drawer")
        app._slot_canvas.yview_moveto(0)
        lb.delete(0, "end")

    # Dynamic track descendants must be attached after rebuilding the list.
    app.tracks = [{"track_name": f"轨道 {i}", "clips": []} for i in range(70)]
    app.selected_set = set(range(70))
    app._build_track_list()
    app.update()
    label = app.track_row_widgets[0][-2]
    for precise in ([False, True] if precise_available else [False]):
        app.track_canvas.yview_moveto(0)
        send_scroll(app, label, precise)
        require(app.track_canvas.yview()[0] > 0, "Track label did not scroll")
    for slot in temporary_slots:
        app._remove_slot(slot["frame"], slot["data"])
    app._slot_canvas.yview_moveto(0)
    print("PASS: mouse wheel / Tk9 touchpad; about descendants; nested listbox; dynamic tracks.")


class ScrollRegressionTests(unittest.TestCase):
    def test_app_scroll_and_idle_startup(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(viewer, "_get_config_path", return_value=Path(tmp) / "new.ini"), \
                patch.object(viewer, "legacy_config_path", return_value=Path(tmp) / "old.ini"), \
                patch.object(viewer.filedialog, "askopenfilename", return_value="") as dialog:
            app = viewer.App()
            errors = []
            app.report_callback_exception = lambda *args: errors.append(args)
            try:
                app.geometry("1280x650+20+20")
                ready = tk.BooleanVar(app, False)
                app.after(180, lambda: ready.set(True))
                app.wait_variable(ready)
                dialog.assert_not_called()
                run_scroll_checks(app)
                self.assertFalse(errors, errors)
            finally:
                app.destroy()

    def test_button_repeated_updates_do_not_redraw(self):
        from ui_widgets import ActionButton
        root = tk.Tk()
        root.configure(bg="#101827")
        try:
            button = ActionButton(root, text="打开文件", bg="#1e2d47")
            button.pack()
            root.update()
            before = button.find_all()
            for _ in range(20):
                button.config(text="打开文件", command=lambda: None)
                button._paint()
            self.assertEqual(before, button.find_all())
            button.config(state="disabled")
            self.assertNotEqual(before, button.find_all())
        finally:
            root.destroy()

    def test_faster_background_keeps_exact_pixels(self):
        def reference(w, h, fill, border, parent, radius=5, inset=.5):
            fill, border, parent = rgb(fill), rgb(border), rgb(parent)
            hw, hh = w/2-inset, h/2-inset
            radius = min(radius, hw, hh)
            output = bytearray()
            for y in range(h):
                for x in range(w):
                    qx = abs(x+.5-w/2) - (hw-radius)
                    qy = abs(y+.5-h/2) - (hh-radius)
                    d = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius
                    outer, inner = max(0, min(1, .5-d)), max(0, min(1, -.5-d))
                    output.extend([round(parent[i]*(1-outer)+border[i]*(outer-inner)+fill[i]*inner) for i in range(3)] + [255])
            return output
        for w, h in ((1, 1), (5, 8), (18, 18), (100, 32), (121, 33)):
            with self.subTest(width=w, height=h):
                args = (w, h, "#12abcd", "#244056", "#0d1523")
                self.assertEqual(reference(*args), rounded_pixels(*args))


if __name__ == "__main__":
    unittest.main(verbosity=2)
