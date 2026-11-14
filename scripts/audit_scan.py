#!/usr/bin/env python3
"""Align independent scan recognition with Markdown and prepare evidence crops.

Recognition text is never substituted into the manuscript. Loose alignment is
only a locator: capitalization, punctuation, hyphenation, and unmatched regions
still require image review, including regions where both engines agree.
"""
import argparse
import collections
import csv
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/fidelity'
# Keep accented letters: ASCII-only matching truncated "chargé" to "charg" and
# caused a misleading missing-letter finding. This remains a loose locator.
WORDS = re.compile(r'[^\W_]+')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain_inlines(inlines):
    result = []
    for node in inlines:
        kind, value = node['t'], node.get('c')
        if kind == 'Str': result.append(value)
        elif kind in ('Space', 'SoftBreak', 'LineBreak'): result.append(' ')
        elif kind in ('Emph', 'Strong', 'SmallCaps', 'Strikeout', 'Superscript', 'Subscript'):
            result.append(plain_inlines(value))
        elif kind == 'Quoted':
            mark = '"' if value[0]['t'] == 'DoubleQuote' else "'"
            result.append(mark + plain_inlines(value[1]) + mark)
        else:
            raise ValueError(f'Unaccounted Markdown inline node {kind}')
    return ''.join(result)


def markdown_blocks(path):
    raw = path.read_text()
    ast = json.loads(subprocess.check_output(['pandoc', str(path), '-f', 'markdown-smart', '-t', 'json'], text=True))
    blocks = []
    state = {'section': 'original-front', 'chapter': None}

    def walk(nodes, parent=''):
        for i, node in enumerate(nodes):
            identity = f'{parent}/{i}'
            kind, value = node['t'], node.get('c')
            if kind in ('Para', 'Plain', 'Header'):
                text = plain_inlines(value[2] if kind == 'Header' else value)
                if kind == 'Header' and text in ('Preface', 'Footnotes', 'Bibliography'):
                    state['section'] = text.lower()
                if kind == 'Header' and text.startswith('Chapter '):
                    state['section'] = 'body'
                    state['chapter'] = text
                if text.startswith('Paste tip:'):
                    blocks.append({'id': identity, 'kind': kind, 'text': text,
                                   'section': 'excluded Google Docs instruction'})
                else:
                    blocks.append({'id': identity, 'kind': kind, 'text': text, **state})
            elif kind == 'BlockQuote':
                walk(value, identity + '/quote')
            elif kind == 'OrderedList':
                start = value[0][0]
                for index, item in enumerate(value[1], start):
                    before = len(blocks)
                    walk(item, identity + f'/item{index}')
                    blocks[before]['list_number'] = index
                    blocks[before]['list_label'] = chr(96+index) if value[0][1]['t']=='LowerAlpha' else str(index)
            else:
                raise ValueError(f'Unaccounted Markdown block node {kind}')
    walk(ast['blocks'])
    # Pandoc lists discard typed ordinal values after the first one; independently
    # require the actual footnote labels in the Markdown to be 1..142.
    foot = raw.split('## Footnotes\n', 1)[1].split('## Bibliography\n', 1)[0]
    labels = [int(n) for n in re.findall(r'(?m)^(\d+)\. ', foot)]
    if labels != list(range(1, 143)):
        raise ValueError('Literal Markdown footnote labels are not 1..142')
    for block in blocks:
        needle = block['text'][:45]
        found = raw.find(needle)
        block['markdown_line'] = raw[:found].count('\n') + 1 if found >= 0 else None
    return blocks


def markdown_tokens(blocks):
    tokens = []
    for block in blocks:
        if block['section'].startswith('excluded '): continue
        text = block['text']
        if 'list_number' in block:
            text = block['list_label'] + '. ' + text
        for match in WORDS.finditer(text):
            tokens.append({'text': match[0], 'key': match[0].lower(), 'block': block['id'],
                           'section': block['section'], 'markdown_line': block['markdown_line'],
                           'offset': match.start()})
    return tokens


def tesseract_tokens(directory):
    tokens, excluded = [], []
    for page in range(1, 122):
        path = directory / f'page-{page:03d}.tsv'
        if not path.exists(): raise ValueError(f'Missing OCR: {path}')
        with path.open() as handle:
            rows = list(csv.DictReader(handle, delimiter='\t', quoting=csv.QUOTE_NONE))
        grouped = collections.defaultdict(list)
        for row in rows:
            if row['level'] == '5' and row['text'].strip():
                grouped[tuple(row[k] for k in ('block_num','par_num','line_num'))].append(row)
        excluded_ids = set()
        for group in grouped.values():
            text = ' '.join(row['text'] for row in group)
            top = min(int(row['top']) for row in group) / 300 * 72
            reason = furniture(page,text,top)
            if reason:
                excluded_ids.update(id(row) for row in group)
        for row in rows:
            if row['level'] != '5' or not row['text'].strip(): continue
            box = [int(row[k]) for k in ('left', 'top', 'width', 'height')]
            if id(row) in excluded_ids:
                excluded.append({'page': page, 'text': row['text'], 'bbox': box,
                                 'reason': furniture(page,' '.join(r['text'] for r in grouped[tuple(row[k] for k in ('block_num','par_num','line_num'))]),box[1]/300*72)})
                continue
            for match in WORDS.finditer(row['text']):
                tokens.append({'text': match[0], 'key': match[0].lower(), 'page': page,
                               'bbox': box, 'confidence': float(row['conf'])})
    return tokens, excluded


def furniture(page, text, top):
    """Never discard an entire top/bottom band: continuation text can start high."""
    if page == 3:
        return 'original contents (explicitly omitted in the edition)'
    solid = ''.join(WORDS.findall(text)).lower()
    header = 'anideologicaloffensiveforthefreeworld'
    if page > 1 and top < 105 and len(solid) > 20 and difflib.SequenceMatcher(None,solid,header).ratio() > .55:
        return 'recognized repeated title header (image review still required)'
    folio = 'i' if page == 2 else str(page-3)
    if page > 1 and top > 680 and solid == folio:
        return 'recognized original folio'
    return None


def vision_tokens(directory):
    tokens, excluded = [], []
    for page in range(1, 122):
        path = directory / f'page-{page:03d}.vision.json'
        data = json.loads(path.read_text())
        observations = data['observations']
        for row in observations: row['top'] = 1-row['bbox'][1]-row['bbox'][3]
        observations.sort(key=lambda row: (round(row['top']*792/3), row['bbox'][0]))
        grouped = []
        for row in observations:
            center = row['top'] + row['bbox'][3]/2
            if grouped and abs(center-grouped[-1][0]) < .005:
                grouped[-1][1].append(row)
            else:
                grouped.append((center,[row]))
        excluded_ids = set()
        for _, group in grouped:
            text = ' '.join(row['candidates'][0]['text'] for row in group)
            if furniture(page,text,min(row['top'] for row in group)*792):
                excluded_ids.update(id(row) for row in group)
        for row in observations:
            text = row['candidates'][0]['text']
            x, y, w, h = row['bbox']; top = (1-y-h)*792
            box = [x*2550, (1-y-h)*3300, w*2550, h*3300]
            if id(row) in excluded_ids:
                excluded.append({'page': page, 'text': text, 'bbox': box,
                                 'reason': 'original contents' if page == 3 else 'recognized title header / folio'})
                continue
            for match in WORDS.finditer(text):
                tokens.append({'text': match[0], 'key': match[0].lower(), 'page': page,
                               'bbox': box, 'confidence': row['candidates'][0]['confidence']})
    return tokens, excluded


def align(expected, actual):
    opcodes = difflib.SequenceMatcher(None, [t['key'] for t in expected],
                                     [t['key'] for t in actual], autojunk=False).get_opcodes()
    findings = []
    coverage = collections.defaultdict(lambda: {'matched_words': 0, 'recognized_words': 0, 'markdown_ranges': []})
    for token in actual: coverage[token['page']]['recognized_words'] += 1
    for op, i, j, k, l in opcodes:
        if op == 'equal':
            pages = collections.defaultdict(list)
            for expected_index, actual_index in zip(range(i, j), range(k, l)):
                page = actual[actual_index]['page']
                coverage[page]['matched_words'] += 1
                pages[page].append(expected_index)
            for page, indices in pages.items():
                coverage[page]['markdown_ranges'].append([min(indices), max(indices)+1])
            continue
        source = actual[k:l]
        pages = sorted({v['page'] for v in source})
        if not pages and actual:
            pages = [actual[min(k,len(actual)-1)]['page']]
        findings.append({'op': op, 'markdown_range': [i,j], 'ocr_range': [k,l], 'pages': pages,
                         'markdown': ' '.join(v['text'] for v in expected[i:j]),
                         'recognized': ' '.join(v['text'] for v in source),
                         'context_before': ' '.join(v['text'] for v in expected[max(0,i-12):i]),
                         'context_after': ' '.join(v['text'] for v in expected[j:j+12]),
                         'markdown_location': expected[i] if i<len(expected) else None,
                         'ocr_locations': source})
    return findings, dict(coverage)


def crop(candidate, identity):
    locations = candidate['ocr_locations']
    if not locations: return None
    page = locations[0]['page']
    page_locs = [row for row in locations if row['page'] == page]
    with Image.open(OUT / 'ocr' / f'page-{page:03d}.png') as image:
        top = max(0,int(min(row['bbox'][1] for row in page_locs))-130)
        bottom = min(image.height,int(max(row['bbox'][1]+row['bbox'][3] for row in page_locs))+130)
        path = OUT / 'review' / f'{identity}.png'
        image.crop((150,top,2450,bottom)).save(path)
    return str(path.relative_to(OUT))


def verify_ocr(directory, source):
    """Reject OCR made from another scan or modified after recognition."""
    config = json.loads((directory/'configuration.json').read_text())
    if config['source_sha256'] != sha(source) or config['dpi'] != 300:
        raise ValueError('OCR source hash or rendering resolution differs')
    inventory = []
    for page in range(1, 122):
        base = directory/f'page-{page:03d}'
        completed = json.loads(base.with_suffix('.complete.json').read_text())
        if set(completed) != {'.png', '.txt', '.tsv'}:
            raise ValueError(f'Incomplete OCR provenance p{page}')
        for extension, expected in completed.items():
            if sha(base.with_suffix(extension)) != expected:
                raise ValueError(f'Modified OCR input p{page} {extension}')
        original = OUT/'ocr'/f'page-{page:03d}.png'
        vision_path = original.with_suffix('.vision.json')
        vision = json.loads(vision_path.read_text())
        if vision['provenance']['image_sha256'] != sha(original):
            raise ValueError(f'Stale Vision recognition p{page}')
        if sha(original) != completed['.png']:
            raise ValueError(f'Recognition engines used different page images p{page}')
        inventory.append({'page':page, 'tesseract_files':completed,
                          'vision_json_sha256':sha(vision_path),
                          'vision_provenance':vision['provenance']})
    return {'configuration':config, 'pages':inventory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='ocr-sauvola')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'review').mkdir(exist_ok=True)
    manuscript = ROOT/'source/manuscript.md'
    provenance = verify_ocr(OUT/args.profile, ROOT/'source/original-1957-typescript-scan.pdf')
    blocks = markdown_blocks(manuscript)
    expected = markdown_tokens(blocks)
    tess, te = tesseract_tokens(OUT / args.profile)
    vision, ve = vision_tokens(OUT/'ocr')
    tf, tc = align(expected, tess)
    vf, vc = align(expected, vision)
    decisions = {}
    ledger_path = ROOT/'audit/review.json'
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        observed = ledger['observed_inputs']
        if (observed.get('source/manuscript.md') == sha(manuscript)
                and observed.get('source/original-1957-typescript-scan.pdf') == provenance['configuration']['source_sha256']):
            for finding in ledger['findings']:
                for identity in [finding['id'], *finding.get('alignment_aliases', [])]:
                    decisions[identity] = finding
    tess_map = {tuple(row['markdown_range']): row for row in tf}
    candidates = []
    for row in vf:
        other = tess_map.get(tuple(row['markdown_range']))
        if other and row['recognized'] and row['recognized'].lower() == other['recognized'].lower():
            candidate = dict(row, tesseract=other['recognized'], status='UNREVIEWED')
            signature = (str(candidate['pages'])+'|'+candidate['markdown']+'|'+candidate['recognized']+'|'+candidate['context_before']+'|'+candidate['context_after']).encode()
            identity = f'candidate-p{candidate["pages"][0]:03d}-' + hashlib.sha256(signature).hexdigest()[:12]
            candidate['id'] = identity
            if identity in decisions:
                decision = decisions[identity]
                candidate['status'] = decision['disposition']
                candidate['review_ledger_id'] = decision['id']
                candidate['review_basis'] = decision.get('resolution', decision['basis'])
            candidate['crop'] = crop(candidate, identity)
            candidates.append(candidate)
    report = {'status': 'SCAN_REVIEW_REQUIRED', 'source_sha256': sha(ROOT/'source/original-1957-typescript-scan.pdf'),
              'markdown_sha256': sha(manuscript), 'markdown_words': len(expected),
              'alignment_only': 'Case-insensitive alphanumeric tokens; never a fidelity certificate.',
              'ocr_provenance': provenance,
              'tesseract': {'tokens': len(tess), 'findings': tf, 'coverage': tc, 'excluded': te},
              'vision': {'tokens': len(vision), 'findings': vf, 'coverage': vc, 'excluded': ve},
              'agreement_candidates': candidates,
              'full_page_review': {str(p): 'UNREVIEWED' for p in range(1,122)}}
    (OUT/'scan-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'markdown-inventory.json').write_text(json.dumps(blocks,ensure_ascii=False,indent=2)+'\n')
    md = ['# Scan-to-Markdown review queue', '',
          'Neither OCR agreement nor high confidence proves the transcription correct. '
          'These are priority candidates; all other discrepancies and all page reviews remain open.', '',
          f'Markdown tokens: {len(expected)}. Tesseract difference regions: {len(tf)}. '
          f'Vision difference regions: {len(vf)}. Shared candidates: {len(candidates)}.', '']
    for row in candidates:
        md.extend([f'## {row["id"]} — PDF page(s) {row["pages"]}', '',
                   f'Markdown: `{row["markdown"]}`', '', f'Both recognition engines: `{row["recognized"]}`', '',
                   f'Context: {row["context_before"]} **[{row["markdown"]}]** {row["context_after"]}', '',
                   f'![Scan evidence]({row["crop"]})', '', f'Disposition: {row["status"]}',
                   row.get('review_basis', ''), ''])
    (OUT/'REVIEW.md').write_text('\n'.join(md))
    print(f'SCAN_REVIEW_REQUIRED: {len(tf)} Tesseract regions, {len(vf)} Vision regions, {len(candidates)} shared candidates')
    raise SystemExit(1)


if __name__ == '__main__':
    main()
