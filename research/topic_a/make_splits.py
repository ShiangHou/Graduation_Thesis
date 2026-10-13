"""Create deterministic proposed splits without exposing gold labels to inference.

The stage assignment only uses group identifiers. These are proposed experimental
splits, not trained model results. Official dev is reserved for calibration.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'.local/topic_a'
OUT=ROOT/'research/topic_a'
SEED='topic-a-20261010-v1'

def assign(groups):
    ordered=sorted(set(groups),key=lambda x:hashlib.sha256((SEED+'|'+x).encode()).hexdigest())
    n=len(ordered)
    cuts=[0,int(.6*n),int(.8*n),int(.9*n),n]
    names=['generator_or_binding_train','selector_train','method_tune','binding_diagnostic_test']
    return {g:names[i] for i in range(4) for g in ordered[cuts[i]:cuts[i+1]]}

def main():
    rows=[]
    fin=json.loads((CACHE/'finqa/dataset/train.json').read_text())
    groups=assign('/'.join(x['filename'].split('/')[:2]) for x in fin)
    for x in fin:
        group='/'.join(x['filename'].split('/')[:2])
        rows.append(dict(dataset='finqa',id=x['id'],group=group,stage=groups[group],answer_type='program'))
    tat=json.loads((CACHE/'tatqa/dataset_raw/tatqa_dataset_train.json').read_text())
    groups=assign(x['table']['uid'] for x in tat)
    for x in tat:
        group=x['table']['uid']
        rows.extend(dict(dataset='tatqa',id=q['uid'],group=group,stage=groups[group],answer_type=q['answer_type']) for q in x['questions'])
    summary={'seed':SEED,'rule':'hash-sort groups, boundaries floor(0.6*n), floor(0.8*n), floor(0.9*n)',
      'official_dev':'calibration only','official_test':'final answer evaluation only',
      'caveat':'FinQA official dev/test share report groups with train; no report independence claim.', 'counts':{}}
    for d in ['finqa','tatqa']:
        summary['counts'][d]={}
        for s in sorted({r['stage'] for r in rows}):
            part=[r for r in rows if r['dataset']==d and r['stage']==s]
            summary['counts'][d][s]={'questions':len(part),'groups':len({r['group']for r in part}),
              'answer_types':dict(Counter(r['answer_type']for r in part))}
        # A group belongs to exactly one stage; every id is unique within a dataset.
        assert len({r['id']for r in rows if r['dataset']==d})==sum(r['dataset']==d for r in rows)
        for group in {r['group']for r in rows if r['dataset']==d}:
            assert len({r['stage']for r in rows if r['dataset']==d and r['group']==group})==1
    (OUT/'split_manifest.json').write_text(json.dumps({'seed':SEED,'items':rows},ensure_ascii=False,indent=2))
    (OUT/'split_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
