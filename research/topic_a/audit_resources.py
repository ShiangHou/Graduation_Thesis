"""Reproducible dataset/evaluator checks. No model inference or API calls.

Run with a Python environment containing numpy, pandas, scipy, sympy, tqdm.
Official evaluator sources must first be fetched with fetch_sources.py.
"""
import collections
import csv
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.local/topic_a'
OUT = ROOT / 'research/topic_a'

def read(name):
    path = CACHE / name
    if path.suffix == '.jsonl':
        return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    return json.loads(path.read_text())

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(CACHE / path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    result = {'date': '2026-10-10', 'kind': 'DATA_AND_EVALUATOR_AUDIT_NOT_MODEL_RESULTS',
              'python': platform.python_version(), 'finqa': {}, 'tatqa': {}}
    fin_eval = module('fin_eval', 'finqa/code/evaluate/evaluate.py')
    sys.path.insert(0, str(CACHE / 'tatqa'))
    tat_eval = module('tat_eval', 'tatqa/tatqa_metric.py')
    group_sets = {}
    for split in ['train', 'dev', 'test']:
        data = read(f'finqa/dataset/{split}.json')
        mismatches, invalid = [], []
        for row in data:
            flag, value = fin_eval.eval_program(fin_eval.program_tokenization(row['qa']['program']), row['table'])
            if flag:
                invalid.append(row['id'])
            if flag or value != row['qa']['exe_ans']:
                mismatches.append({'id': row['id'], 'computed': value, 'gold': row['qa']['exe_ans'],
                                   'program': row['qa']['program'], 'invalid': bool(flag)})
        group_sets[split] = {level: set(key(r) for r in data) for level, key in {
            'page': lambda r: r['filename'],
            'report_company_year': lambda r: '/'.join(r['filename'].split('/')[:2]),
            'company': lambda r: r['filename'].split('/')[0]}.items()}
        result['finqa'][split] = {'questions': len(data), 'groups': {k: len(v) for k,v in group_sets[split].items()},
          'with_nonempty_gold_inds': sum(bool(r['qa'].get('gold_inds')) for r in data),
          'roundtrip_exact_matches': len(data)-len(mismatches), 'invalid_programs': len(invalid),
          'roundtrip_mismatches': mismatches}
    result['finqa']['split_group_intersections'] = {
        f'{a}__{b}': {k: len(group_sets[a][k] & group_sets[b][k]) for k in group_sets[a]}
        for a,b in [('train','dev'),('train','test'),('dev','test')]}
    tat_sets = {}
    for split in ['train', 'dev', 'test_gold']:
        data = read(f'tatqa/dataset_raw/tatqa_dataset_{split}.json')
        qs = [q for r in data for q in r['questions']]
        metric = tat_eval.TaTQAEmAndF1()
        for q in qs:
            answer = q['answer'] if isinstance(q['answer'],list) else str(q['answer'])
            metric(q, answer, q.get('scale',''))
        tat_sets[split] = {r['table']['uid'] for r in data}
        result['tatqa'][split] = {'contexts': len(data), 'questions': len(qs),
           'answer_types': dict(collections.Counter(q.get('answer_type') for q in qs)),
           'with_nonempty_mapping': sum(bool(q.get('mapping')) for q in qs),
           'with_nonempty_facts': sum(bool(q.get('facts')) for q in qs),
           'with_nonempty_derivation': sum(bool(q.get('derivation')) for q in qs),
           'gold_self_score_em_f1_scale_op': metric.get_overall_metric()}
    result['tatqa']['table_uid_intersections'] = {f'{a}__{b}':len(tat_sets[a]&tat_sets[b])
        for a,b in [('train','dev'),('train','test_gold'),('dev','test_gold')]}
    for split in ['train','dev']:
        data = read(f'tatqa/dataset_tagop/tatqa_dataset_{split}.json')
        qs = [q for r in data for q in r['questions']]
        arithmetic = [q for q in qs if q.get('answer_type') == 'arithmetic']
        result['tatqa']['tagop_'+split] = {'questions':len(qs),'arithmetic_questions':len(arithmetic),
            'with_nonempty_mapping':sum(bool(q.get('mapping')) for q in qs),
            'arithmetic_with_mapping':sum(bool(q.get('mapping')) for q in arithmetic),
            'with_nonempty_facts':sum(bool(q.get('facts')) for q in qs),
            'field_presence':dict(collections.Counter(k for q in qs for k in q))}
        if split == 'train':
            # Exact cell text duplicates, deliberately not a semantic ambiguity estimate.
            mapped, duplicate = 0,0
            for r in data:
                counts = collections.Counter(str(c).strip() for row in r['table']['table'] for c in row if str(c).strip())
                for q in r['questions']:
                    if q.get('answer_type') != 'arithmetic':
                        continue
                    cells = q.get('mapping',{}).get('table',[])
                    if cells:
                        mapped += 1
                        duplicate += any(counts[str(r['table']['table'][i][j]).strip()]>1 for i,j in cells)
            result['tatqa']['tagop_train']['arithmetic_with_table_mapping'] = mapped
            result['tatqa']['tagop_train']['mapped_arithmetic_with_exact_duplicate_cell_text'] = duplicate
    result['financereasoning'] = {}
    for split in ['easy','medium','hard']:
        data = read(f'financereasoning/data/FinanceReasoning/{split}.json')
        result['financereasoning'][split] = {'questions':len(data),
            'source_prefixes':dict(collections.Counter(r.get('source','').rsplit('-',1)[0] for r in data))}
    result['financebench'] = {'questions':len(read('financebench/data/financebench_open_source.jsonl'))}
    for model in ['gpt-4_oracle','gpt-4-1106-preview_oracle']:
        data = read(f'financebench/results/{model}.jsonl')
        result['financebench'][model+'_released_labels'] = dict(collections.Counter(r.get('label') for r in data))
    result['verifin_published_counts_reexpressed'] = []
    with (CACHE / 'verifin/results/paper_metrics.csv').open() as f:
        for row in csv.DictReader(f):
            if not all(row[k] for k in ['n','TA','FA','TR','FR','AB']):
                continue  # Release includes unpopulated run placeholders.
            n,ta,fa,tr,fr,ab = (int(row[k]) for k in ['n','TA','FA','TR','FR','AB'])
            assert n == ta+fa+tr+fr+ab
            result['verifin_published_counts_reexpressed'].append({
                'dataset':row['dataset'],'run':row['run'],'n':n,'accepts':ta+fa,
                'answer_coverage':(ta+fa)/n,'decision_coverage':(n-ab)/n,
                'accepted_error_rate':fa/(ta+fa) if ta+fa else None})
    result['input_hash_check'] = []
    for manifest in ['data_sources_manifest.json']:
        for row in json.loads((OUT / manifest).read_text()):
            if row['status']=='downloaded':
                actual=hashlib.sha256((CACHE/row['name']).read_bytes()).hexdigest()
                assert actual==row['sha256'],row['name']
                result['input_hash_check'].append(row['name'])
    (OUT/'resource_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['input_hash_check','verifin_published_counts_reexpressed']},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
