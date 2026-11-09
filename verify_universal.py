"""Checks for the Universal 2 gate, runnable on Windows as well as macOS."""
import struct
import tempfile
import unittest
from pathlib import Path

from macos_universal import architectures, audit_bundle, require_universal


def thin(cpu):
    return struct.pack("<8I", 0xFEEDFACF, cpu, 0, 6, 0, 0, 0, 0)


def fat():
    return (struct.pack(">II", 0xCAFEBABE, 2)
            + struct.pack(">5I", 0x01000007, 0, 48, 32, 0)
            + struct.pack(">5I", 0x0100000C, 0, 80, 32, 0)
            + thin(0x01000007) + thin(0x0100000C))


class UniversalGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, data):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def bundle(self):
        self.write("Contents/MacOS/PT Clip Viewer", fat())
        self.write("Contents/Frameworks/_tkinter.so", fat())
        self.write("Contents/Frameworks/tkinterdnd2/tkdnd/osx-arm64/libtkdnd2.9.3.dylib", thin(0x0100000C))
        self.write("Contents/Frameworks/tkinterdnd2/tkdnd/osx-x64/libtkdnd2.9.4.dylib", thin(0x01000007))

    def test_fat_and_thin_headers(self):
        self.assertEqual(architectures(self.write("fat", fat())), {"x86_64", "arm64"})
        self.assertEqual(architectures(self.write("arm", thin(0x0100000C))), {"arm64"})
        self.assertEqual(architectures(self.write("script", b"print('hi')")), set())
        with self.assertRaises(RuntimeError):
            require_universal(self.root / "arm")

    def test_dual_dispatch_is_allowed(self):
        self.bundle()
        self.assertEqual(len(audit_bundle(self.root)["binaries"]), 4)

    def test_tcl9_dispatch_names_are_audited(self):
        self.write("Contents/MacOS/PT Clip Viewer", fat())
        self.write("Contents/Frameworks/_tkinter.so", fat())
        self.write("Contents/Frameworks/tkinterdnd2/tkdnd/osx-arm64-tcl9/libtcl9tkdnd2.10.3.dylib", thin(0x0100000C))
        self.write("Contents/Frameworks/tkinterdnd2/tkdnd/osx-x64-tcl9/libtcl9tkdnd2.10.3.dylib", thin(0x01000007))
        self.assertEqual(len(audit_bundle(self.root)["binaries"]), 4)

    def test_accidental_thin_core_is_rejected(self):
        self.bundle()
        self.write("Contents/Frameworks/libpython.dylib", thin(0x01000007))
        with self.assertRaisesRegex(RuntimeError, "Single-architecture core"):
            audit_bundle(self.root)

    def test_missing_dnd_arch_is_rejected(self):
        self.bundle()
        (self.root / "Contents/Frameworks/tkinterdnd2/tkdnd/osx-arm64/libtkdnd2.9.3.dylib").unlink()
        with self.assertRaisesRegex(RuntimeError, "Missing TkDnD"):
            audit_bundle(self.root)

    def test_upstream_dnd_payload_contains_both_runtimes(self):
        import tkinterdnd2
        base = Path(tkinterdnd2.__file__).parent / "tkdnd"
        for directory, arch in (("osx-arm64", "arm64"), ("osx-x64", "x86_64")):
            with self.subTest(directory=directory):
                libraries = list((base / directory).glob("*.dylib"))
                self.assertTrue(libraries)
                for library in libraries:
                    self.assertIn(arch, architectures(library))


if __name__ == "__main__":
    unittest.main(verbosity=2)
