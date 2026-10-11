"""Download public primary-source research data; no external code is executed."""
import json, hashlib, urllib.request, concurrent.futures
from pathlib import Path
BASE=Path(__file__).resolve().parents[3]
OUT=BASE/'.local/topic_b/public_item_chunk'
OUT.mkdir(parents=True,exist_ok=True)
SOURCES={
'finrank.jsonl':'https://raw.githubusercontent.com/datanxt/FinRank/916dc27e77b90e294ea1b3a2cc5b0abcf07392d1/FinRank.jsonl',
'finrank_repair_log.json':'https://raw.githubusercontent.com/datanxt/FinRank/916dc27e77b90e294ea1b3a2cc5b0abcf07392d1/repair_log.json',
'finrank_splits.json':'https://raw.githubusercontent.com/datanxt/FinRank/916dc27e77b90e294ea1b3a2cc5b0abcf07392d1/baselines/splits.json',
'finqa_dev.json':'https://raw.githubusercontent.com/czyssrs/FinQA/0f16e2867befa6840783e58be38c9efb9229d742/dataset/dev.json',
'financerag_tree.json':'https://huggingface.co/api/datasets/Linq-AI-Research/FinanceRAG/tree/main?recursive=true',
'finder_metadata.json':'https://huggingface.co/api/datasets/Linq-AI-Research/FinDER',
'finrank_license.txt':'https://raw.githubusercontent.com/datanxt/FinRank/916dc27e77b90e294ea1b3a2cc5b0abcf07392d1/LICENSE'
}
def fetch(pair):
 name,url=pair;p=OUT/name
 try:
  if not p.exists():
   with urllib.request.urlopen(url,timeout=45) as r: data=r.read(60_000_001)
   if len(data)>60_000_000: raise ValueError('size cap exceeded')
   p.write_bytes(data)
  b=p.read_bytes(); return {'file':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 except Exception as e: return {'file':name,'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: rows=list(ex.map(fetch,SOURCES.items()))
(Path(__file__).parent/'download_audit_20261012.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps(rows,ensure_ascii=False,indent=2))
