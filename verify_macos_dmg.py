"""Mount and test the built DMG on a native macOS runner."""
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from macos_universal import audit_bundle


def main():
    if sys.platform != "darwin":
        raise SystemExit("This check must run on macOS.")
    dmg = Path(sys.argv[1]).resolve()
    arch = platform.machine()
    if arch not in ("arm64", "x86_64"):
        raise SystemExit(f"Unsupported native test architecture: {arch}")
    with tempfile.TemporaryDirectory(prefix="ptclip-dmg-check-") as tmp:
        mount = Path(tmp) / "volume"
        mount.mkdir()
        subprocess.run(["hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", str(mount), str(dmg)], check=True, timeout=120)
        try:
            app = mount / "PT Clip Viewer.app"
            audit_bundle(app)
            subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True, timeout=60)
            report = Path(tmp) / "smoke.txt"
            subprocess.run(["/usr/bin/arch", f"-{arch}", str(app / "Contents/MacOS/PT Clip Viewer"),
                            "--smoke-test", str(report)], check=True, timeout=60)
            if report.read_text(encoding="utf-8").strip() != "OK":
                raise RuntimeError("Application smoke check failed")
            if len(sys.argv) > 2:
                subprocess.run(["/usr/bin/arch", f"-{arch}", str(app / "Contents/MacOS/PT Clip Viewer"),
                                "--ui-preview", str(Path(sys.argv[2]).resolve())], check=True, timeout=90)
            print(f"PASS: same Universal 2 DMG runs natively on {arch}")
        finally:
            subprocess.run(["hdiutil", "detach", str(mount)], check=True, timeout=60)


if __name__ == "__main__":
    main()
