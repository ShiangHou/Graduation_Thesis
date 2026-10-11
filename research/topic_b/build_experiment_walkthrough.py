"""Build one real-data walkthrough and hand-checkable metric fixtures.

No network, LLM calls, training, or benchmark-wide evaluation. BM25 here is an
explicit pedagogical implementation, not a reproduction of a published run.
"""
import collections
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name('experiment_walkthrough')


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def metrics(ranking, gold, pool, k=20):
    if len(ranking) != len(set(ranking)):
        raise ValueError('duplicate IDs: evaluate structure before ranking')
    if not set(ranking).issubset(set(pool)):
        raise ValueError('out-of-pool ID')
    relevant = {d for d, grade in gold.items() if grade > 0}
    if not relevant:
        raise ValueError('no positive qrels: predeclare a separate policy')
    head = ranking[:k]
    dcg = sum(gold.get(d, 0) / math.log2(i + 2) for i, d in enumerate(head))
    ideal = sum(g / math.log2(i + 2)
                for i, g in enumerate(sorted(gold.values(), reverse=True)[:k]))
    hit = len(set(head) & relevant)
    in_pool = relevant & set(pool)
    pool_grades = sorted((gold[d] for d in in_pool), reverse=True)[:k]
    pool_ideal = sum(g / math.log2(i + 2) for i, g in enumerate(pool_grades))
    return {
        'ndcg_at_20': dcg / ideal,
        'recall_at_20': hit / len(relevant),
        'precision_at_20': hit / k,
        'rr_at_20': next((1 / (i + 1) for i, d in enumerate(head) if d in relevant), 0),
        'pool_recall': len(in_pool) / len(relevant),
        'conditional_pool_recall_at_20': hit / len(in_pool) if in_pool else None,
        'conditional_pool_ndcg_at_20': dcg / pool_ideal if pool_ideal else None,
    }


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    OUT.mkdir(exist_ok=True)
    archive = ROOT / '.local/topic_b/fiqa.zip'
    with zipfile.ZipFile(archive) as z:
        corpus = [json.loads(line) for line in z.read('fiqa/corpus.jsonl').splitlines()]
        queries = {r['_id']: r for r in map(json.loads, z.read('fiqa/queries.jsonl').splitlines())}
        rows = list(csv.DictReader(io.StringIO(z.read('fiqa/qrels/test.tsv').decode()), delimiter='\t'))
    qid = '8'
    gold = {r['corpus-id']: int(r['score']) for r in rows if r['query-id'] == qid}
    qterms = set(tokens(queries[qid]['text']))
    # Length and query-term frequencies are calculated over the entire corpus.
    index, df = [], collections.Counter()
    for d in corpus:
        ts = tokens(d['title'] + ' ' + d['text'])
        tf = collections.Counter(t for t in ts if t in qterms)
        df.update(tf.keys())
        index.append((d['_id'], len(ts), tf))
    avgdl = sum(length for _, length, _ in index) / len(index)
    idf = {t: math.log(1 + (len(index) - df[t] + 0.5) / (df[t] + 0.5)) for t in qterms}
    scored = []
    for did, length, tf in index:
        score = sum(idf[t] * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length / avgdl))
                    for t, count in tf.items())
        scored.append((did, score))
    scored.sort(key=lambda p: (-p[1], p[0]))
    lookup = {d['_id']: d for d in corpus}
    top250 = [d for d, _ in scored[:250]]
    candidate_input = {
        'task_type': 'financial_evidence_reranking',
        'query_id': 'fiqa:8', 'query': queries[qid]['text'],
        'top_k': 20, 'candidate_count': 250,
        'candidates': [{'candidate_id': 'fiqa:' + did,
                        'title': lookup[did]['title'], 'text': lookup[did]['text']}
                       for did in top250],
    }
    save('fiqa_q8_input_top250.json', candidate_input)
    save('fiqa_q8_gold_evaluation_only.json', {
        'query_id': 'fiqa:8', 'qrels': {'fiqa:' + d: g for d, g in gold.items()},
        'usage': 'evaluation only; not part of model input',
        'gold_document_examples': [lookup[d] for d in gold],
    })
    summary = {
        'status': 'one-query illustrative retrieval; no LLM results',
        'fiqa_zip_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'query': queries[qid]['text'], 'corpus_count': len(corpus),
        'retriever': {'type': 'custom BM25', 'k1': 1.2, 'b': 0.75,
                      'tokenizer': 'lowercase regex [a-z0-9]+',
                      'stopwords': False, 'stemming': False,
                      'tie_break': 'lexicographic document ID'},
        'gold_ranks': {did: next(i+1 for i, pair in enumerate(scored) if pair[0] == did) for did in gold},
        'pool_metrics': {str(n): metrics([d for d, _ in scored[:20]], gold,
                                      [d for d, _ in scored[:n]]) for n in [80, 150, 250]},
        'pool_definition': 'prefixes of the same retrieval run; no gold injection',
    }
    save('fiqa_q8_retrieval_summary.json', summary)
    # Synthetic rankings make arithmetic independently checkable.
    ranking = ['U1', 'A', 'U2', 'U3', 'B'] + ['U' + str(i) for i in range(4, 19)]
    fixture_gold = {'A': 1, 'B': 1}
    fixture = {'status': 'synthetic arithmetic example, not model output',
               'ranking': ranking, 'qrels': fixture_gold,
               'metrics': metrics(ranking, fixture_gold, ranking)}
    assert len(ranking) == 20
    assert math.isclose(fixture['metrics']['recall_at_20'], 1.0)
    assert math.isclose(fixture['metrics']['precision_at_20'], 0.1)
    assert math.isclose(fixture['metrics']['rr_at_20'], 0.5)
    ideal_rank = ['A', 'B'] + [d for d in ranking if d not in fixture_gold]
    assert math.isclose(metrics(ideal_rank, fixture_gold, ideal_rank)['ndcg_at_20'], 1.0)
    no_gold = ['X' + str(i) for i in range(20)]
    assert metrics(no_gold, fixture_gold, no_gold)['conditional_pool_recall_at_20'] is None
    save('metric_arithmetic_example.json', fixture)
    report_path = ROOT / '.local/topic_b/findver/financial_reports/NJR-2024-02-06_10-Q.json'
    rows = json.loads((ROOT / '.local/topic_b/findver/testmini.json').read_text())
    record = next(r for r in rows if r['example_id'] == 'ie-val-0')
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    blocks = {r['id']: r for r in report['context']}
    assert len(blocks) == len(report['context'])
    assert set(record['relevant_context']).issubset(blocks)
    save('findver_ie_val_0_aligned_example.json', {
        'status': 'real record with evidence IDs aligned; gold kept for inspection only',
        'record': record, 'report_url': report['url'],
        'report_sha256': hashlib.sha256(report_bytes).hexdigest(),
        'report_candidate_count': len(blocks),
        'evidence_blocks': [blocks[i] for i in record['relevant_context']],
    })
    print(json.dumps({'output_directory': str(OUT), 'gold_ranks': summary['gold_ranks'],
                      'bm25_example_metrics': summary['pool_metrics'],
                      'synthetic_metrics': fixture['metrics'],
                      'findver_blocks': len(blocks)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
