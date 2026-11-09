"""Small, testable platform helpers shared by the desktop builds."""
import os
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"
UI_FONT = "PingFang SC" if IS_MAC else "Microsoft YaHei UI"
CODE_FONT = "Menlo" if IS_MAC else "Consolas"
MODIFIER = "Command" if IS_MAC else "Control"
UNDO_HINT = "⌘Z / ⇧⌘Z" if IS_MAC else "Ctrl+Z / Ctrl+Y"


def config_path():
    if IS_MAC:
        base = Path.home() / "Library" / "Application Support" / "PT Clip Viewer"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PT Clip Viewer"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pt_clip_viewer"
    return base / "pt_clip_viewer.ini"


def legacy_config_path():
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    return base / "pt_clip_viewer.ini"


def wheel_units(event):
    """macOS Tk emits small deltas; Windows generally emits multiples of 120."""
    delta = event.delta
    if not delta:
        return 0
    if IS_MAC:
        return -int(delta) if abs(delta) >= 1 else (-1 if delta > 0 else 1)
    return -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
