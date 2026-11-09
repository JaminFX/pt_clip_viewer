"""TkDnD's two macOS runtimes are staged and audited after COLLECT/BUNDLE.

The default hook selects just the build host's architecture. Passing the thin
TkDnD dylibs through PyInstaller's universal2 binary processing is also wrong:
they are intentionally loaded from distinct directories by TkinterDnD._require.
The Python package is still included through the application's normal import.
"""
datas = []
binaries = []
