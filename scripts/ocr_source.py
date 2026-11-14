#!/usr/bin/env python3
"""Independent, resumable OCR of the scan. Never reads the existing transcription."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--pages', help='Inclusive PDF page range, e.g. 1-10')
    parser.add_argument('--profile', choices=['default', 'sauvola'], default='default')
    args = parser.parse_args()
    source = ROOT / 'source/original-1957-typescript-scan.pdf'
    output = ROOT / ('build/fidelity/ocr' if args.profile == 'default' else 'build/fidelity/ocr-sauvola')
    output.mkdir(parents=True, exist_ok=True)
    config = {
        'source_sha256': digest(source), 'dpi': 300,
        'pymupdf': pymupdf.VersionBind,
        'tesseract': subprocess.check_output(['tesseract', '--version'], text=True).splitlines()[0],
        'options': ['-l', 'eng', '--psm', '3', '-c', 'load_system_dawg=0',
                    '-c', 'load_freq_dawg=0', 'txt', 'tsv'],
    }
    if args.profile == 'sauvola':
        config['options'] = ['-l', 'eng', '--psm', '6', '-c', 'thresholding_method=2', 'txt', 'tsv']
    tessdata = Path(subprocess.check_output(['brew', '--prefix'], text=True).strip()) / 'share/tessdata/eng.traineddata'
    config['english_model_sha256'] = digest(tessdata)
    manifest = output / 'configuration.json'
    if manifest.exists() and json.loads(manifest.read_text()) != config:
        raise SystemExit('OCR configuration changed; archive/remove the existing output before re-running.')
    manifest.write_text(json.dumps(config, indent=2) + '\n')
    with pymupdf.open(source) as doc:
        count = len(doc)
    start, end = map(int, args.pages.split('-')) if args.pages else (1, count)
    if not (1 <= start <= end <= count):
        parser.error('Invalid PDF page range')

    def recognize(number):
        base = output / f'page-{number:03d}'
        marker = base.with_suffix('.complete.json')
        if marker.exists():
            data = json.loads(marker.read_text())
            if all(digest(base.with_suffix(ext)) == expected for ext, expected in data.items()):
                return number, 'cached'
            raise RuntimeError(f'Cached OCR page {number} changed')
        original = ROOT / 'build/fidelity/ocr' / f'page-{number:03d}.png'
        if args.profile == 'sauvola' and original.exists():
            if not base.with_suffix('.png').exists():
                base.with_suffix('.png').symlink_to(Path('../ocr') / original.name)
        else:
            with pymupdf.open(source) as doc:
                doc[number - 1].get_pixmap(dpi=config['dpi'], colorspace=pymupdf.csGRAY).save(base.with_suffix('.png'))
        env = dict(os.environ, OMP_THREAD_LIMIT='1')
        result = subprocess.run(['tesseract', str(base.with_suffix('.png')), str(base),
                                 *config['options']], env=env, capture_output=True, text=True, check=True)
        base.with_suffix('.stderr.txt').write_text(result.stderr)
        marker.write_text(json.dumps({ext: digest(base.with_suffix(ext))
                                     for ext in ('.png', '.txt', '.tsv')}, indent=2) + '\n')
        return number, 'recognized'

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(recognize, p) for p in range(start, end + 1)]
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            number, status = future.result()
            print(f'{done}/{end-start+1}: PDF page {number} {status}', flush=True)


if __name__ == '__main__':
    main()
