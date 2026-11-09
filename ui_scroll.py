"""Scoped scrolling for Tk 8 mouse wheels and Tk 9 two-finger gestures."""
import tkinter as tk

from pt_platform import wheel_units


class ScrollRegion:
    """Route descendants to their local scroller, without process-wide bindings.

    A nested listbox/text scrolls first; at its edge the outer canvas scrolls.
    Bind before native widget classes so one event is never applied twice.
    """

    def __init__(self, target):
        self.target = target
        self.tag = f"PTScroll:{target}"
        self.tk9 = int(target.tk.call("package", "provide", "Tk").split(".")[0]) >= 9
        target.bind_class(self.tag, "<MouseWheel>", self._wheel)
        if self.tk9:
            target.bind_class(self.tag, "<TouchpadScroll>", self._touchpad)
        if target.tk.call("tk", "windowingsystem") == "x11":
            target.bind_class(self.tag, "<Button-4>", lambda e: self._scroll(e, -1))
            target.bind_class(self.tag, "<Button-5>", lambda e: self._scroll(e, 1))
        target.bind("<Destroy>", self._destroy, add="+")
        self.attach(target)

    def attach(self, widget):
        tags = widget.bindtags()
        if self.tag not in tags:
            widget.bindtags((self.tag,) + tags)
        for child in widget.winfo_children():
            self.attach(child)

    def _wheel(self, event):
        # Shift-wheel retains native horizontal behavior.
        if event.state & 1:
            return None
        return self._scroll(event, wheel_units(event, tk9=self.tk9))

    def _touchpad(self, event):
        # %D packs signed X/Y deltas, not conventional MouseWheel units.
        dx, dy = self.target.tk.call("tk::PreciseScrollDeltas", event.delta)
        if not dy:
            return None
        if dx and self.target.winfo_class() in ("Treeview", "Text", "Listbox"):
            self.target.xview_scroll(-int(dx), "units")
        return self._scroll(event, -int(dy))

    def _scroll(self, event, units):
        if not units:
            return None
        widget = event.widget
        while widget is not None and widget != self.target:
            if widget.winfo_class() in ("Listbox", "Text", "Treeview"):
                first, last = widget.yview()
                if (units < 0 and first > 0) or (units > 0 and last < 1):
                    widget.yview_scroll(units, "units")
                    return "break"
            widget = widget.master
        first, last = self.target.yview()
        if (units < 0 and first > 0) or (units > 0 and last < 1):
            self.target.yview_scroll(units, "units")
        return "break"

    def _destroy(self, event):
        if event.widget == self.target:
            # Class tags are global within a Tcl interpreter; remove their scripts.
            for sequence in self.target.bind_class(self.tag):
                self.target.unbind_class(self.tag, sequence)
