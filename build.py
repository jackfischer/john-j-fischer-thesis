#!/usr/bin/env python3
"""Convert MASTER-final.md into LaTeX body files for the book."""
import re, sys, subprocess, json
from collections import Counter

import os
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source', 'manuscript.md')
L = open(SRC, encoding='utf-8').read().split('\n')
report = []

fn_i = next(i for i, l in enumerate(L) if l.startswith('## Footnotes'))
bib_i = next(i for i, l in enumerate(L) if l.startswith('## Bibliography'))
pre_i = next(i for i, l in enumerate(L) if l.startswith('## Preface'))

body = L[pre_i:fn_i]
fnlines = L[fn_i + 1:bib_i]
bib = L[bib_i + 1:]

# ---------- footnotes ----------
notes = {}
for l in fnlines:
    m = re.match(r'^(\d+)\.\s+(.*)$', l)
    if m:
        notes[int(m.group(1))] = m.group(2).strip()
    elif l.strip():
        report.append('Unparsed footnote line: ' + l[:80])
assert sorted(notes) == list(range(1, 143)), 'footnote entries not 1..142'

MARK = re.compile(r'(?<![\d/\w])\s?(\d{1,3})/(?![\d/\w])')
# remove paste-tip line (Google Docs instruction, not part of the text)
body = [l for l in body if not l.startswith('_Paste tip')]

seq = []
for l in body:
    for m in MARK.finditer(l):
        seq.append(int(m.group(1)))
# headings that lost their markers in MASTER-final (present in md-verified pages 13 & 15)
HEAD_NOTES = {'### Adam Smith': 30, '### Malthus and Ricardo': 31}

HEADS = {
 'Sources of the Communist Doctrine of Inevitability': 'Sources of the Doctrine of Inevitability',
 'Evaluation of the Materialistic Conception of History': 'The Materialistic Conception of History',
}
DISPLAY = {
 'Sources of the Communist Doctrine of Inevitability': 'Sources of the Communist\\\\ Doctrine of Inevitability',
 'The Marx-Engels Doctrine of Inevitability': 'The Marx-Engels Doctrine\\\\ of Inevitability',
 'Lenin the Applier and Stalin the Continuer': 'Lenin the Applier\\\\ and Stalin the Continuer',
 'Evaluation of the Materialistic Conception of History': 'Evaluation of the Materialistic\\\\ Conception of History',
 'Is Democratic Capitalism Doomed to Failure?': 'Is Democratic Capitalism\\\\ Doomed to Failure?',
}
# ---------- inline transforms ----------
STOP_CAPS = {'USAF', 'VIII', 'NATO', 'ICBM', 'ICBMS'}
CAPRUN = re.compile(r"(?<![\w*.])((?:[A-Z][A-Z'\-]+[ ,]+)*[A-Z][A-Z'\-]{3,}(?:[ ,]+[A-Z][A-Z'\-]+)*)(?!\w)")

def caps(m):
    s = m.group(1)
    if s in STOP_CAPS or re.fullmatch(r'[IVXLC\-]+', s):
        return s
    t = s.lower()
    t = re.sub(r'\bcreator\b', 'Creator', t)          # proper noun (the Creator)
    report.append('italic: %s -> %s' % (s, t))
    # typed capitals = the quoted source's italics; \emph toggles to upright when nested in italics
    return '\\emph{' + t + '}'

def inline(t):
    t = t.replace('***', '\\* \\* \\*')           # elision asterisks in Petrie quote
    t = re.sub(r'\s+--\s+', '—', t)               # typed dash -> em dash
    t = re.sub(r'(?<=\w)--(?=\w)', '—', t)
    t = re.sub(r'(?<=\d)-(?=\d)', '–', t)          # number ranges -> en dash
    t = re.sub(r'(?<=\d)–(?=\d)', '–', t)
    t = CAPRUN.sub(caps, t)
    NB = '\u00a0'
    t = re.sub(r'(?<=\b[A-Z]\.) (?=[A-Z]\.)', NB, t)        # U. S., N. J., D. C.
    t = re.sub(r'\b(pp?\.|Vol\.|No\.) (?=[\dIVXivx])', lambda m: m.group(1) + NB, t)
    t = re.sub(r'\((\d{1,2}) (?=[A-Z][a-z])', lambda m: '(' + m.group(1) + NB, t)  # (1 April
    return t

def conv_marks(l):
    def rep(m):
        return '[^%s]' % m.group(1)
    return MARK.sub(rep, l)

out = []
chap_first = False
for l in body:
    if l.startswith('## '):
        title = l[3:].strip()
        if title == 'Preface':
            out.append('\\chapter{Preface}')
        else:
            m = re.match(r'Chapter ([IVX]+) — (.*)', title)
            if m.group(1) == 'I':
                out.append('\\mainmatter')
            head = HEADS.get(m.group(2), m.group(2))
            out.append('\\chapter[%s][%s]{%s}' % (m.group(2), head, DISPLAY.get(m.group(2), m.group(2))))
        out.append('')
        chap_first = True
        continue
    if l.startswith('### '):
        h = l.strip()
        n = HEAD_NOTES.get(h)
        out.append('## ' + h[4:] + ('[^%d]' % n if n else ''))
        if n:
            seq_insert = n
        continue
    m = re.match(r'^\*\((Marginal notes?): (.*)\)\*\s*$', l)
    if m:
        out.append('\\marginalnote{%s}{%s}' % (m.group(1), inline(m.group(2))))
        continue
    if not l.startswith('>') and re.search(r'\d/ > "', l):
        # block quote run into the preceding paragraph in the transcription (line 399)
        a, b = re.split(r'(?<=\d/) > (?=")', l, maxsplit=1)
        report.append('Split run-in block quote: ' + a[-40:])
        out.append(inline(conv_marks(a))); out.append(''); out.append('> ' + inline(b))
        continue
    t = inline(conv_marks(l))
    if chap_first and t.strip() and not t.startswith('>') and not t.startswith('\\'):
        # first words of a chapter in small caps
        mm = re.match(r'^([A-Z][\w\'’]*(?: [\w\'’]+)?)(\s)', t)
        if mm and '*' not in mm.group(1):
            t = '\\noindent\\textsc{%s}%s' % (mm.group(1), t[mm.end(1):])
        chap_first = False
    elif t.strip():
        chap_first = False
    out.append(t)

# footnote definitions
out.append('')
for n in sorted(notes):
    out.append('[^%d]: %s' % (n, inline(notes[n])))
    out.append('')

# ---------- verification ----------
full_seq = []
for l in out:
    if l.startswith('[^') and ']:' in l[:8]:
        continue
    full_seq += [int(x) for x in re.findall(r'\[\^(\d+)\]', l)]
c = Counter(full_seq)
report.append('marker sequence length %d; unique %d' % (len(full_seq), len(c)))
report.append('missing: %s' % sorted(set(range(1, 143)) - set(c)))
report.append('duplicates: %s' % [k for k, v in c.items() if v > 1])
prev = 0
for n in full_seq:
    if n != prev + 1:
        report.append('order: %d follows %d' % (n, prev))
    prev = n

# ---------- bibliography ----------
ENT = re.compile(r'^(?:[A-Z][A-Za-z\'\-\. ]{1,60}, .*(\*|").*|Editors of .*)')
bout = ['\\backmatter', '\\chapter{Bibliography}', '']
for l in bib:
    if not l.strip():
        continue
    if l.startswith('### '):
        bout += ['', '## ' + l[4:].strip(), '']
        continue
    if l.startswith('>'):
        bout += ['::: bibnote', '', inline(l), '', ':::', '']
        continue
    if ENT.match(l) and len(l) < 330:
        bout += ['::: bibentry', '', inline(l), '', ':::', '']
    elif l.startswith('Sheed, F. J.,'):
        k = l.index('1947.') + 5
        bout += ['::: bibentry', '', inline(l[:k]), '', ':::', '', '::: bibnote', '', inline(l[k:].strip()), '', ':::', '']
        report.append('Bibliography: split Sheed entry from its annotation (run together in transcription)')
    else:
        bout += ['::: bibnote', '', inline(l), '', ':::', '']

open('build/body.md', 'w').write('\n'.join(out) + '\n')
open('build/bib.md', 'w').write('\n'.join(bout) + '\n')

def pandoc(src, dst):
    subprocess.run(['pandoc', src, '-f', 'markdown+smart-auto_identifiers-implicit_figures',
                    '--top-level-division=chapter', '--lua-filter=divs.lua', '-t', 'latex',
                    '--wrap=preserve', '-o', dst], check=True)
pandoc('build/body.md', 'build/body.tex')
pandoc('build/bib.md', 'build/bib.tex')

# move footnotes out of section headings (avoid letterspaced note text)
def fix_heading_notes(tex):
    out, i = [], 0
    key = '\\texorpdfstring{'
    while True:
        j = tex.find(key, i)
        if j < 0:
            out.append(tex[i:]); break
        out.append(tex[i:j])
        k = j + len(key); depth = 1; a = k
        while depth:
            c = tex[k]; depth += (c == '{') - (c == '}'); k += 1
        first = tex[a:k-1]
        # skip second arg
        assert tex[k] == '{'
        d = 1; m = k + 1
        while d:
            c = tex[m]; d += (c == '{') - (c == '}'); m += 1
        f = first.find('\\footnote{')
        if f >= 0:
            fb = f + len('\\footnote{'); d = 1; e = fb
            while d:
                c = first[e]; d += (c == '{') - (c == '}'); e += 1
            note = first[fb:e-1]
            out.append(first[:f] + '\\footnotemark' + first[e:])
            # the section command's closing brace follows; append footnotetext after it
            rest = tex[m:]
            assert rest[0] == '}'
            out.append('}\\footnotetext{' + note + '}')
            i = m + 1
        else:
            out.append(first); i = m
    return ''.join(out)
for fn in ('build/body.tex',):
    t = open(fn).read(); open(fn, 'w').write(fix_heading_notes(t))

# sample: Preface + Chapter I only
tex = open('build/body.tex').read()
k = tex.index('\\chapter[Sources of')
open('build/sample-body.tex', 'w').write(tex[:k])

open('build/report.txt', 'w').write('\n'.join(report) + '\n')
print('\n'.join(r for r in report if not r.startswith('italic:')))
print('italic runs:', sum(r.startswith('italic:') for r in report))
