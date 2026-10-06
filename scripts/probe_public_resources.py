"""Read-only small public-resource feasibility probe. No model API calls."""
import hashlib
import json
import urllib.request
from pathlib import Path
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local' / 'public_probe'
OUT.mkdir(parents=True, exist_ok=True)
SOURCES = [
    ('financebench', 'https://raw.githubusercontent.com/patronus-ai/financebench/main/data/financebench_open_source.jsonl', 'financebench.jsonl'),
    ('fund_quarterly_report', 'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-04-22/562590_20260422_R75K.pdf', 'fund_quarterly.pdf'),
    ('fund_prospectus', 'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2026-01-23/562820_20260123_W2AC.pdf', 'fund_prospectus.pdf'),
]
results = []
for name, url, filename in SOURCES:
    result = {'resource': name, 'url': url, 'checked_date': '2026-10-06'}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Academic feasibility check'})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(20_000_000)
            result['http_status'] = response.status
        path = OUT / filename
        path.write_bytes(raw)
        result.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if filename.endswith('.jsonl'):
            rows = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
            result['rows'] = len(rows)
            result['first_record_fields'] = list(rows[0])
            result['all_have_evidence'] = all(bool(row.get('evidence')) for row in rows)
        else:
            reader = PdfReader(path)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            text = text.encode('utf-8', errors='replace').decode('utf-8')
            (OUT / (path.stem + '.txt')).write_text(text)
            result['pages'] = len(reader.pages)
            result['extractable_characters'] = len(text)
            result['field_presence'] = {field: field in text for field in ['基金主代码', '投资目标', '业绩比较基准', '投资组合', '占基金资产净值比例', '标的指数']}
        result['status'] = 'verified'
    except Exception as exc:
        result.update(status='failed', error=str(exc))
    results.append(result)
    print(json.dumps(result, ensure_ascii=False))
(ROOT / 'research' / 'public_resource_probe.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
