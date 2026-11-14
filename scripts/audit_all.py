#!/usr/bin/env python3
"""Run independent fidelity checks and fail while findings/review remain open."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/fidelity'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    policy = json.loads((ROOT/'audit/source-manifest.json').read_text())
    review = json.loads((ROOT/'audit/review.json').read_text())
    blockers = []
    for category in ('authoritative_source', 'reference_assets'):
        for name, expected in policy.get(category, {}).items():
            if not (ROOT/name).is_file() or digest(ROOT/name) != expected:
                blockers.append(f'Pinned {category} changed or missing: {name}')
    for name, expected in review['observed_inputs'].items():
        if not (ROOT/name).is_file() or digest(ROOT/name) != expected:
            blockers.append(f'Review evidence needs reassessment after input change: {name}')
    for finding in review['findings']:
        for evidence in finding.get('evidence', []):
            path = ROOT/evidence['path']
            if not path.is_file() or digest(path) != evidence['sha256']:
                blockers.append(f'Missing/changed evidence: {finding["id"]} {path.name}')
        if finding['disposition'] not in ('REJECTED_OCR', 'SOURCE_VERIFIED_REPAIR', 'RESOLVED'):
            blockers.append(f'{finding["disposition"]}: {finding["id"]}')
    blockers.extend(review['outstanding_review'])
    results = []
    for name in policy['checks']:
        command = [sys.executable, str(ROOT/'scripts'/name)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        log = OUT/(Path(name).stem+'.log')
        log.write_text(result.stdout+result.stderr)
        results.append({'script':name, 'exit_code':result.returncode,
                        'log':str(log.relative_to(ROOT))})
        print(f'{name}: exit {result.returncode}', flush=True)
        if result.returncode:
            blockers.append(f'Independent check requires attention: {name} (see {log.relative_to(ROOT)})')
    summary = {'status':'REVIEW_REQUIRED' if blockers else 'PASS',
               'scope':'Complete audit gate; individual text checks have narrower scope.',
               'inputs':{name:digest(ROOT/name) for name in review['observed_inputs'] if (ROOT/name).is_file()},
               'checks':results, 'blockers':blockers}
    (OUT/'gate-report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(summary['status'])
    for blocker in blockers:
        print(' -', blocker)
    raise SystemExit(bool(blockers))


if __name__ == '__main__':
    main()
