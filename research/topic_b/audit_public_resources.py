"""Download and inspect small public BEIR resources; never run downloaded code.

Usage: python3 Graduation_Thesis/research/topic_b/audit_public_resources.py
Archives are cached under Graduation_Thesis/.local/topic_b; audit is JSON.
"""
import concurrent.futures
import csv
import hashlib
import io
import json
import statistics
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.local/topic_b'
OUT = Path(__file__).resolve().parent
BASE = 'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/'

def quantiles(values):
    values = sorted(values)
    return {'min': values[0], 'median': statistics.median(values),
            'p90': values[int(.90 * (len(values)-1))],
            'p95': values[int(.95 * (len(values)-1))], 'max': values[-1]}

def inspect(name):
    url = BASE + name + '.zip'
    row = {'name': name, 'url': url, 'checked_date': '2026-10-10'}
    dest = CACHE / (name + '.zip')
    try:
        if dest.exists():
            raw = dest.read_bytes()
            row['download_status'] = 'cached'
        else:
            req = urllib.request.Request(url, headers={'User-Agent': 'ThesisResourceAudit/1.0'})
            with urllib.request.urlopen(req, timeout=50) as response:
                row['http_status'] = response.status
                raw = response.read(60_000_001)
            if len(raw) > 60_000_000:
                raise ValueError('archive exceeds 60 MB audit limit')
            dest.write_bytes(raw)
            row['download_status'] = 'downloaded'
        row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            counts = {}
            lengths = []
            for path in archive.namelist():
                if path.endswith('.jsonl'):
                    n = 0
                    fields = None
                    for line in archive.read(path).decode('utf-8').splitlines():
                        if not line.strip():
                            continue
                        item = json.loads(line)
                        n += 1
                        fields = fields or sorted(item)
                        if path.endswith('/corpus.jsonl'):
                            text = (item.get('title', '') + ' ' + item.get('text', '')).strip()
                            lengths.append(len(text))
                    counts[path] = {'rows': n, 'fields': fields}
                elif path.endswith('.tsv'):
                    rows = list(csv.DictReader(io.StringIO(archive.read(path).decode('utf-8')), delimiter='\t'))
                    queries = {}
                    grades = {}
                    for item in rows:
                        grade = int(item['score'])
                        grades[str(grade)] = grades.get(str(grade), 0) + 1
                        if grade > 0:
                            qid = item['query-id']
                            queries[qid] = queries.get(qid, 0) + 1
                    counts[path] = {'rows': len(rows), 'query_count': len({r['query-id'] for r in rows}),
                                    'grades': grades, 'mean_positive_per_query': statistics.mean(queries.values()),
                                    'positive_count_quantiles': quantiles(list(queries.values()))}
            row['inspection'] = counts
            row['corpus_characters_quantiles'] = quantiles(lengths)
            row['corpus_characters_mean'] = statistics.mean(lengths)
        row['status'] = 'parsed_and_counted'
    except Exception as exc:
        row.update(status='failed', error=str(exc))
    return row

def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(inspect, ['fiqa', 'scifact', 'nfcorpus']))
    path = OUT / 'resource_audit_20261010.json'
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
