# Fidelity audit — review required

The scan-to-Markdown transcription is **not verbatim**. Twelve differences below
were confirmed by inspecting the scan images. Several appear to correct mistakes
in the original, but a literal edition must preserve those readings or identify
the changes explicitly. No manuscript, generator, or PDF corrections have been
applied in this audit.

These are findings from targeted inspections, not an exhaustive count of errors.
None of the 121 pages has yet received complete line-by-line sign-off.

## Confirmed scan-to-Markdown differences

Page numbers here are physical, one-based PDF pages. Printed body page numbers
are three lower. Each link opens a preserved crop of the authoritative scan.

| Scan PDF page | Scan reading | Current Markdown | Evidence |
| --- | --- | --- | --- |
| 5 | prophesy | prophecy | [Messianic prophesy](evidence/candidate-p005-dd3ff2e73319.png) |
| 7 | analyse | analyze | [study, analyse, dissect and refute](evidence/candidate-p007-003fbfe070fb.png) |
| 11 | basis | basic | [matter is the basis reality](evidence/candidate-p011-a740e3a88626.png) |
| 35 | full | fully | [To appreciate full the distinction](evidence/candidate-p035-958684cf3031.png) |
| 37 | member | members | [Bolsheviki or member of the majority](evidence/candidate-p037-6ceb225634be.png) |
| 38 | portend | portent | [the portend of events](evidence/candidate-p038-30ab53efd251.png) |
| 52 | reconcilation | reconciliation | [reconcilation of opposites](evidence/candidate-p052-7d221213a7aa.png) |
| 57 | classess | classes | [polarized into classess](evidence/candidate-p057-51c1b3aceed8.png) |
| 61 | in | is | [history in his hypothesis](evidence/candidate-p061-136712e407c4.png) |
| 82 | compliment | complement | [do not compliment each other](evidence/candidate-p082-169bb87d79e5.png) |
| 92 | seperate | separate | [a seperate set of functions](evidence/candidate-p092-d7d2b70ce10f.png) |
| 119 | charge' | charg' | [Soviet charge' d'affaires](evidence/candidate-p119-eb5a15d95644.png) |

[review.json](review.json) records stable finding IDs, exact Markdown context and
locations, dispositions, source-page coordinates, and evidence hashes. It also
records seven rejected shared OCR suggestions and four ambiguous inspections.
For example, both OCR engines proposed changing 1848 to 1846 on scan page 58;
the image supports the existing 1848. Agreement between engines is not proof.

## Independent downstream check

The Markdown-to-book check compares the body plus 142 separate footnote bodies,
and checks footnote attachment positions. It does not import the build generator.

- All 143 streams have identical non-whitespace character sequences **ignoring
  case**, after the explicitly enumerated typography changes below. This is a
  diagnostic result, not an exact fidelity certificate.
- All 142 note bodies pass the case-preserving text comparison. Body note attachments match
  after restoring two markers visibly present in the scan: [30 beside Adam
  Smith](evidence/source-heading-note-30.png) and [31 beside Malthus and
  Ricardo](evidence/source-heading-note-31.png). The existing build already
  restores these markers; they are missing from the Markdown.
- The body fails the case-preserving comparison. The existing generator turns
  uppercase emphasis into lowercase italics, producing 26 contiguous groups of
  changed characters. The audit reports the exact locations and readings.
- Six inferred spaces occur only between adjacent quotation marks. They remain
  recorded for typographic review. Word spaces are otherwise checked separately
  from character equality, so `the rapist` cannot pass as `therapist`.
- Original note numbers are mapped to printed reading-order numbers before
  comparing note identities. In particular, the source sequence 58, 60, 61, 59
  is not assumed to be numeric reading order.

Explicit downstream transformations are chapter display labels, dash/range
typography, ellipses, spaced elision marks, and a malformed Markdown quote
delimiter. Each occurrence is logged. Curly/straight quotation marks and named
typographic ligatures have explicit equivalences. A physical line-end hyphen can
be dropped only where its surrounding source context confirms the joined form.
The case-insensitive context search used to locate these hyphens does **not**
lowercase the primary text comparison. Mathematical `a²` remains text.

## Coverage and remaining work

All 121 scan pages were independently rendered upright at 300 dpi and recognized
locally by Tesseract and Apple Vision. Neither engine received the Markdown.
Raw text, word/line boxes, confidence values, images, tool configuration, and
hashes are retained under `build/fidelity/`. A second Tesseract profile improves
the results while preserving the first profile separately.
[recognition-provenance.json](recognition-provenance.json) preserves the initial
engine/configuration details and per-page hashes outside the build directory.

The current alignment has 7,438 Tesseract difference regions, 9,663 Vision
difference regions, and 278 shared suggestions. These counts measure review
work, not manuscript errors. Alignment uses case-insensitive alphanumeric tokens
to locate passages; it cannot certify punctuation, case, or exact wording.
Repeated-header exclusions are logged and still need image review. Original
contents page 3 is explicitly excluded from body alignment, never silently
counted as verified.

The remaining work is complete page-by-page scan comparison, adjudication of
the disagreement queue, punctuation and emphasis review, marginal-note review,
bibliography review, original/added front-matter accounting, and resolution of
the confirmed differences in an evidence-backed changeset. Preserve source
errors in the literal transcription; put any editorial corrections in a separate
record. Never resolve an unclear scan from grammar, historical expectation, or
OCR agreement alone.

## Reproduce

Use Python 3.11+ and the native macOS tools:

```sh
brew install tesseract pandoc poppler
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-audit.txt
.venv/bin/python scripts/ocr_source.py
.venv/bin/python scripts/ocr_source.py --profile sauvola
mkdir -p build/fidelity/swift-cache
swiftc -module-cache-path build/fidelity/swift-cache scripts/vision_ocr.swift -o build/fidelity/vision_ocr
.venv/bin/python scripts/ocr_vision.py --binary build/fidelity/vision_ocr
.venv/bin/python -m unittest discover -s scripts -p 'test_*.py' -v
.venv/bin/python scripts/audit_all.py
```

Apple Vision uses the local macOS recognition service. A restrictive process
sandbox may prevent that service from running; normal local Terminal execution
does not upload the scans. The initial run used Tesseract 5.5.4, PyMuPDF 1.28.2,
and the configuration/model hashes retained with its OCR outputs. A changed
configuration refuses to reuse old cached recognition. Archive the old output
before intentionally changing OCR settings.

`audit_all.py` deliberately exits **1 / REVIEW_REQUIRED** while any check or
review item remains unresolved. Missing OCR, changed pinned inputs, and stale
evidence also fail. `source-manifest.json` pins the authoritative scan;
`review.json` pins the inputs inspected for the evidence ledger. Updating a hash
alone does not constitute a review. Large working files stay in ignored
`build/fidelity/`; the compact initial results and image evidence live here.

The 20 adversarial/regression tests cover changed digits, ordinals, omissions,
order, word boundaries, note identity/attachment, emphasis loss, mathematical
superscripts, and accidental loss of text near page edges. They test detection
of corruption, not agreement with the existing generator.
