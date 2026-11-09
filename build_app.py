"""Build locally on Windows or macOS; macOS also produces a drag-install DMG."""
import shutil
import subprocess
import sys
from pathlib import Path
from macos_universal import architectures, audit_bundle, require_universal

ROOT = Path(__file__).resolve().parent
VERSION = "3.9.9"


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def main():
    if sys.platform not in ("win32", "darwin"):
        raise SystemExit("Run this script on Windows or macOS.")
    mac = sys.platform == "darwin"
    if mac:
        import _tkinter
        require_universal(sys.executable)
        require_universal(_tkinter.__file__)
        for tool in ("codesign", "hdiutil", "ditto"):
            if not shutil.which(tool):
                raise SystemExit(f"macOS build tool is missing: {tool}")
    import tkinter
    probe = tkinter.Tk()
    probe.withdraw()
    if sys.platform == "darwin" and probe.tk.call("tk", "windowingsystem") != "aqua":
        probe.destroy()
        raise SystemExit("Use a macOS Python with native Aqua Tk (python.org installer recommended).")
    probe.destroy()
    name = "PT Clip Viewer" if mac else "pt_clip_viewer"
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            "--windowed", "--onedir", "--name", name,
            "--distpath", ROOT / "dist", "--workpath", ROOT / "build",
            "--specpath", ROOT / "build",
            "--icon", ROOT / ("logo.icns" if mac else "logo.ico"),
            "--add-data", f"{ROOT / 'logo.ico'}{':' if mac else ';'}."]
    if mac:
        args += ["--osx-bundle-identifier", "com.jaminfx.ptclipviewer",
                 "--target-architecture", "universal2",
                 "--additional-hooks-dir", ROOT / "hooks-macos"]
    else:
        args += ["--collect-all", "tkinterdnd2"]
    args += ["--add-data", f"{ROOT / 'assets'}{':' if mac else ';'}assets"]
    args.append(ROOT / "pt_clip_viewer.py")
    run(*args)
    if not mac:
        print(f"Built: {ROOT / 'dist' / name}")
        return
    app = ROOT / "dist" / f"{name}.app"
    # Keep the two upstream TkDnD runtimes separate. Their versions differ;
    # combining these unrelated dylibs with lipo would not be a valid fix.
    import tkinterdnd2
    dnd_source = Path(tkinterdnd2.__file__).parent / "tkdnd"
    for directory, arch in (("osx-arm64", "arm64"), ("osx-x64", "x86_64")):
        source = dnd_source / directory
        libraries = list(source.glob("*.dylib"))
        if not libraries or not (source / "pkgIndex.tcl").is_file():
            raise SystemExit(f"Incomplete TkDnD runtime: {source}")
        for library in libraries:
            if arch not in architectures(library):
                raise SystemExit(f"Wrong TkDnD architecture: {library}")
        destination = app / "Contents" / "Frameworks" / "tkinterdnd2" / "tkdnd" / directory
        destination.mkdir(parents=True, exist_ok=True)
        for file in source.iterdir():
            if file.suffix in (".tcl", ".dylib"):
                shutil.copy2(file, destination / file.name)
        for library in destination.glob("*.dylib"):
            run("codesign", "--force", "--sign", "-", library)
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    audit_bundle(app, output / f"PT_Clip_Viewer_{VERSION}_Universal2_architectures.json")
    # Set the displayed version before re-signing the changed bundle.
    import plistlib
    plist_path = app / "Contents" / "Info.plist"
    with plist_path.open("rb") as f:
        plist = plistlib.load(f)
    plist.update(CFBundleShortVersionString=VERSION, CFBundleVersion=VERSION,
                 NSHighResolutionCapable=True)
    with plist_path.open("wb") as f:
        plistlib.dump(plist, f)
    run("codesign", "--force", "--deep", "--sign", "-", app)
    run("codesign", "--verify", "--deep", "--strict", app)
    # Check the bundled Tk and TkDnD libraries before packaging the app.
    smoke = ROOT / "build" / "smoke.txt"
    # Native architecture is tested here. Cloud workflow tests the SAME DMG
    # on both Intel and Apple Silicon; an Intel host cannot execute arm64.
    run(app / "Contents" / "MacOS" / name, "--smoke-test", smoke)
    if not smoke.exists() or smoke.read_text(encoding="utf-8").strip() != "OK":
        raise SystemExit("Bundled application smoke check did not complete.")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="ptclip-dmg-") as tmp:
        stage = Path(tmp)
        run("ditto", app, stage / app.name)
        (stage / "Applications").symlink_to("/Applications")
        dmg = output / f"PT_Clip_Viewer_{VERSION}_macOS_Universal2.dmg"
        # hdiutil refuses an existing destination unless explicitly overwritten.
        run("hdiutil", "create", "-ov", "-volname", "PT Clip Viewer",
            "-srcfolder", stage, "-format", "UDZO", dmg)
    print(f"Built: {dmg}")


if __name__ == "__main__":
    main()
