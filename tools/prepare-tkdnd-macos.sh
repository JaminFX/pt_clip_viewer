#!/bin/bash
# Build the missing Intel Tcl 9 runtime from the same maintained upstream fork
# used by tkinterdnd2. No downloaded binary or source is selected by a moving tag.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PT_PYTHON:-.venv-macos/bin/python}"
DEST="$($PYTHON -c 'import pathlib,tkinterdnd2; print(pathlib.Path(tkinterdnd2.__file__).parent / "tkdnd" / "osx-x64-tcl9")')"
if [[ -f "$DEST/pkgIndex.tcl" ]]; then exit 0; fi
if [[ "$(uname -m)" != x86_64 ]]; then
    echo 'The Intel Tcl 9 runtime must be built on an Intel Mac or supplied in vendor/tkdnd.' >&2
    exit 1
fi
brew install autoconf tcl-tk
TCLTK_PREFIX="$(brew --prefix tcl-tk)"
export PATH="$TCLTK_PREFIX/bin:$PATH"
export LDFLAGS="-L$TCLTK_PREFIX/lib"
export CPPFLAGS="-I$TCLTK_PREFIX/include"
export PKG_CONFIG_PATH="$TCLTK_PREFIX/lib/pkgconfig"
SOURCE="$(pwd)/build/tkdnd-tcl9-source"
if [[ ! -d "$SOURCE/.git" ]]; then
    git clone --no-checkout https://github.com/Squiblydoo/tkdnd.git "$SOURCE"
fi
git -C "$SOURCE" fetch --depth 1 origin f2b256ecf374595fa20005c479655e9fd72889f8
git -C "$SOURCE" checkout --detach f2b256ecf374595fa20005c479655e9fd72889f8
(
    cd "$SOURCE"
    autoreconf -fi
    tclsh tcl-conf-arm
    make -j2 install arch=x86_64
)
LIBRARY="$(find "$SOURCE/cmake/runtime" -name pkgIndex.tcl -print -quit)"
test -n "$LIBRARY"
mkdir -p "$DEST"
cp "$(dirname "$LIBRARY")/"*.tcl "$DEST/"
cp "$(dirname "$LIBRARY")/"*.dylib "$DEST/"
mkdir -p build/tkdnd-vendor/osx-x64-tcl9
cp "$DEST/"*.tcl "$DEST/"*.dylib build/tkdnd-vendor/osx-x64-tcl9/
cp "$SOURCE/license.terms" build/tkdnd-vendor/LICENSE.txt
printf '%s\n' f2b256ecf374595fa20005c479655e9fd72889f8 > build/tkdnd-vendor/source-commit.txt
