"""Restore normal window bounds and recover safely after a display is removed."""
import sys
import re


def current_bounds(root):
    width, height = root.winfo_width(), root.winfo_height()
    x, y = root.winfo_x(), root.winfo_y()
    match = re.fullmatch(r"[0-9]+x[0-9]+([+-])(-?[0-9]+)([+-])(-?[0-9]+)", root.geometry())
    # Use WM coordinates where absolute: widget coordinates on some window
    # managers include the title bar, which otherwise causes drift on reopen.
    if match:
        if match[1] == "+":
            x = int(match[2])
        if match[3] == "+":
            y = int(match[4])
    return width, height, x, y


def workareas(root):
    if sys.platform == "darwin":
        try:
            import ctypes
            from ctypes.util import find_library

            class Point(ctypes.Structure):
                _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

            class Size(ctypes.Structure):
                _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]

            class Rect(ctypes.Structure):
                _fields_ = [("origin", Point), ("size", Size)]

            library = find_library("CoreGraphics")
            if library:
                graphics = ctypes.CDLL(library)
                display_id = ctypes.c_uint32
                graphics.CGGetActiveDisplayList.argtypes = [display_id, ctypes.POINTER(display_id), ctypes.POINTER(display_id)]
                graphics.CGGetActiveDisplayList.restype = ctypes.c_int32
                graphics.CGDisplayBounds.argtypes = [display_id]
                graphics.CGDisplayBounds.restype = Rect
                ids, count = (display_id * 32)(), display_id()
                if graphics.CGGetActiveDisplayList(32, ids, ctypes.byref(count)) == 0:
                    areas = []
                    for index in range(count.value):
                        rect = graphics.CGDisplayBounds(ids[index])
                        # CoreGraphics uses logical global coordinates, like Tk.
                        # Reserve a conservative margin for menu bars and Dock.
                        areas.append((round(rect.origin.x), round(rect.origin.y)+32,
                                      round(rect.size.width), max(200, round(rect.size.height)-96)))
                    if areas:
                        return areas
        except (OSError, AttributeError):
            pass
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MonitorInfo(ctypes.Structure):
                _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                            ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

            areas = []
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, ctypes.c_void_p,
                                              ctypes.c_void_p, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
            user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MonitorInfo)]
            user32.GetMonitorInfoW.restype = wintypes.BOOL

            @callback_type
            def collect(monitor, dc, rect, data):
                info = MonitorInfo()
                info.size = ctypes.sizeof(info)
                if user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    r = info.work
                    areas.append((bool(info.flags & 1), (r.left, r.top, r.right-r.left, r.bottom-r.top)))
                return True

            user32.EnumDisplayMonitors.argtypes = [ctypes.c_void_p, ctypes.c_void_p, callback_type, wintypes.LPARAM]
            user32.EnumDisplayMonitors.restype = wintypes.BOOL
            if user32.EnumDisplayMonitors(None, None, collect, 0) and areas:
                return [area for primary, area in sorted(areas, key=lambda item: not item[0])]
        except (OSError, AttributeError):
            pass
    # Keep clear of the macOS menu bar/Dock and common desktop panels.
    top, bottom = (32, 64) if sys.platform == "darwin" else (0, 48)
    return [(0, top, root.winfo_screenwidth(), max(200, root.winfo_screenheight()-top-bottom))]


def choose_bounds(saved, areas):
    """Return (width, height, absolute x, absolute y), with a visible title bar."""
    valid = (saved is not None and len(saved) == 4 and
             all(isinstance(n, int) and abs(n) < 1000000 for n in saved) and
             saved[0] > 0 and saved[1] > 0)
    width, height, x, y = saved if valid else (1400, 800, 0, 0)
    area = next((a for a in areas if valid and a[0] <= x+width//2 < a[0]+a[2]
                 and a[1] <= y+height//2 < a[1]+a[3]), None)
    restore = area is not None
    ax, ay, aw, ah = area or areas[0]
    max_width, max_height = max(160, aw-16), max(120, ah-48)
    width = min(max_width, max(min(960, max_width), width))
    height = min(max_height, max(min(600, max_height), height))
    if restore:
        x = min(max(x, ax), ax+aw-width)
        y = min(max(y, ay), ay+ah-height-32)
    else:
        x, y = ax+(aw-width)//2, ay+(ah-height-32)//2
    return width, height, x, y


def geometry_string(bounds):
    width, height, x, y = bounds
    # '+-100' means an absolute negative coordinate; '-100' anchors to the right.
    return f"{width}x{height}+{x}+{y}"
