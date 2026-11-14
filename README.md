National War College thesis by Col. John J. Fischer, USAF, 1957
"An Ideological Offensive for the Free World"

Restored from original typeset scanned copy

- `book.pdf`: the current typeset edition
- `book-lulu.pdf`: the hardcover interior upload, with Lulu bleed dimensions
- [Hardcover printing, paper recommendations, and preflight](PRINTING.md)
- `source/manuscript.md`: the working transcription, with documented minor editorial repairs (see the fidelity audit)
- `./build.sh`: rebuild with pandoc + LuaLaTeX (memoir, EB Garamond, microtype)

## Build on macOS

Install Homebrew, then:

```sh
brew install texlive pandoc poppler
./build.sh
```

Python 3 must also be on `PATH` (Homebrew's TeX Live installation includes it).
TeX Live supplies LuaLaTeX, EB Garamond, and the required LaTeX packages;
Poppler supplies `pdfinfo`. The build generates `book.pdf` and `sample.pdf`.

For the additional Lulu upload PDF, install `requirements-audit.txt` in a virtual
environment and run `PY="$PWD/.venv/bin/python" ./build.sh --lulu`.
See [PRINTING.md](PRINTING.md) for the full command and proof workflow.

## Fidelity audit

[Audit findings, scan evidence, and reproduction instructions](audit/REPORT.md).
The [editorial decisions](audit/EDITORIAL-DECISIONS.md) accept eleven existing
spelling/grammar repairs or spelling normalizations and one French accent
restoration for this printing. The edition is not a verbatim facsimile.
Audit commands deliberately report `REVIEW_REQUIRED` while the remaining
discrepancies and page review remain open.
