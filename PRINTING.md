# Lulu hardcover printing

Specifications checked against Lulu's official documentation on 14 November 2026.

## Which file to use

- **`book-lulu.pdf`**: interior upload for a **6 × 9 inch hardcover**. Its physical PDF pages are 6.25 × 9.25 inches, including 0.125 inch of white bleed on every side. TrimBox marks the finished 6 × 9 page. Upload single pages as supplied, including intentional blanks; do not impose spreads or add crop marks.
- **`book.pdf`**: the 6 × 9 reading/review edition, with clickable contents, bookmarks, and page labels. Same interior typography and pagination.
- The current interior has **150 pages**. The first PDF page is a right-hand page. Blank versos are intentional.

The upload export preserves vector type and rules, embedded font programs, and original image pixels. It does not rasterize pages, invent image detail, or convert colors. Its added bleed is plain white because this interior has no artwork extending to the trim.

## Typography and physical margins

The edition retains EB Garamond at 11pt with oldstyle figures, restrained small caps, italic chapter titles, optical margin protrusion, and subtle font expansion. Memoir handles the two-sided layout, chapter openings, hanging footnotes, and contents. The 0.90-inch nominal inner margin includes a 0.10-inch binding allowance; the original text-column width is preserved. Running heads are inside the half-inch trim safety area.

Ragged page bottoms avoid stretching paragraph and heading spaces to fill a page; footnotes stay at the foot. Bibliography citations use hanging indents and a ragged right edge, while the author's longer annotations remain justified. The transcription note and complete contents each fit one page. The rebuilt log has no overfull boxes, missing glyphs, font substitutions, or unresolved references. Two existing underfull warnings occur in justified block quotations and have been visually reviewed.

## Rebuild and preflight

```sh
brew install texlive pandoc poppler
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-audit.txt
PY="$PWD/.venv/bin/python" ./build.sh --lulu
```

The ordinary `./build.sh` still builds the reading edition without the Python audit dependencies. `--lulu` also runs `scripts/prepare_lulu.py` and writes `build/print/preflight.json`. The checked-in [preflight snapshot](audit/print-preflight.json) identifies the exact release PDFs by SHA-256.

The preflight checks every page's boxes, unencrypted status, embedded fonts, image resolution, and content margins, including running heads and folios. Actual image resolution is about 315 ppi. All content is at least 0.50 inch from trim and 0.70 inch from the inner edge. It rejects live transparency, soft masks, and non-normal blending. Upload pages contain no links or other interactive annotations.

Every exported page is compared with the reading PDF at 144 dpi. Text, font identity, size, color, and image pixels are preserved, and translated glyph positions must agree within 0.001pt. The report distinguishes exact raster matches from a few tiny glyph-edge antialiasing differences caused by floating-point translation; these are not text changes. The [typography regression snapshot](audit/typography-wording.json) also records that all 143 manuscript streams retain the preceding edition's wording, case, emphasis, word boundaries, and note attachments after accounting for discretionary line-end hyphens.

This is a print-production check. The separate [transcription audit](audit/REPORT.md) retains its own scope and open findings.

To repeat the typography regression check against the preceding accepted PDF:

```sh
git show c40538d:book.pdf > /tmp/john-before-typography.pdf
.venv/bin/python scripts/audit_typography.py --baseline /tmp/john-before-typography.pdf
```

## Paper, cover, and proof

For this largely textual book, my recommendation is **black-and-white printing on 60# cream uncoated paper**. For the binding, a linen hardcover with a dust jacket would suit the restrained interior; casewrap is also compatible. Confirm availability for the chosen format and printing region in [Lulu's calculator](https://www.lulu.com/pricing).

Before ordering:

1. Finalize the existing draft dedication and family foreword. Review the transcription note alongside the editorial decisions; this typography pass leaves its wording as supplied.
2. Freeze the final interior, then download Lulu's cover template for that exact page count, paper, and hardcover binding. Covers are a separate PDF containing back, spine, and front; a dust jacket has its own template. Do not reuse a paperback template. Casewrap cover content needs Lulu's larger 0.75-inch cover safety area. The current files are interiors, not covers.
3. Upload `book-lulu.pdf`, download Lulu's processed print-ready PDF, and inspect trim, margins, blank pages, chapter openings, and the facsimile. This local check cannot certify Lulu's server-side processing.
4. Order one physical hardcover proof before the family run. Check gutter comfort, Garamond/footnote legibility, paper show-through, trim alignment, facsimile reproduction, and the cover/spine fit.

## Official references

- [PDF creation settings](https://help.lulu.com/en/support/solutions/articles/64000255519-pdf-creation-settings): file size, bleed, safety, gutter, fonts, images, security, and color.
- [Full bleed instructions](https://help.lulu.com/en/support/solutions/articles/64000255584): trim variation and white bleed for non-bleeding interiors.
- [Cover and interior paper stocks](https://help.lulu.com/en/support/solutions/articles/64000255473-cover-and-interior-paper-stocks): cream/white options, linen jackets, and casewrap.
- [How to create a print book](https://help.lulu.com/en/support/solutions/articles/64000255486-how-to-create-a-print-book): processed-PDF review and proof ordering.
