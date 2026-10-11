"""Read-only checks of the cached FinDVer JSONs; no network or model calls."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.local' / 'topic_b' / 'findver'
AUDIT = Path(__file__).with_name('findver_resource_audit_20261011.json')


def main():
    recorded = json.loads(AUDIT.read_text())
    reports = []
    for info in recorded['files']:
        data = (CACHE / info['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info['sha256']
        rows = json.loads(data)
        assert len(rows) == info['count']
        assert len({r['example_id'] for r in rows}) == len(rows)
        assert all(isinstance(r['entailment_label'], bool) for r in rows)
        standard = sum(bool(r.get('explanation')) for r in rows)
        alternate = sum(bool(r.get('explaination')) for r in rows)
        normalized = sum(bool(r.get('explanation') or r.get('explaination')) for r in rows)
        assert normalized == info['nonempty_explanation_normalized']
        reports.append({r['report'] for r in rows})
        print(json.dumps({
            'file': info['file'], 'rows': len(rows),
            'subsets': dict(collections.Counter(r['subset'] for r in rows)),
            'standard_explanation': standard,
            'alternate_explaination': alternate,
            'normalized_explanation': normalized,
            'unique_reports': len(reports[-1]),
        }, ensure_ascii=False))
    overlap = len(reports[0] & reports[1])
    assert overlap == recorded['overlapping_reports_between_splits']
    print(json.dumps({'overlapping_report_filenames': overlap,
                      'evidence_indices_aligned_to_reports': False,
                      'model_experiments_run': False}))


if __name__ == '__main__':
    main()
