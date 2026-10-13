"""Audit the downloaded, revision-pinned GBFR benchmark files, without inference."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.local/topic_a'
OUT = ROOT / 'research/topic_a'

def main():
    manifest = json.loads((OUT/'gbfr_sources_manifest.json').read_text())
    commit = manifest[0]['url'].split('/')[5]
    result = {'repo':'https://github.com/aolaoban/Graph-Bounded_Financial_Reasoning',
              'commit':commit,'date':'2026-10-10',
              'root_license_file_found':False,
              'license_note':'No root license file was found in the inspected checkout at this revision; not an authorization to redistribute.',
              'datasets':{}}
    official = {split: {x['qa']['question'].strip().lower() for x in
                json.loads((CACHE/f'finqa/dataset/{split}.json').read_text())}
                for split in ['train','dev','test']}
    for row in manifest:
        if row['status'] != 'downloaded':
            raise RuntimeError(row)
        raw = (CACHE/row['name']).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        assert sha == row['sha256']
        if not row['name'].endswith('.json'):
            continue
        records = json.loads(raw)
        key=row['name'].removeprefix('gbfr/')
        item={'rows':len(records),'sha256':sha,
              'negative_types':dict(collections.Counter(r['negative_sample_details']['modification_type']
                         for r in records if 'negative_sample_details' in r)),
              'answer_types':dict(collections.Counter(r['answer_type'] for r in records if 'answer_type' in r))}
        if key.startswith('data/FinQA/'):
            questions=[r.get('negative_sample_details',{}).get('original_question',r['question']).strip().lower() for r in records]
            item['parent_question_exact_matches_to_official_splits']={s:sum(q in known for q in questions) for s,known in official.items()}
            item['matching_caveat']='Question-text matching only; duplicate question strings require context/source matching before final deduplication.'
        result['datasets'][key]=item
    (OUT/'gbfr_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print('GBFR hashes and counts verified:',len(result['datasets']),'data files')

if __name__=='__main__':
    main()
