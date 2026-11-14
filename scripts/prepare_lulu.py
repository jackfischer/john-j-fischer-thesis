#!/usr/bin/env python3
"""Add white bleed to the 6x9 interior and verify the complete print export.

Requires requirements-audit.txt. Page content stays vector; original raster
images are neither resampled nor recompressed. This is not a PDF/X conversion
or a substitute for reviewing Lulu's processed PDF and a physical proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import pymupdf
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
TRIM = pymupdf.Rect(0, 0, 432, 648)
MEDIA = pymupdf.Rect(0, 0, 450, 666)
INSET = pymupdf.Rect(9, 9, 441, 657)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(a, b):
    return all(abs(x-y) < .02 for x,y in zip(a,b))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def glyphs(page):
    return [(char['c'],span['font'],span['size'],span['color'],char['bbox'])
            for block in page.get_text('rawdict')['blocks']
            for line in block.get('lines',[]) for span in line['spans'] for char in span['chars']]


def inventory(doc):
    fonts = {}
    images = []
    min_safety = 1000
    min_gutter = 1000
    for number, page in enumerate(doc, 1):
        for font in page.get_fonts(full=True):
            xref, _, kind, name = font[:4]
            require(xref > 0 and bool(doc.extract_font(xref)[3]), f'Unembedded font: {name}')
            require(kind != 'Type3', f'Bitmap/Type3 font requires review: {name}')
            fonts[name] = kind
        bounds = []
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                bounds.extend(pymupdf.Rect(s['bbox']) for s in line['spans'] if s['text'].strip())
        for im in page.get_image_info(hashes=True):
            box = pymupdf.Rect(im['bbox'])
            xppi, yppi = im['width']*72/box.width, im['height']*72/box.height
            require(min(xppi,yppi) >= 299.5, f'Image below 300 ppi on page {number}: {xppi:.1f}, {yppi:.1f}')
            images.append({'page':number, 'pixels':[im['width'],im['height']],
                           'ppi':[round(xppi,2),round(yppi,2)], 'pixel_md5':im['digest'].hex()})
            bounds.append(box)
        for box in bounds:
            safety = min(box.x0,box.y0,432-box.x1,648-box.y1)
            gutter = box.x0 if number % 2 else 432-box.x1
            min_safety, min_gutter = min(min_safety,safety), min(min_gutter,gutter)
            require(safety >= 36-.1, f'Content outside half-inch trim safety: page {number}, {box}')
            require(gutter >= 50.4-.1, f'Content inside .70-inch gutter safety: page {number}, {box}')
    # These interiors use opaque text and images. Reject transparency rather
    # than silently flattening it or rasterizing the typography.
    for xref in range(1, doc.xref_length()):
        obj = doc.xref_object(xref)
        require(not re.search(r'/SMask\s+(?!/None\b)\S+',obj), f'Soft mask requires flattening: object {xref}')
        require(not re.search(r'/S\s*/Transparency\b',obj), f'Transparency group requires review: object {xref}')
        for opacity in re.findall(r'/(?:ca|CA)\s+([\d.]+)',obj):
            require(float(opacity)==1, f'Transparent object requires flattening: {xref}')
        for blend in re.findall(r'/BM\s*/(\w+)',obj):
            require(blend in ('Normal','Compatible'), f'Blend mode requires flattening: {xref}')
    return {'embedded_fonts':fonts, 'images':images,
            'minimum_content_safety_inches':round(min_safety/72,3),
            'minimum_inner_content_margin_inches':round(min_gutter/72,3),
            'transparency':'No soft masks, transparency groups, non-opaque alpha, or non-normal blend modes.'}


def prepare(source, target, report_path):
    with pymupdf.open(source) as src:
        require(not src.is_encrypted, 'Encrypted source PDF')
        require(len(src)%2==0, 'Interior must end on an even page; add an intentional blank in LaTeX')
        for i,p in enumerate(src,1):
            require(close(p.rect,TRIM) and p.rotation==0, f'Unexpected source size/rotation: page {i}')
        contents = inventory(src)
        out = pymupdf.open()
        for i,p in enumerate(src):
            q = out.new_page(width=450,height=666)
            if p.get_contents():
                q.show_pdf_page(INSET,src,i)
            q.set_trimbox(INSET)
            q.set_bleedbox(MEDIA)
        metadata = dict(src.metadata)
        metadata['producer'] = f'LuaLaTeX; PyMuPDF {pymupdf.VersionBind} white-bleed export'
        out.set_metadata(metadata)
        out.set_page_labels(src.get_page_labels())
        out.set_toc(src.get_toc())
        out.save(target,garbage=4,deflate=True)
        out.close()
        with pymupdf.open(target) as printed:
            require(not printed.is_encrypted and len(src)==len(printed), 'Page count/security changed')
            pixel_checks = []
            antialiasing_differences = []
            maximum_glyph_position_error = 0
            for i,(p,q) in enumerate(zip(src,printed),1):
                require(close(q.mediabox,MEDIA) and close(q.cropbox,MEDIA), f'Incorrect media/crop box: {i}')
                require(close(q.trimbox,INSET) and close(q.bleedbox,MEDIA), f'Incorrect trim/bleed box: {i}')
                require(not list(q.annots() or []) and not q.get_links() and not list(q.widgets() or []), f'Interactive annotation: {i}')
                original = p.get_pixmap(matrix=pymupdf.Matrix(2,2),alpha=False,annots=False)
                result = q.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=INSET,alpha=False,annots=False)
                require(original.width==result.width and original.height==result.height, f'Raster dimensions differ: {i}')
                if original.samples != result.samples:
                    # Translating vector glyphs by exactly 9pt can cross a
                    # floating-point rasterizer rounding boundary. Permit only
                    # tiny edge-antialias changes, with exact text/image checks
                    # and sub-.001pt glyph-position agreement below.
                    diff = ImageChops.difference(
                        Image.frombytes('RGB',(original.width,original.height),original.samples),
                        Image.frombytes('RGB',(result.width,result.height),result.samples))
                    histogram = diff.histogram()
                    changed = sum(count for value,count in enumerate(histogram) if value%256)
                    maximum = max(hi for lo,hi in diff.getextrema())
                    require(changed/(original.width*original.height*3) < .0001 and maximum<=80,
                            f'Trimmed render differs beyond edge-antialias tolerance: {i}')
                    antialiasing_differences.append({'page':i,'changed_rgb_components':changed,
                        'total_rgb_components':original.width*original.height*3,'maximum_channel_difference':maximum,
                        'bbox_144dpi':diff.getbbox()})
                require(p.get_text()==q.get_text(), f'Extracted text changed: {i}')
                aa,bb = glyphs(p),glyphs(q)
                require(len(aa)==len(bb), f'Glyph count changed: {i}')
                for a,b in zip(aa,bb):
                    require(a[:2]==b[:2] and abs(a[2]-b[2])<.001 and a[3]==b[3], f'Glyph text/font/size/color changed: {i}')
                    error = max(abs(right-left-9) for left,right in zip(a[4],b[4]))
                    maximum_glyph_position_error = max(maximum_glyph_position_error,error)
                    require(error<.001, f'Glyph position changed: {i}')
                before = [(im['width'],im['height'],im['digest']) for im in p.get_image_info(hashes=True)]
                after = [(im['width'],im['height'],im['digest']) for im in q.get_image_info(hashes=True)]
                require(before==after, f'Image pixels changed: {i}')
                for font in q.get_fonts(full=True):
                    require(bool(printed.extract_font(font[0])[3]), f'Export font unembedded: {font[3]}')
                pixel_checks.append(hashlib.sha256(original.samples).hexdigest())
            report = {'status':'PASS','source':{'path':source.name,'sha256':digest(source)},
                      'output':{'path':target.name,'sha256':digest(target)},'pages':len(src),
                      'trim_inches':[6,9],'upload_inches':[6.25,9.25],'white_bleed_inches':.125,
                      'exact_144dpi_trim_render_pages':len(src)-len(antialiasing_differences),
                      'edge_antialiasing_differences_144dpi':antialiasing_differences,
                      'maximum_glyph_position_error_points':maximum_glyph_position_error,
                      'every_page_text_and_image_pixels_identical':True,
                      'page_render_sha256':pixel_checks, **contents,
                      'remaining_physical_checks':['Lulu processed-PDF review','Physical hardcover proof'],
                      'specification':'https://help.lulu.com/en/support/solutions/articles/64000255519-pdf-creation-settings'}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: {target.name}; {report["pages"]} pages; text and image pixels identical; glyph positions within .001pt')
    print(f'144dpi renders: {report["exact_144dpi_trim_render_pages"]} exact; {len(antialiasing_differences)} with tiny edge-antialias differences (recorded).')
    print(f'Fonts embedded; images >=300 ppi; safety >=0.50in; inner content margin >=0.70in. Report: {report_path}')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'book.pdf')
    parser.add_argument('--output',type=Path,default=ROOT/'book-lulu.pdf')
    parser.add_argument('--report',type=Path,default=ROOT/'build/print/preflight.json')
    args = parser.parse_args()
    require(args.source.resolve()!=args.output.resolve(), 'Source and output must differ')
    prepare(args.source,args.output,args.report)
