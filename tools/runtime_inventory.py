"""Record the actual build/runtime versions without machine-specific paths."""
import importlib.metadata
import json
import platform
import ssl
import sys
import tkinter
import pyexpat
import zlib
from pathlib import Path

root = tkinter.Tk()
root.withdraw()
data = {"python": platform.python_version(), "architecture": platform.machine(),
        "platform": sys.platform, "openssl": ssl.OPENSSL_VERSION,
        "expat": pyexpat.EXPAT_VERSION, "zlib_compatibility": zlib.ZLIB_RUNTIME_VERSION,
        "tcl": root.tk.call("info", "patchlevel"), "tk": root.tk.call("package", "provide", "Tk"),
        "packages": {}}
root.destroy()
for name in ("pyinstaller", "tkinterdnd2", "Pillow", "altgraph", "packaging",
             "pyinstaller-hooks-contrib", "setuptools", "macholib", "pefile", "pywin32-ctypes"):
    try:
        data["packages"][name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        continue
path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps(data))
