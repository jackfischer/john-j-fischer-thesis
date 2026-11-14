National War College thesis by Col. John J. Fischer, USAF, 1957
"An Ideological Offensive for the Free World"

Restored from original typeset scanned copy

- `book.pdf`: the current typeset edition
- `source/manuscript.md`: the working transcription (confirmed differences from the scan remain; see the fidelity audit)
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

## Fidelity audit

[Audit findings, scan evidence, and reproduction instructions](audit/REPORT.md).
The independent checks have confirmed twelve scan-to-Markdown differences.
The transcription is not certified verbatim. Audit commands deliberately report
`REVIEW_REQUIRED` while discrepancies and page review remain open.
