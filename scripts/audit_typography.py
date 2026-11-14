#!/usr/bin/env python3
"""Compare a previous accepted book with the current typography, preserving case.

This checks typesetting regressions, not the transcription against the scan.
Use an immutable prior PDF supplied with --baseline. No generator is imported.
"""
import argparse
import json
from pathlib import Path

import pymupdf

from audit_pdf import ROOT, canonical, markdown_blocks, pdf_lines, reference, rendered, sha


def check(baseline, book, output):
    blocks = markdown_blocks(ROOT/'source/manuscript.md')
    expected, note_map, _ = reference(blocks)
    versions = []
    for path in (baseline, book):
        with pymupdf.open(path) as doc:
            actual, _ = rendered(doc,pdf_lines(doc,[],infer_spaces=True),note_map,blocks)
        versions.append(actual)
    results = []
    for key in sorted(expected.keys() | versions[0].keys() | versions[1].keys()):
        context = canonical(expected.get(key,[]))['text']
        a,b = [canonical(streams.get(key,[]),reference=context,hyphen_context_ignore_case=True)
               for streams in versions]
        def anchors(c):
            return [(v['key'],v['offset']) for v in c['anchors']]
        def emphasis(c):
            return [('Italic' in g.get('font',''),'Bold' in g.get('font','')) for g in c['locations']]
        def spaces(c):
            return {pos for pos,required in c['boundaries'].items() if required}
        row = {'stream':key,'characters_identical':a['text']==b['text'],
               'anchors_identical':anchors(a)==anchors(b),'emphasis_identical':emphasis(a)==emphasis(b),
               'word_boundaries_match':(all(p in b['boundaries'] for p in spaces(a))
                                        and all(p in a['boundaries'] for p in spaces(b))),
               'hyphens_accounted_for':not any(v['kind'].startswith('UNRESOLVED') for c in (a,b) for v in c['changes'])}
        row['passed'] = all(value for name,value in row.items() if name!='stream')
        results.append(row)
    passed = all(row['passed'] for row in results)
    report = {'status':'PASS' if passed else 'FAIL',
              'scope':'Typesetting regression against the previously accepted edition; not a transcription certificate. '
                      'Source-informed discretionary hyphens and physical line breaks accounted for; case and emphasis preserved.',
              'baseline_book_sha256':sha(baseline),'book_sha256':sha(book),
              'source_markdown_sha256':sha(ROOT/'source/manuscript.md'),'comparisons':results}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'{report["status"]}: {len(results)} streams; wording, case, emphasis, word boundaries, and note attachments')
    for row in results:
        if not row['passed']:
            print(row)
    return not passed


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--book',type=Path,default=ROOT/'book.pdf')
    parser.add_argument('--output',type=Path,default=ROOT/'build/print/typography-wording.json')
    args = parser.parse_args()
    raise SystemExit(check(args.baseline,args.book,args.output))
