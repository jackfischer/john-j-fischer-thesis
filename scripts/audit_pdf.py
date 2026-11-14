#!/usr/bin/env python3
"""Independently compare Markdown wording and note attachment with the printed PDF.

The Markdown remains untrusted relative to the scan. This is a separate pipeline
check and reports case changes rather than silently lowercasing the reference.
"""
import collections
import hashlib
import json
from pathlib import Path
import re

import pymupdf

from audit_scan import ROOT, markdown_blocks
from fidelity_text import add_line, canonical, compare, line_text, pdf_lines, EQUIVALENTS

OUT=ROOT/'build/fidelity'
SUP_DIGITS=dict(zip('⁰¹²³⁴⁵⁶⁷⁸⁹','0123456789'))
MARK=re.compile(r'(?<![\w/])\s?(\d{1,3})/(?![\w/])')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def typography(text):
    # Each class is recorded in the report; none changes a word or a digit.
    text=re.sub(r'\s+--\s+','—',text)
    text=re.sub(r'(?<=\w)--(?=\w)','—',text)
    text=re.sub(r'(?<=\d)-(?=\d)','–',text)
    text=re.sub(r'^--\s+','—',text)
    text=text.replace('--','–')
    return text.replace('...','…').replace('***','* * *')


def reference(blocks):
    streams=collections.defaultdict(list)
    order=[];changes=[]
    for block in blocks:
        section=block['section']
        if section=='footnotes':
            if 'list_number' in block:
                key=f'note:{block["list_number"]}'
                if key in streams:raise ValueError(f'Duplicate {key}')
                streams[key]=[{'c':c,'id':block['id'],'markdown_line':block['markdown_line']}
                              for c in typography(block['text'])]
            elif block['text']!='Footnotes':raise ValueError('Unaccounted footnote block')
            continue
        if section not in ('preface','body','bibliography'):continue
        text=block['text']
        if 'list_label' in block:text=block['list_label']+'. '+text
        match=re.fullmatch(r'Chapter ([IVX]+) — (.*)',text)
        if match:
            replacement='chapter '+match[1].lower()+' '+match[2]
            changes.append({'kind':'display chapter label','original':text,'printed':replacement,'block':block['id']})
            text=replacement
        repaired=re.sub(r'(?<=\d/) > (?=")',' ',text)
        if repaired!=text:
            changes.append({'kind':'run-in Markdown blockquote delimiter repaired',
                            'original':text,'printed':repaired,'block':block['id']})
        converted=typography(repaired)
        if text!=converted:
            changes.append({'kind':'dash / ellipsis / elision typography','original':text,'printed':converted,'block':block['id']})
        text=converted
        position=0
        for match in MARK.finditer(text):
            streams['body'].extend({'c':c,'id':block['id'],'markdown_line':block['markdown_line']} for c in text[position:match.start()])
            original=int(match[1]);order.append(original)
            streams['body'].append({'c':'','anchor':f'note:{original}','id':block['id']})
            position=match.end()
        streams['body'].extend({'c':c,'id':block['id'],'markdown_line':block['markdown_line']} for c in text[position:])
        # These are independently visible in scan PDF pages 13 and 15. They are
        # missing from the Markdown, and are separately reported as source repairs.
        restored={'Adam Smith':30,'Malthus and Ricardo':31}.get(text) if block['kind']=='Header' else None
        if restored:
            streams['body'].append({'c':'','anchor':f'note:{restored}','id':block['id']})
            order.append(restored)
            changes.append({'kind':'source-evidenced footnote marker absent from Markdown',
                            'heading':text,'original_note':restored,'scan_pdf_page':13 if restored==30 else 15})
        streams['body'].append({'c':'\n','line_break':True})
    if sorted(order)!=list(range(1,143)):raise ValueError('Reference anchor coverage is not 1..142')
    return dict(streams),{i:original for i,original in enumerate(order,1)},changes


def roman(number):
    result=''
    for value,letters in [(100,'c'),(90,'xc'),(50,'l'),(40,'xl'),(10,'x'),(9,'ix'),(5,'v'),(4,'iv'),(1,'i')]:
        while number>=value:result+=letters;number-=value
    return result


def rendered(doc,lines,note_map,blocks):
    streams=collections.defaultdict(list);excluded=[]
    # Edition front matter may reflow. Locate the author's text by bookmarks,
    # retaining the original positions for PDFs predating the bookmark export.
    starts={title:page for level,title,page in doc.get_toc() if level==1}
    first_page=starts.get('Preface',13)
    main_start=starts.get('Introduction',15)
    chapter_titles=[re.sub(r'^Chapter [IVX]+ — ','',b['text']).lower()
                    for b in blocks if b['kind']=='Header' and b['text'].startswith('Chapter ')]
    headers=set(chapter_titles)|{'an ideological offensive for the free world','preface','bibliography',
        'sources of the doctrine of inevitability','the materialistic conception of history'}
    note=None
    next_anchor=1
    for page,page_lines in lines.items():
        if page<first_page or page==len(doc):
            for line in page_lines:excluded.append({'page':page,'text':line_text(line),'reason':'edition front matter / facsimile / colophon'})
            continue
        folio=roman(page) if page<main_start else str(page-main_start+1)
        furniture=headers|{folio}|{f'{folio} {h}' for h in headers}|{f'{h} {folio}' for h in headers}
        rules=[d['rect'] for d in doc[page-1].get_drawings()
               if any(abs(d['rect'].width-width)<.02 for width in (43.636,39.851))
               and d['rect'].height<.1]
        if len(rules)>1:raise ValueError(f'Multiple footnote rules p{page}')
        rule=rules[0] if rules else None
        for line in page_lines:
            text=line_text(line).strip()
            if max(g['y'] for g in line)<60 or min(g['y'] for g in line)>590:
                if text not in furniture:raise ValueError(f'Unexpected furniture p{page}: {text!r}')
                excluded.append({'page':page,'text':text,'reason':'validated running head / folio'});continue
            if rule and min(g['y'] for g in line)>rule.y0:
                label=re.match(r'^(\d+)\.',text)
                if label and min(g['x'] for g in line if g['c'].strip())<rule.x0+2:
                    rendered_number=int(label[1])
                    original=note_map[rendered_number]
                    note=f'note:{original}'
                    if note in streams:raise ValueError(f'Duplicate rendered footnote {note}')
                    remaining=len(label[0]);keep=[]
                    for g in line:
                        if remaining and not g['c'].isspace():remaining-=1
                        else:keep.append(g)
                    line=keep
                if note is None:raise ValueError(f'Unattached note continuation p{page}')
                add_line(streams[note],line);continue
            body=[];i=0
            while i<len(line):
                glyph=line[i]
                if glyph['c'] in SUP_DIGITS:
                    first=i
                    digits=''
                    while i<len(line) and line[i]['c'] in SUP_DIGITS:
                        digits+=SUP_DIGITS[line[i]['c']];i+=1
                    if int(digits)==next_anchor:
                        body.append(dict(glyph,c='',anchor=f'note:{note_map[int(digits)]}'))
                        next_anchor+=1
                    else:
                        # A literal mathematical superscript such as a² is text.
                        # An out-of-sequence footnote will remain visible as a diff.
                        body.extend(line[first:i])
                    continue
                body.append(glyph);i+=1
            add_line(streams['body'],body)
    if next_anchor!=143:raise ValueError(f'Expected 142 ordered anchors; found {next_anchor-1}')
    return dict(streams),excluded


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    blocks=markdown_blocks(ROOT/'source/manuscript.md')
    expected,note_map,changes=reference(blocks)
    inventory=[]
    with pymupdf.open(ROOT/'book.pdf') as doc:
        actual,excluded=rendered(doc,pdf_lines(doc,inventory,infer_spaces=True),note_map,blocks)
    comparisons=compare('Markdown + two scan-evidenced markers -> PDF',expected,actual,
                        book=True,check_emphasis=False)
    for result in comparisons:
        key=result['stream']
        left=canonical(expected.get(key,[]))
        right=canonical(actual.get(key,[]),reference=left['text'],hyphen_context_ignore_case=True)
        result['case_insensitive_text_equal']=left['text'].lower()==right['text'].lower()
        result['case_only_changes']=[]
        if result['case_insensitive_text_equal']:
            for i,(a,b) in enumerate(zip(left['text'],right['text'])):
                if a!=b:
                    if result['case_only_changes'] and result['case_only_changes'][-1]['end']==i:
                        row=result['case_only_changes'][-1];row['end']+=1;row['original']+=a;row['printed']+=b
                    else:
                        result['case_only_changes'].append({'start':i,'end':i+1,'original':a,'printed':b,
                            'context':left['text'][max(0,i-35):i+65],
                            'markdown_location':left['locations'][i], 'pdf_location':right['locations'][i]})
            # Also locate footnote attachment after case-only differences; lengths are unchanged.
        if not result['case_insensitive_text_equal']:
            print('WORDING/PUNCTUATION FINDING',key,'regions',len(result['differences']))
    lower_expected={k:[dict(g,c=g['c'].lower()) for g in v] for k,v in expected.items()}
    lower_actual={k:[dict(g,c=g['c'].lower()) for g in v] for k,v in actual.items()}
    layout_checks=compare('diagnostic only: word boundaries and attachment ignoring case',
                          lower_expected,lower_actual,book=True,check_emphasis=False)
    report={'status':'REVIEW_REQUIRED',
            'scope':'Case-preserving text, word boundaries, and note identity/attachment; emphasis remains unverified.',
            'source_markdown_sha256':sha(ROOT/'source/manuscript.md'),
            'book_sha256':sha(ROOT/'book.pdf'),'comparisons':comparisons,
            'explicit_typographic_and_structural_transforms':changes,
            'rendered_to_original_note_map':note_map,'excluded':excluded,
            'case_insensitive_layout_checks':layout_checks,
            'limitations':['Markdown has not been certified against the scan.',
                           'Case-insensitive equality is diagnostic only; strict comparison preserves case.',
                           'Per-character emphasis and original front matter still require separate review.']}
    (OUT/'pdf-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'book-glyphs.jsonl').open('w') as handle:
        for row in inventory:handle.write(json.dumps(row,ensure_ascii=False)+'\n')
    print('REVIEW_REQUIRED:',len(comparisons),'streams;',
          sum(c['case_insensitive_text_equal'] for c in comparisons),'equal ignoring case;',
          sum(c['anchors_equal'] for c in comparisons),'with matching anchors')
    print('Case-insensitive layout checks:',sum(c['passed'] for c in layout_checks),'/',len(layout_checks))
    raise SystemExit(1)


if __name__=='__main__':main()
