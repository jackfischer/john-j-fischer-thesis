#!/bin/sh
# Rebuild everything: ./build.sh
set -e
cd "$(dirname "$0")"
mkdir -p build
python3 build.py
for i in 1 2 3; do lualatex -interaction=nonstopmode -halt-on-error book.tex >/dev/null; done
cp book.toc sample.toc
lualatex -interaction=nonstopmode -halt-on-error sample.tex >/dev/null
echo "book.pdf: $(pdfinfo book.pdf | awk '/Pages/{print $2}') pages; sample.pdf: $(pdfinfo sample.pdf | awk '/Pages/{print $2}') pages"
