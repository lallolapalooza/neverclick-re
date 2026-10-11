#!/usr/bin/env bash
# Headless Ghidra analysis + full C decompilation dump for one PE/ELF binary.
# Usage: decompile-one.sh <binary> <outfile.c> [extra analyzeHeadless args...]
set -euo pipefail

BIN="$1"; OUT="$2"; shift 2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_DIR="$(dirname "$SCRIPT_DIR")/ghidra/projects"
mkdir -p "$PROJ_DIR"

PROJ_NAME="${GHIDRA_PROJ_NAME:-ghidra-proj}"
FILE_TAG="$(basename "$BIN")-$(echo -n "$BIN" | sha256sum | cut -c1-12)"

/opt/ghidra/support/analyzeHeadless "$PROJ_DIR" "$PROJ_NAME" \
  -import "$BIN" \
  -scriptPath "$SCRIPT_DIR" \
  -postScript DumpDecompilation.java "$OUT" \
  "$@" 2>&1 | tail -25

echo "output: $OUT"
