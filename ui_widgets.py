"""Platform-independent dark action buttons with native-resolution Lucide strokes."""
import json
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path

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


def draw_icon(canvas, name, x, y, size, color, tag="icon"):
    scale = size / 24
    for shape in ICONS.get(name, []):
        coords = shape["points"]
        if shape["kind"] == "circle":
            cx, cy, radius = coords
            canvas.create_oval(x+(cx-radius)*scale, y+(cy-radius)*scale,
                               x+(cx+radius)*scale, y+(cy+radius)*scale,
                               outline=color, width=1.8*scale, tags=tag)
        else:
            points = [value for pair in coords for value in
                      (x+pair[0]*scale, y+pair[1]*scale)]
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=1.8*scale,
                                   capstyle="round", joinstyle="round", tags=tag)


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
        for key in list(kw):
            if key in self.OPTIONS:
                self._values[key] = kw.pop(key)
        if kw:
            super().configure(**kw)
        self._font.configure(**tkfont.Font(self, font=self._values["font"]).actual())
        self._measure()

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
        if pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
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
        self.delete("all")
        disabled = self._values["state"] == "disabled"
        fill = "#202c3e" if disabled else self._values["bg"]
        fg = "#91a4bc" if disabled else self._values["fg"]
        if not disabled:
            fill = tint(self, fill, -.13 if self._pressed else .10 if self._hovered else 0)
        w, h = max(self.winfo_width(), self.winfo_reqwidth()), max(self.winfo_height(), self.winfo_reqheight())
        r = 6
        pts = [1+r,1,w-r-1,1,w-1,1,w-1,1+r,w-1,h-r-1,w-1,h-1,w-r-1,h-1,
               r+1,h-1,1,h-1,1,h-r-1,1,r+1,1,1]
        focused = self.focus_get() == self and not disabled
        self.create_polygon(pts, smooth=True, splinesteps=16, fill=fill,
                            outline="#7dd3fc" if focused else tint(self, fill, .08), width=1)
        text_width = self._font.measure(self._label)
        total = text_width + (self._icon_size+(6 if self._label else 0) if self._icon else 0)
        x = (w-total)/2
        if self._icon:
            draw_icon(self, self._icon, x, (h-self._icon_size)/2, self._icon_size, fg)
            x += self._icon_size + (6 if self._label else 0)
        if self._label:
            self.create_text(x, h/2, text=self._label, font=self._font, fill=fg, anchor="w")


def apply_dark_inputs(root):
    for widget in ("Entry", "Listbox", "Text"):
        for option, value in (("borderWidth", 0), ("highlightThickness", 1),
                              ("highlightBackground", "#243044"), ("highlightColor", "#38bdf8")):
            root.option_add(f"*{widget}.{option}", value)
