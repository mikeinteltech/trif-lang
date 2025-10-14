#!/usr/bin/env bash
set -euo pipefail

CXX=${CXX:-g++}
CXXFLAGS=("-std=c++20" "-O3" "-Wall" "-Wextra" "-Werror" "-DNDEBUG")
SRC_DIR="$(cd "$(dirname "$0")" && pwd)/src"
BUILD_DIR="${BUILD_DIR:-$SRC_DIR/../build}"
mkdir -p "$BUILD_DIR"

sources=(
  "$SRC_DIR/lexer.cpp"
  "$SRC_DIR/parser.cpp"
  "$SRC_DIR/codegen.cpp"
  "$SRC_DIR/compiler.cpp"
  "$SRC_DIR/main.cpp"
)

includes=("-I$SRC_DIR/../include")

output="$BUILD_DIR/trifc"

echo "[trif-build] Compiling ${#sources[@]} translation units..."
"$CXX" "${CXXFLAGS[@]}" "${includes[@]}" "${sources[@]}" -o "$output"
echo "[trif-build] Output -> $output"
