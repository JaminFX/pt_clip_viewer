"""Regression checks for untrusted local exports and release hardening."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import edl_parser

ROOT = Path(__file__).resolve().parent


class ExportSecurityTests(unittest.TestCase):
    def test_malformed_whitespace_does_not_hang(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "malformed.txt"
            file.write_text("TRACK NAME: A\n1 1 " + " "*1_000_000 + "x\n", encoding="utf-8")
            command = "import edl_parser; print(edl_parser.parse_edl(" + repr(str(file)) + "))"
            result = subprocess.run([sys.executable, "-c", command], cwd=ROOT,
                                    capture_output=True, text=True, timeout=3, check=True)
            self.assertEqual(result.stdout.strip(), "[]")

    def test_byte_limit_is_enforced_in_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "oversize.txt"
            file.write_bytes(b"A"*33)
            with patch.object(edl_parser, "MAX_EDL_BYTES", 32):
                with self.assertRaisesRegex(ValueError, "20 MB"):
                    edl_parser.parse_edl(file)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX named-pipe check")
    def test_named_pipe_is_rejected_without_waiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "pipe"
            os.mkfifo(file)
            with self.assertRaises(ValueError):
                edl_parser.read_export(file)

    def test_valid_rows_deduplicate_and_preserve_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "export.txt"
            file.write_text("轨道名：中文 Reading\n"
                            "1 1 A  B  00:00:01:00 00:00:02:00 00:00:01:00\n"
                            "1 1 duplicate  00:00:01:00 00:00:02:00 00:00:01:00\n"
                            "2 2 channel2  00:00:01:00 00:00:02:00 00:00:01:00\n", encoding="utf-8")
            tracks = edl_parser.parse_edl(file)
            self.assertEqual(tracks[0]["track_name"], "中文 Reading")
            self.assertEqual(len(tracks[0]["clips"]), 1)
            self.assertEqual(tracks[0]["clips"][0]["name"], "A  B")

    def test_even_length_gbk_is_not_misread_as_bomless_utf16(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "gbk.txt"
            content = "TRACK NAME: 中文\n1 1 测试片段  00:00:01:00 00:00:02:00 00:00:01:00\n".encode("gbk")
            if len(content) % 2:
                content += b"\n"
            file.write_bytes(content)
            self.assertEqual(edl_parser.parse_edl(file)[0]["track_name"], "中文")

    def test_workflow_actions_are_immutable(self):
        import re
        workflow = (ROOT / ".github/workflows/macos-universal.yml").read_text(encoding="utf-8")
        refs = re.findall(r"uses:\s+([^\s#]+)", workflow)
        self.assertTrue(refs)
        self.assertTrue(all(re.fullmatch(r"actions/[\w-]+@[0-9a-f]{40}", ref) for ref in refs))
        self.assertNotIn("pull_request_target", workflow)

    def test_release_gates_do_not_use_optimizable_asserts(self):
        import ast
        for name in ("ui_validation.py", "pt_clip_viewer.py"):
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
