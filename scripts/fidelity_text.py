"""Text comparison helpers, independent of the manuscript build pipeline.

Shared audit algorithms are vendored in each standalone repository.
"""
import collections
import difflib
import re

EQUIVALENTS = dict(zip('‘’“”', "''\"\"")) | {
    'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st', 'ﬆ': 'st'}

def line_text(line):
    return ''.join(g['c'] for g in line)


def pdf_lines(doc, inventory, infer_spaces=False):
    """Preserve native lines, then merge separately encoded runs on one baseline."""
    result = {}
    for page_no, page in enumerate(doc, 1):
        lines = []
        for bi, block in enumerate(page.get_text('rawdict')['blocks']):
            for li, line in enumerate(block.get('lines', [])):
                glyphs = []
                for si, span in enumerate(line['spans']):
                    for ci, char in enumerate(span['chars']):
                        glyphs.append({'c': char['c'], 'page': page_no, 'bbox': char['bbox'],
                                       'x': char['origin'][0], 'y': char['origin'][1],
                                       'size': span['size'], 'font': span['font'],
                                       'id': f'p{page_no}:b{bi}:l{li}:s{si}:c{ci}'})
                if not any(g['c'].strip() for g in glyphs):
                    continue
                main_size = max(g['size'] for g in glyphs if g['c'].strip())
                y = next(g['y'] for g in glyphs if abs(g['size'] - main_size) < .001 and g['c'].strip())
                lines.append((y, min(g['x'] for g in glyphs), glyphs))
        merged = []
        for y, x, glyphs in sorted(lines, key=lambda v: (round(v[0], 1), v[1])):
            if merged and abs(y - merged[-1][0]) < .08:
                merged[-1][1].extend(glyphs)
            else:
                merged.append((y, glyphs))
        result[page_no] = []
        for line_id, (_, glyphs) in enumerate(merged):
            # Preserve native content order within each run. Components of a ligature
            # overlap geometrically; sorting their individual x coordinates scrambles them.
            out = []
            heading = (any(abs(g['size'] - 13.92) < .01 for g in glyphs if g['c'].strip())
                       or all('Bold' in g['font'] for g in glyphs if g['c'].strip()))
            for glyph in glyphs:
                glyph['heading'] = heading
                if infer_spaces and out:
                    prev = out[-1]
                    gap = glyph['bbox'][0] - prev['bbox'][2]
                    if (max(prev['size'], glyph['size']) < 20
                            and not prev['c'].isspace() and not glyph['c'].isspace()
                            and gap > .11 * min(glyph['size'], prev['size'])):
                        out.append(dict(glyph, c=' ', inferred_space=True))
                glyph['line'] = f'p{page_no}:line{line_id}'
                out.append(glyph)
            meaningful = [g for g in out if g['c'].strip()]
            if meaningful and meaningful[-1]['c'] == '-':
                meaningful[-1]['eol_hyphen'] = True
            result[page_no].append(out)
            inventory.append({'page': page_no, 'line': line_id, 'text': line_text(out), 'glyphs': out})
    return result


def add_line(stream, glyphs):
    glyphs = list(glyphs)
    while glyphs and glyphs[0]['c'].isspace():
        glyphs.pop(0)
    while glyphs and glyphs[-1]['c'].isspace():
        glyphs.pop()
    stream.extend(glyphs)
    stream.append({'c': '\n', 'line_break': True})


def canonical(glyphs, omit_chapter_dot=False, reference=None, hyphen_context_ignore_case=False):
    atoms = []
    changes = []
    for glyph in glyphs:
        if omit_chapter_dot and glyph.get('chapter_separator'):
            changes.append({'kind': 'chapter-label period omitted', 'location': glyph.get('id')})
            continue
        if 'anchor' in glyph:
            atoms.append(dict(glyph)); continue
        char = glyph['c']
        for c in EQUIVALENTS.get(char, char):
            atoms.append(dict(glyph, c=c))
    # Resolve only a physical line-end hyphen, using an exact surrounding source passage.
    if reference is not None:
        solid = ''.join(a['c'] for a in atoms if not a['c'].isspace())
        offset = 0
        for atom in atoms:
            c = atom['c']
            if c.isspace():
                continue
            if c == '-' and atom.get('eol_hyphen'):
                left, right = solid[max(0, offset-32):offset], solid[offset+1:offset+33]
                keep, drop = left + '-' + right, left + right
                search_reference = reference.lower() if hyphen_context_ignore_case else reference
                keep_at = search_reference.find(keep.lower() if hyphen_context_ignore_case else keep)
                drop_at = search_reference.find(drop.lower() if hyphen_context_ignore_case else drop)
                if drop_at >= 0 and keep_at < 0:
                    atom['c'] = ''
                    changes.append({'kind': 'discretionary line-end hyphen', 'location': atom.get('id'),
                                    'reference_offset': drop_at + len(left), 'context': drop,
                                    'context_matched_ignoring_case': hyphen_context_ignore_case})
                elif keep_at < 0:
                    changes.append({'kind': 'UNRESOLVED line-end hyphen', 'location': atom.get('id'), 'context': keep})
            offset += len(c)
    text = ''
    locations = []
    boundaries = {}
    anchors = []
    previous = None
    for atom in atoms:
        if 'anchor' in atom:
            anchors.append({'key': atom['anchor'], 'offset': len(text), 'location': atom.get('id')})
        elif atom['c'].isspace():
            # A true space is mandatory; a physical line break is allowed to reflow.
            if text:
                boundaries[len(text)] = boundaries.get(len(text), False) or not atom.get('line_break', False)
        else:
            text += atom['c']
            locations.extend([atom] * len(atom['c']))
        previous = atom
    boundaries.pop(len(text), None)
    return {'text': text, 'locations': locations, 'boundaries': boundaries,
            'anchors': anchors, 'changes': changes}


def compare(label, expected, actual, book=False, check_emphasis=True):
    results = []
    for stream in sorted(expected.keys() | actual.keys()):
        if book and stream == 'toc':
            continue  # Report original-vs-regenerated contents separately; never call it verified.
        a = canonical(expected.get(stream, []), omit_chapter_dot=book)
        b = canonical(actual.get(stream, []), reference=a['text'] if book else None,
                      hyphen_context_ignore_case=book)
        finding = {'comparison': label, 'stream': stream, 'emphasis_checked': check_emphasis,
                   'expected_chars': len(a['text']),
                   'actual_chars': len(b['text']), 'text_equal': a['text'] == b['text'],
                   'changes': a['changes'] + b['changes'], 'differences': []}
        if a['text'] != b['text']:
            # Tokens improve alignment speed; character offsets still locate every difference.
            pattern = r'\w+|[^\w]'
            aa, bb = re.findall(pattern, a['text']), re.findall(pattern, b['text'])
            ai, bj = [0], [0]
            for token in aa: ai.append(ai[-1] + len(token))
            for token in bb: bj.append(bj[-1] + len(token))
            for op, i, j, k, l in difflib.SequenceMatcher(None, aa, bb, autojunk=False).get_opcodes():
                if op == 'equal': continue
                source_loc = a['locations'][ai[i]] if ai[i] < len(a['locations']) else {}
                target_loc = b['locations'][bj[k]] if bj[k] < len(b['locations']) else {}
                finding['differences'].append({'kind': op, 'expected': ''.join(aa[i:j]),
                    'actual': ''.join(bb[k:l]), 'expected_location': source_loc,
                    'actual_location': target_loc, 'context': a['text'][max(0,ai[i]-50):ai[j]+50]})
        else:
            missing = sorted(pos for pos, mandatory in a['boundaries'].items()
                             if mandatory and pos not in b['boundaries'])
            extra = sorted(pos for pos, mandatory in b['boundaries'].items()
                           if mandatory and pos not in a['boundaries'])
            # Extraction inserts spaces in tracked display type; these remain findings.
            finding['word_boundary_differences'] = [
                {'offset': pos, 'kind': kind, 'context': a['text'][max(0,pos-25):pos]+'|'+a['text'][pos:pos+25],
                 'expected_location': a['locations'][pos], 'actual_location': b['locations'][pos]}
                for kind, positions in [('missing space', missing), ('extra space', extra)] for pos in positions]
            style_diffs = []
            allowed_style_chars = collections.Counter()
            for pos, (left, right) in enumerate(zip(a['locations'], b['locations'])):
                def flags(g):
                    return (('i' in g.get('style', '')) or 'Italic' in g.get('font', ''),
                            ('b' in g.get('style', '')) or 'Bold' in g.get('font', ''))
                si, sb = flags(left); ti, tb = flags(right)
                italic_ok = si == ti
                bold_ok = sb == tb
                if book and left.get('heading'):
                    if not si and ti and abs(left.get('size',0)-13.92) < .01:
                        italic_ok = True
                        allowed_style_chars['chapter titles in italics'] += 1
                    if sb and not tb:
                        bold_ok = True
                        allowed_style_chars['heading bold replaced by display styling'] += 1
                if check_emphasis and not (italic_ok and bold_ok):
                    if style_diffs and style_diffs[-1]['end'] == pos and style_diffs[-1]['source_flags'] == [si,sb] and style_diffs[-1]['target_flags'] == [ti,tb]:
                        style_diffs[-1]['end'] += 1
                        style_diffs[-1]['text'] += a['text'][pos]
                    else:
                        style_diffs.append({'start':pos, 'end':pos+1, 'text':a['text'][pos],
                                            'source_flags':[si,sb], 'target_flags':[ti,tb],
                                            'expected_location':left, 'actual_location':right})
            finding['emphasis_differences'] = style_diffs
            finding['documented_design_style_characters'] = dict(allowed_style_chars)
        finding['anchors_equal'] = [(v['key'], v['offset']) for v in a['anchors']] == [
            (v['key'], v['offset']) for v in b['anchors']]
        if not finding['anchors_equal']:
            finding['expected_anchors'] = a['anchors']; finding['actual_anchors'] = b['anchors']
        finding['passed'] = (finding['text_equal'] and finding['anchors_equal']
            and not finding.get('word_boundary_differences')
            and not finding.get('emphasis_differences')
            and not any(c['kind'].startswith('UNRESOLVED') for c in finding['changes']))
        results.append(finding)
    return results
