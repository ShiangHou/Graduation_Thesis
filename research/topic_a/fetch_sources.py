"""Fetch public research artifacts, pin GitHub revisions, and record SHA-256.

Only downloads data/text; never runs downloaded code or calls model APIs.
Usage: python3 research/topic_a/fetch_sources.py
       python3 research/topic_a/fetch_sources.py --files research/topic_a/extra_sources.json
"""
import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.local/topic_a'
OUT = ROOT / 'research/topic_a'
REPOS = {
    'finqa': 'czyssrs/FinQA',
    'tatqa': 'NExTplusplus/TAT-QA',
    'verifin': 'verifiedfinance/anon',
    'financebench': 'patronus-ai/financebench',
    'financereasoning': 'BUPT-Reasoning-Lab/FinanceReasoning',
    'numberdiagnosis': 'microsoft/NumberDiagnosis',
    'gbfr': 'aolaoban/Graph-Bounded_Financial_Reasoning',
    'finground': 'bettyguo/FinGround',
    'docmath': 'yale-nlp/DocMath-Eval',
    'tatllm': 'fengbinzhu/TAT-LLM',
}

def fetch(url, limit=160_000_000):
    request = urllib.request.Request(url, headers={'User-Agent': 'ThesisResearchResourceAudit/1.0'})
    with urllib.request.urlopen(request, timeout=55) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Download exceeds size limit')
    return data

def repo_task(item):
    name, repo = item
    try:
        meta = json.loads(fetch(f'https://api.github.com/repos/{repo}'))
        commit = json.loads(fetch(f'https://api.github.com/repos/{repo}/commits/{meta["default_branch"]}'))
        sha = commit['sha']
        tree = json.loads(fetch(f'https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1'))
        (CACHE / f'{name}_tree.json').write_text(json.dumps(tree, indent=2))
        paths = [x['path'] for x in tree.get('tree', []) if x['type'] == 'blob']
        return name, {'repo': repo, 'commit': sha, 'commit_date': commit['commit']['committer']['date'],
                      'license': meta.get('license'), 'tree_truncated': tree.get('truncated'), 'files': paths}
    except Exception as exc:
        return name, {'repo': repo, 'error': str(exc)}

def file_task(item):
    name, url = item['name'], item['url']
    dest = CACHE / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = {'name': name, 'url': url, 'checked_date': '2026-10-10'}
    try:
        raw = None
        cached = Path(item['cached_path']) if item.get('cached_path') else None
        if cached and cached.is_file() and item.get('git_blob_sha'):
            old = cached.read_bytes()
            blob_sha = hashlib.sha1(b'blob ' + str(len(old)).encode() + b'\0' + old).hexdigest()
            if blob_sha == item['git_blob_sha']:
                raw = old
                result['cache_verified_against_pinned_git_blob'] = blob_sha
        if raw is None:
            raw = fetch(url)
        dest.write_bytes(raw)
        result.update(status='downloaded', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    except Exception as exc:
        result.update(status='failed', error=str(exc))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--files', type=Path)
    parser.add_argument('--only', nargs='*', help='Repository names to refresh')
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    if args.files:
        items = json.loads(args.files.read_text())
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(file_task, items))
        target = OUT / (args.files.stem + '_manifest.json')
        target.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        for row in results:
            print(row['name'], row['status'], row.get('bytes', row.get('error')))
    else:
        target = OUT / 'repository_inventory.json'
        results = json.loads(target.read_text()) if target.exists() else {}
        selected = {k: v for k, v in REPOS.items() if args.only is None or k in args.only}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            attempts = dict(pool.map(repo_task, selected.items()))
        (OUT / 'repository_refresh_attempt.json').write_text(json.dumps(attempts, indent=2))
        for name, result in attempts.items():
            if 'error' not in result or 'commit' not in results.get(name, {}):
                results[name] = result
        (OUT / 'repository_inventory.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
        for name, row in results.items():
            print(name, row.get('commit', row.get('error')), len(row.get('files', [])))

if __name__ == '__main__':
    main()
