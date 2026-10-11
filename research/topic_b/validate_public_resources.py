"""Check identifiers, split overlap and empty text in already cached BEIR ZIPs."""
import csv
import io
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def inspect(name):
    with zipfile.ZipFile(ROOT / '.local/topic_b' / (name + '.zip')) as archive:
        corpus = [json.loads(line) for line in archive.read(name + '/corpus.jsonl').decode().splitlines() if line.strip()]
        queries = [json.loads(line) for line in archive.read(name + '/queries.jsonl').decode().splitlines() if line.strip()]
        doc_ids = {str(d['_id']) for d in corpus}
        query_ids = {str(q['_id']) for q in queries}
        empty_ids = {str(d['_id']) for d in corpus if not (d.get('title', '') + ' ' + d.get('text', '')).strip()}
        qrel_stats, split_queries, empty_relevant = {}, {}, set()
        for path in archive.namelist():
            if '/qrels/' not in path or not path.endswith('.tsv'):
                continue
            split = Path(path).stem
            rows = list(csv.DictReader(io.StringIO(archive.read(path).decode()), delimiter='\t'))
            pairs = {(r['query-id'], r['corpus-id']) for r in rows}
            split_queries[split] = {r['query-id'] for r in rows}
            empty_relevant.update(r['corpus-id'] for r in rows if int(r['score']) > 0 and r['corpus-id'] in empty_ids)
            qrel_stats[split] = {
                'duplicate_pairs': len(rows) - len(pairs),
                'missing_query_ids': sorted({r['query-id'] for r in rows} - query_ids),
                'missing_document_ids': sorted({r['corpus-id'] for r in rows} - doc_ids),
                'positive_qrels_with_empty_text': sum(int(r['score']) > 0 and r['corpus-id'] in empty_ids for r in rows),
            }
        split_names = sorted(split_queries)
        overlaps = {a + '__' + b: len(split_queries[a] & split_queries[b])
                    for i, a in enumerate(split_names) for b in split_names[i + 1:]}
        return {
            'name': name, 'checked_date': '2026-10-10',
            'duplicate_corpus_ids': len(corpus) - len(doc_ids),
            'duplicate_query_ids': len(queries) - len(query_ids),
            'empty_title_and_text_count': len(empty_ids),
            'empty_ids': sorted(empty_ids),
            'empty_documents_in_positive_qrels': sorted(empty_relevant),
            'query_split_overlap_counts': overlaps, 'qrels_checks': qrel_stats,
        }


def main():
    result = [inspect(name) for name in ['fiqa', 'nfcorpus', 'scifact']]
    path = OUT / 'resource_consistency_20261010.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
