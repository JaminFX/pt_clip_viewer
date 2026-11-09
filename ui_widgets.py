"""Platform-independent dark action buttons with native-resolution Lucide strokes."""
import json
from functools import lru_cache
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from pathlib import Path
from aa_graphics import rounded_png, icon_png, checkbox_png

ASSETS = Path(__file__).resolve().parent / "assets"
ICONS = json.loads((ASSETS / "lucide-paths.json").read_text(encoding="utf-8"))


def button_content(text):
    """Keep the existing dynamic labels while replacing their emoji with Lucide."""
    cleaned = text.lstrip("📂📋ℹ⚙✏✕＋+↩↪✅ ✨")
    for needle, icon in (("已复制", "check"), ("打开", "folder-open"),
                         ("设置", "settings-2"), ("关于", "info"),
                         ("关闭编辑", "panel-right-close"), ("编辑模式", "panel-right-open"),
                         ("撤销", "undo-2"), ("回撤", "redo-2"),
                         ("删除", "trash-2"), ("清空", "trash-2"),
                         ("保存", "save"), ("全不选", "square-dashed"),
                         ("全选", "list-checks"), ("添加", "plus"),
                         ("合并", "layers-2"), ("复制", "copy")):
        if needle in cleaned:
            return cleaned, icon
    if text.strip() == "✕":
        return "", "x"
    return cleaned, None


@lru_cache(maxsize=256)
def icon_bytes(name, size, color):
    return icon_png(size, ICONS.get(name, []), color)


def draw_checkbox(canvas, checked, color):
    canvas.delete("all")
    canvas._check_photo = tk.PhotoImage(master=canvas, data=checkbox_png(18, color, canvas.cget("bg"), bool(checked)), format="png")
    canvas.create_image(0, 0, image=canvas._check_photo, anchor="nw")


def tint(widget, color, amount):
    rgb = widget.winfo_rgb(color)
    return "#" + "".join(f"{max(0, min(255, round(c/257*(1-amount)+255*amount))):02x}" for c in rgb)


class ActionButton(tk.Canvas):
    """Button-compatible commands, state, cget, focus and activation on both OSes."""
    OPTIONS = {"text", "command", "font", "fg", "bg", "state", "padx", "pady",
               "image", "compound", "relief", "cursor", "activebackground",
               "activeforeground", "disabledforeground"}

    def __init__(self, master=None, **kw):
        self._values = {"text": "", "command": None, "font": ("TkDefaultFont", 10),
                        "fg": "#e8f4ff", "bg": "#1e2d47", "state": "normal",
                        "padx": 10, "pady": 4, "cursor": "hand2"}
        canvas_options = {key: value for key, value in kw.items() if key not in self.OPTIONS}
        self._values.update({key: value for key, value in kw.items() if key in self.OPTIONS})
        self._hovered = self._pressed = False
        super().__init__(master, background=master.cget("bg"), borderwidth=0,
                         highlightthickness=0, takefocus=1, **canvas_options)
        self._font = tkfont.Font(self, font=self._values["font"])
        self._text_label = tk.Label(self, font=self._font, borderwidth=0,
                                    highlightthickness=0, padx=0, pady=0, takefocus=0)
        self._photos = {}
        self.bind("<Configure>", self._paint)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<FocusIn>", self._paint)
        self.bind("<FocusOut>", self._paint)
        self.bind("<KeyPress-space>", self._key_press)
        self.bind("<KeyRelease-space>", self._key_release)
        self.bind("<Return>", self._key_release)
        for sequence, handler in (("<Enter>", self._enter), ("<Leave>", self._leave),
                                  ("<ButtonPress-1>", self._press), ("<ButtonRelease-1>", self._release)):
            self._text_label.bind(sequence, handler)
        self._measure()

    def _measure(self):
        self._label, self._icon = button_content(self._values["text"])
        self._icon_size = max(14, round(self._font.metrics("linespace") * .86))
        width = self._font.measure(self._label) + 2*int(self._values["padx"])
        if self._icon:
            width += self._icon_size + (6 if self._label else 0)
        height = max(22, self._font.metrics("linespace") + 2*int(self._values["pady"]) + 4)
        super().configure(width=max(24, width+4), height=height,
                          takefocus=0 if self._values["state"] == "disabled" else 1,
                          cursor="arrow" if self._values["state"] == "disabled" else "hand2")
        self._paint()

    def configure(self, cnf=None, **kw):
        if cnf is not None:
            if isinstance(cnf, str):
                return self.cget(cnf)
            kw = {**cnf, **kw}
        if not kw:
            return super().configure()
        changed = set()
        for key in list(kw):
            if key in self.OPTIONS:
                value = kw.pop(key)
                if self._values.get(key) != value:
                    self._values[key] = value
                    changed.add(key)
        if kw:
            super().configure(**kw)
        if "font" in changed:
            self._font.configure(**tkfont.Font(self, font=self._values["font"]).actual())
        if changed & {"text", "font", "padx", "pady"}:
            self._measure()
        elif changed & {"bg", "fg", "state", "cursor"}:
            if changed & {"state", "cursor"}:
                super().configure(takefocus=0 if self._values["state"] == "disabled" else 1,
                                  cursor="arrow" if self._values["state"] == "disabled" else self._values["cursor"])
            self._paint()

    config = configure

    def cget(self, key):
        if key in self._values:
            return self._values[key]
        return super().cget(key)

    __getitem__ = cget

    def invoke(self):
        if self._values["state"] != "disabled" and self._values.get("command"):
            return self._values["command"]()

    def _enter(self, event):
        self._hovered = True
        self._paint()

    def _leave(self, event):
        # Moving between the native text label and its canvas stays in the button.
        if (0 <= event.x_root-self.winfo_rootx() < self.winfo_width()
                and 0 <= event.y_root-self.winfo_rooty() < self.winfo_height()):
            return
        self._hovered = self._pressed = False
        self._paint()

    def _press(self, event):
        if self._values["state"] != "disabled":
            self.focus_set()
            self._pressed = True
            self._paint()

    def _release(self, event):
        pressed = self._pressed
        self._pressed = False
        self._paint()
        if pressed and 0 <= event.x_root-self.winfo_rootx() < self.winfo_width() and 0 <= event.y_root-self.winfo_rooty() < self.winfo_height():
            self.invoke()

    def _key_press(self, event):
        if self._values["state"] != "disabled":
            self._pressed = True
            self._paint()
        return "break"

    def _key_release(self, event):
        self._pressed = False
        self._paint()
        self.invoke()
        return "break"

    def _paint(self, event=None):
        if not hasattr(self, "_label"):
            return
        disabled = self._values["state"] == "disabled"
        fill = "#202c3e" if disabled else self._values["bg"]
        fg = "#91a4bc" if disabled else self._values["fg"]
        if not disabled:
            fill = tint(self, fill, -.13 if self._pressed else .10 if self._hovered else 0)
        w = self.winfo_width() if self.winfo_width() > 1 else self.winfo_reqwidth()
        h = self.winfo_height() if self.winfo_height() > 1 else self.winfo_reqheight()
        parent = self.master.cget("bg")
        focused = self.focus_get() == self and not disabled
        border = "#7dd3fc" if focused else tint(self, fill, .12)
        paint_key = (w, h, fill, fg, border, parent, self._label, self._icon, self._icon_size, str(self._font.actual()))
        if paint_key == getattr(self, "_paint_key", None):
            return
        self._paint_key = paint_key
        self.delete("all")
        super().configure(bg=parent)
        background_key = ("background", w, h, fill, border, parent)
        if background_key not in self._photos:
            self._photos[background_key] = tk.PhotoImage(master=self,
                data=rounded_png(w, h, fill, border, parent), format="png")
        self.create_image(0, 0, image=self._photos[background_key], anchor="nw")
        text_width = self._font.measure(self._label)
        total = text_width + (self._icon_size+(6 if self._label else 0) if self._icon else 0)
        x = round((w-total)/2)
        if self._icon:
            icon_key = ("icon", self._icon, self._icon_size, fg)
            if icon_key not in self._photos:
                self._photos[icon_key] = tk.PhotoImage(master=self,
                    data=icon_bytes(self._icon, self._icon_size, fg), format="png")
            self.create_image(x, round((h-self._icon_size)/2), image=self._photos[icon_key], anchor="nw")
            x += self._icon_size + (6 if self._label else 0)
        if self._label:
            self._text_label.configure(text=self._label, font=self._font, fg=fg, bg=fill)
            self._text_label.place(x=round(x), y=round(h/2), anchor="w")
        else:
            self._text_label.place_forget()
        # Resize/hovers should not retain every old native-resolution bitmap.
        protected = {background_key}
        if self._icon:
            protected.add(icon_key)
        while len(self._photos) > 24:
            obsolete = next(key for key in self._photos if key not in protected)
            del self._photos[obsolete]


class VisibleScrollbar(ttk.Scrollbar):
    def set(self, first, last):
        self.state(["disabled"] if float(last)-float(first) >= .999999 else ["!disabled"])
        return super().set(first, last)


def apply_dark_inputs(root):
    for widget in ("Entry", "Listbox", "Text"):
        for option, value in (("borderWidth", 0), ("highlightThickness", 1),
                              ("highlightBackground", "#243044"), ("highlightColor", "#38bdf8")):
            root.option_add(f"*{widget}.{option}", value)
