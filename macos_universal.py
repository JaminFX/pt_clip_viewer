"""Inspect Mach-O headers without executing them, including on Windows."""
import json
import struct
from pathlib import Path

UNIVERSAL = {"x86_64", "arm64"}
CPUS = {0x01000007: "x86_64", 0x0100000C: "arm64"}
THIN = {b"\xcf\xfa\xed\xfe": "<", b"\xfe\xed\xfa\xcf": ">",
        b"\xce\xfa\xed\xfe": "<", b"\xfe\xed\xfa\xce": ">"}
FAT = {b"\xca\xfe\xba\xbe": (">", 20), b"\xbe\xba\xfe\xca": ("<", 20),
       b"\xca\xfe\xba\xbf": (">", 32), b"\xbf\xba\xfe\xca": ("<", 32)}


def architectures(path):
    """Return Mach-O CPU names, or an empty set for a non-Mach-O file."""
    with Path(path).open("rb") as f:
        header = f.read(8)
        magic = header[:4]
        if magic in THIN:
            if len(header) != 8:
                raise ValueError(f"Truncated Mach-O file: {path}")
            cpu = struct.unpack(THIN[magic] + "I", header[4:])[0]
            return {CPUS.get(cpu, f"cpu:{cpu:#x}")}
        if magic not in FAT:
            return set()
        endian, entry_size = FAT[magic]
        count = struct.unpack(endian + "I", header[4:])[0]
        if not 1 <= count <= 32:
            raise ValueError(f"Invalid fat Mach-O architecture count: {path}")
        result = set()
        for _ in range(count):
            entry = f.read(entry_size)
            if len(entry) != entry_size:
                raise ValueError(f"Truncated fat Mach-O file: {path}")
            cpu = struct.unpack(endian + "I", entry[:4])[0]
            result.add(CPUS.get(cpu, f"cpu:{cpu:#x}"))
        return result


def require_universal(path):
    found = architectures(path)
    if not UNIVERSAL <= found:
        raise RuntimeError(f"Universal 2 required: {path}; found {sorted(found)}. "
                           "Use the python.org macOS universal2 Python installer.")


def audit_bundle(app, report_path=None):
    """Require fat core binaries and both separately dispatched TkDnD libraries."""
    app = Path(app)
    records = []
    dnd_found = set()
    for path in sorted(app.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        found = architectures(path)
        if not found:
            continue
        rel = path.relative_to(app).as_posix()
        expected = None
        for directory, arch in (("osx-arm64", "arm64"), ("osx-x64", "x86_64")):
            prefix = f"Contents/Frameworks/tkinterdnd2/tkdnd/{directory}/"
            if rel.startswith(prefix) and path.suffix == ".dylib" and path.name.startswith("libtkdnd"):
                expected = arch
                if arch not in found:
                    raise RuntimeError(f"Wrong TkDnD architecture: {rel}: {sorted(found)}")
                dnd_found.add(arch)
                break
        if expected is None and not UNIVERSAL <= found:
            raise RuntimeError(f"Single-architecture core binary: {rel}: {sorted(found)}")
        records.append({"file": rel, "architectures": sorted(found),
                        "loaded_for": expected or "both"})
    if dnd_found != UNIVERSAL:
        raise RuntimeError(f"Missing TkDnD runtime(s): {UNIVERSAL - dnd_found}")
    main = app / "Contents" / "MacOS" / "PT Clip Viewer"
    require_universal(main)
    if not any("_tkinter" in record["file"] for record in records):
        raise RuntimeError("Bundled _tkinter extension was not found")
    report = {"target": "universal2", "binaries": records,
              "note": "Core binaries contain both slices; TkDnD is dispatched by process architecture."}
    if report_path:
        Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
