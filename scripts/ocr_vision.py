#!/usr/bin/env python3
"""Run the second, local recognition engine on the independently rendered scan."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    binary = args.binary.resolve()
    directory = ROOT / 'build/fidelity/ocr'
    images = sorted(directory.glob('page-???.png'))
    if len(images) != 121:
        raise SystemExit('First finish rendering/OCR of all 121 source pages.')

    def run(path):
        output = path.with_suffix('.vision.json')
        provenance = {'image_sha256': sha(path), 'binary_sha256': sha(binary)}
        if output.exists():
            if json.loads(output.read_text()).get('provenance') != provenance:
                raise RuntimeError(f'Stale recognition: {output}')
            return path.stem, 'cached'
        result = subprocess.run([str(binary), str(path)], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if not data['observations']:
            raise RuntimeError(f'No recognized text: {path}')
        data['provenance'] = provenance
        output.write_text(json.dumps(data, indent=2) + '\n')
        return path.stem, 'recognized'

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(run, path) for path in images]
        for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
            page, state = future.result()
            print(f'{n}/{len(images)}: {page} {state}', flush=True)


if __name__ == '__main__':
    main()
