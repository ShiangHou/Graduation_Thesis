"""Offline audit + public item/chunk examples. No LLM or benchmark result.
Expanded-pool candidates without query-specific labels remain UNJUDGED.
"""
from pathlib import Path
import json, hashlib, re, math, statistics, collections, random
HERE=Path(__file__).resolve().parent
CACHE=HERE.parents[2]/'.local/topic_b/public_item_chunk'
OUT=HERE/'examples'; OUT.mkdir(exist_ok=True)
def write(name,x): (OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def norm(s): return ' '.join(s.split())
def tok(s): return re.findall(r'[a-z0-9]+',s.lower())
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
rows=[json.loads(s) for s in (CACHE/'finrank.jsonl').read_text().splitlines()]
corpus={}; text_origins=collections.defaultdict(set); idmap={};counts=collections.Counter();allchars=[];allwords=[];hash_mismatches=[]
for r in rows:
 for role in ['passages','hard_negatives']:
  for p in r[role]:
   text=p['text'];md={k:str((r if role=='passages' else p).get(k,'')) for k in ['ticker','year','doc_type']};md['page']=str(p.get('page_number',''))
   key=json.dumps([md,norm(text)],sort_keys=True);uid='I_'+digest(key)[:20]
   idmap[p['passage_id']]=uid
   lines=[norm(x).strip('# ').strip() for x in text.splitlines() if norm(x)]
   # Query-independent, identical title algorithm for positive/negative/all candidates.
   title=lines[0][:100] if lines else '[empty]'
   corpus.setdefault(uid,{'id':uid,'item':{'issuer':md['ticker'],'filing_year_raw':md['year'],'form':md['doc_type'],'disclosure_title_extract':title},'chunk':text,'provenance':{'dataset':'FinRank','page_number_raw':md['page']}})
   text_origins[norm(text)].add(tuple(md.values()));counts[role]+=1;allchars.append(len(text));allwords.append(len(tok(text)))
   if hashlib.sha1(text.strip().encode()).hexdigest()!=p['text_sha1']: hash_mismatches.append(p['passage_id'])
r=rows[0];q=r['question'];positives={idmap[p['passage_id']] for p in r['passages']}; negatives={idmap[p['passage_id']] for p in r['hard_negatives']};assert not positives&negatives
# Simple fully specified BM25 on source metadata + title + chunk, solely for constructing a demo pool.
keys=sorted(corpus);freq=[];df=collections.Counter();lens=[]
for k in keys:
 c=corpus[k];f=collections.Counter(tok(json.dumps(c['item'])+' '+c['chunk']));freq.append(f);df.update(f.keys());lens.append(sum(f.values()))
avg=sum(lens)/len(lens); scores=[]
for i,k in enumerate(keys):
 score=0.0
 for t in set(tok(q)):
  n=freq[i][t]
  if n: score+=math.log(1+(len(keys)-df[t]+.5)/(df[t]+.5))*n*2.2/(n+1.2*(.25+.75*lens[i]/avg))
 scores.append((score,k))
ranked=[k for _,k in sorted(scores,key=lambda z:(-z[0],z[1]))]
base=sorted(positives|negatives); expanded=base+[k for k in ranked if k not in positives|negatives]
label_map={k:1 for k in positives};label_map.update({k:0 for k in negatives})
for n in [20,50,100,150,250]:
 chosen=expanded[:n];random.Random(20261012).shuffle(chosen)
 modelinput={'task':'Rank financial disclosure items by usefulness for the public question. Return top 20 with source-bound reasons; state limitations for weak or irrelevant items. Do not claim every returned item is sufficient evidence.','query':q,'candidates':[corpus[k] for k in chosen]}
 assert len(chosen)==len(set(chosen))==n
 raw=json.dumps(modelinput)
 assert not any(x in raw for x in ['"hard_negatives"','"qrels"','"answer"','"query_rewrite"',':hn0',':p0'])
 write(f'finrank_input_{n}.json',modelinput)
 write(f'finrank_eval_only_{n}.json',{'source_query_id':r['id'],'pool_type':'positive-preserving curated expansion, not natural retrieval','model_was_run':False,'ready_for_complete_gold_evaluation':False,'labels':{k:{'relevance':label_map.get(k),'status':'source_positive' if k in positives else 'source_hard_negative' if k in negatives else 'UNJUDGED'} for k in chosen},'source_answer_evaluation_only':r['answer'],'notice':'Other records’ passages are NOT automatically negatives. Expanded labels need audit; metadata year is filing year, not automatically fiscal period.'})
write('finrank_original_small_pool.json',{'query':q,'candidates':[corpus[k] for k in base],'evaluation_only_labels':label_map,'notice':'Teaching file includes labels; do not pass entire file to model.'})
# FinQA example: construct input solely from table + prose; never copy qa.gold_inds text into input.
a=json.loads((CACHE/'finqa_dev.json').read_text());f=a[0];header=f['table'][0];cards=[]
for i,row in enumerate(f['table'][1:],1):
 fields=[{'metric':header[j],'value':row[j]} for j in range(1,min(len(row),len(header)))]
 cards.append({'id':f'T{i:02d}','item':{'entity':row[0],'record_type':'payment_network_metrics'},'chunk':{'table_header':header,'table_row':row,'context_before':f['pre_text'][3],'scope_notes':f['post_text'][2:14]},'source':{'filename':f['filename'],'table_row_index':i}})
write('finqa_real_item_chunk_example.json',{'query':f['qa']['question'],'candidates':cards,'notice':'Six-row real example only; not a 250-item pool and not model output.'})
write('finqa_evaluation_only.json',{'source_id':f['id'],'gold_evidence_keys':list(f['qa']['gold_inds']),'answer':f['qa']['answer'],'program':f['qa']['program'],'notice':'Gold source evidence labels, not exhaustive new multi-report pool labels. Filename 2008 is not table period: context says calendar 2007; JCB has additional period caveats.'})
repair=json.loads((CACHE/'finrank_repair_log.json').read_text())
splits=json.loads((CACHE/'finrank_splits.json').read_text())
audit={'date':'2026-10-12','finrank':{'records':len(rows),'unique_query_ids':len({x['id'] for x in rows}),'source_tickers':len({x['ticker'] for x in rows}),**counts,'unique_raw_texts':len({p['text'] for r in rows for role in ['passages','hard_negatives'] for p in r[role]}),'unique_normalized_texts':len(text_origins),'unique_source_bound_cards':len(corpus),'text_with_multiple_source_metadata':sum(len(v)>1 for v in text_origins.values()),'median_candidate_chars_occurrence_weighted':statistics.median(allchars),'median_candidate_regex_words_occurrence_weighted':statistics.median(allwords),'qid_label_mismatches':len(repair['qid_label_mismatches']),'source_text_sha1_mismatch_ids':hash_mismatches,'split_regimes':list(splits),'first_demo_known_positive':len(positives),'first_demo_known_negative':len(negatives),'expanded_250_unjudged':250-len(label_map)},'finqa':{'downloaded_split':'dev only','records':len(a),'first_id':f['id'],'first_question':f['qa']['question'],'first_table_items':len(cards)},'scope':'Read-only source audit and deterministic construction demo. No model inference, no training, no claimed hallucination result.'}
(HERE/'assembly_audit_20261012.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));print(json.dumps(audit,ensure_ascii=False,indent=2))
