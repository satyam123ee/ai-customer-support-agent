from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def main():
 g=load(ROOT/'outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl'); e=load(ROOT/'outputs/phase5/evidence/historical_evidence_results.jsonl'); r6=load(ROOT/'outputs/phase6/generation/golden_grounded_responses.jsonl'); d=load(ROOT/'outputs/phase7/decisions/escalation_decisions.jsonl')
 assert len(g)==len(r6)==len(d)==200
 gd={x['golden_id']:x for x in g}; p6={x['query_id']:x for x in r6}; ev={}
 for x in e: ev.setdefault(x['golden_id'],{})[str(x['retrieved_message_id'])]=x
 seen=set()
 for x in d:
  q=x['query_id']; assert q in gd and q not in seen; seen.add(q); assert x['customer_message']==gd[q]['text']
  if x['selected_evidence_id'] is not None:
   s=ev[q][str(x['selected_evidence_id'])]; assert abs(float(x['evidence_score'])-float(s['deterministic_evidence_score']))<1e-9; assert x['response_type']==s['response_type']
  assert x['decision'] in {'auto_handle','escalate'} and x['decision_method']=='deterministic_rule_based'
  if x['decision']=='auto_handle': assert x['should_escalate'] is False and x['generated_response']==p6[q]['generated_response'] and x['generated_response'] is not None
  else: assert x['should_escalate'] is True and x['generated_response'] is None and x['escalation_reason']
 print('PHASE 7 VALIDATION: PASS')
 print('200/200 queries validated; provenance, score/type matching, response matching, decision consistency, and no-fabrication checks passed.')
if __name__=='__main__': main()
