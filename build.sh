#!/bin/sh
# Rebuild everything: ./build.sh [--lulu]
set -e
cd "$(dirname "$0")"
case "${1:-}" in ''|--lulu) ;; *) echo "Usage: $0 [--lulu]" >&2; exit 2 ;; esac
PY=${PY:-python3}
mkdir -p build
$PY build.py
for i in 1 2 3; do lualatex -interaction=nonstopmode -halt-on-error book.tex >/dev/null; done
cp book.toc sample.toc
lualatex -interaction=nonstopmode -halt-on-error sample.tex >/dev/null
echo "book.pdf: $(pdfinfo book.pdf | awk '/Pages/{print $2}') pages; sample.pdf: $(pdfinfo sample.pdf | awk '/Pages/{print $2}') pages"
if [ "${1:-}" = --lulu ]; then "$PY" scripts/prepare_lulu.py; fi
