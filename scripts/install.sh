#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SOURCE_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)
TRIF_PREFIX=${TRIF_PREFIX:-"$HOME/.trif"}
TRIF_HOME="$TRIF_PREFIX/toolchain"
TRIF_BIN="$TRIF_PREFIX/bin"

mkdir -p "$TRIF_HOME" "$TRIF_BIN"
rm -rf "$TRIF_HOME"/*
cp -R "$SOURCE_DIR"/. "$TRIF_HOME"/

WRAPPER="$TRIF_BIN/trif"
cat > "$WRAPPER" <<'WRAP'
#!/usr/bin/env bash
PYTHON=${PYTHON:-python3}
exec "$PYTHON" -m trif_lang "$@"
WRAP
chmod +x "$WRAPPER"

echo "Trif installed to $TRIF_HOME"
echo "Add $TRIF_BIN to your PATH to use the trif CLI."
