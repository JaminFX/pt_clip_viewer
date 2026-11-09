"""Regression checks for platform paths, wheel events and Pro Tools encodings."""
import configparser
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pt_platform
import pt_clip_viewer as viewer


class PlatformRegressionTests(unittest.TestCase):
    def test_diagonal_strokes_have_partial_pixel_coverage(self):
        from aa_graphics import stroke_mask
        coverage = stroke_mask(18, [{"kind": "path", "points": [(4, 12), (10, 18), (20, 5)]}], samples=8)
        self.assertTrue(any(0 < value < 255 for value in coverage))
        self.assertIn(255, coverage)
        self.assertIn(0, coverage)

    def test_mac_trackpad_and_windows_wheel(self):
        for mac, delta, expected in [(True, 1, -1), (True, -2, 2),
                                     (False, 120, -1), (False, -240, 2),
                                     (False, 60, -1), (True, 0, 0)]:
            with self.subTest(mac=mac, delta=delta), patch.object(pt_platform, "IS_MAC", mac):
                self.assertEqual(pt_platform.wheel_units(SimpleNamespace(delta=delta)), expected)

    def test_mac_settings_outside_application(self):
        with patch.object(pt_platform, "IS_MAC", True), patch.object(Path, "home", return_value=Path("/Users/test")):
            self.assertEqual(str(pt_platform.config_path()).replace("\\", "/"),
                             "/Users/test/Library/Application Support/PT Clip Viewer/pt_clip_viewer.ini")

    def test_legacy_preferences_migrate_on_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "old.ini"
            new = Path(tmp) / "user" / "new.ini"
            old.write_text("[settings]\nsmart_merge_ask = false\n", encoding="utf-8")
            with patch.object(viewer, "_get_config_path", return_value=new), patch.object(viewer, "legacy_config_path", return_value=old):
                cfg = viewer.load_config()
                self.assertFalse(cfg.getboolean("settings", "smart_merge_ask"))
                viewer.save_config(cfg)
                self.assertTrue(new.is_file())
                self.assertFalse(viewer.load_config().getboolean("settings", "smart_merge_ask"))

    def test_chinese_edl_encodings(self):
        sample = "TRACK NAME: Reading 中文\n1 1 测试片段  00:00:01:00 00:00:02:00 00:00:01:00\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "测试.txt"
            for encoding in ("utf-8", "utf-8-sig", "utf-16", "gbk"):
                with self.subTest(encoding=encoding):
                    path.write_text(sample, encoding=encoding)
                    tracks = viewer.parse_edl(str(path))
                    self.assertEqual(tracks[0]["track_name"], "Reading 中文")
                    self.assertEqual(tracks[0]["clips"][0]["name"], "测试片段")


if __name__ == "__main__":
    unittest.main(verbosity=2)
