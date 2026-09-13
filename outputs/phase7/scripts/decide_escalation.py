from pathlib import Path
import json, re
from collections import Counter
ROOT = Path(__file__).resolve().parents[3]
P3 = ROOT / 'outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl'
P5 = ROOT / 'outputs/phase5/evidence/historical_evidence_results.jsonl'
P6 = ROOT / 'outputs/phase6/generation/golden_grounded_responses.jsonl'
OUT = ROOT / 'outputs/phase7/decisions/escalation_decisions.jsonl'
SUMMARY = ROOT / 'outputs/phase7/decisions/phase7_decision_summary.json'
HIGH_RISK = [
 ('account_or_security_sensitive', re.compile(r'\b(password|passcode|security|locked out|account recovery|apple id|icloud account|verification code|two[- ]factor|2fa|stolen|lost (my )?(iphone|ipad|mac)|find my)\b', re.I)),
 ('billing_or_payment_case_specific', re.compile(r'\b(charged|charge|refund|refund me|payment|billing|credit card|debit card|purchase|subscription|unauthorized purchase|unknown purchase|money)\b', re.I)),
 ('order_repair_case_specific', re.compile(r'\b(order|repair|replacement|replace my|service appointment|genius bar|shipment|shipping|delivery|return my|warranty claim)\b', re.I)),
]
def load(p):
 with open(p, encoding='utf-8') as f: return [json.loads(x) for x in f if x.strip()]
def main():
 golden={x['golden_id']:x for x in load(P3)}; ev={}
 for x in load(P5): ev.setdefault(x['golden_id'],[]).append(x)
 p6={x['query_id']:x for x in load(P6)}; rows=[]
 for qid in sorted(golden,key=lambda x:int(x.split('-')[1])):
  g=golden[qid]; r6=p6[qid]; selected=(r6.get('selected_evidence') or [None])[0]
  sid=selected.get('retrieved_message_id') if selected else None
  source=next((x for x in ev.get(qid,[]) if str(x.get('retrieved_message_id'))==str(sid)),None) if sid else None
  score=source.get('deterministic_evidence_score') if source else r6.get('evidence_score')
  rtype=source.get('response_type') if source else (selected.get('response_type') if selected else 'none')
  response=r6.get('generated_response') if r6.get('grounding_status')=='grounded_historical_response' else None
  reason=None; text=g['text']
  for rr,pat in HIGH_RISK:
   if pat.search(text): reason=rr; break
  if reason is None and r6.get('grounding_status')!='grounded_historical_response': reason='insufficient_historical_evidence'
  elif reason is None and not response: reason='no_grounded_response'
  elif reason is None and rtype not in {'diagnostic_question','direct_guidance'}: reason='generic_routing_only' if rtype=='generic_routing' else 'other_safety_or_grounding_concern'
  elif reason is None and (score is None or float(score)<0.35): reason='insufficient_historical_evidence'
  elif reason is None and g.get('evaluation',{}).get('gold_intent') is None and g.get('bucket') in {'ambiguous','multi_intent','unclassified'}: reason='ambiguous_request'
  decision='escalate' if reason else 'auto_handle'
  rows.append({'query_id':qid,'customer_message':text,'selected_evidence_id':sid,'evidence_score':score,'response_type':rtype,'generated_response':response if decision=='auto_handle' else None,'should_escalate':decision=='escalate','escalation_reason':reason,'decision':decision,'decision_method':'deterministic_rule_based'})
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with open(OUT,'w',encoding='utf-8',newline='\n') as f:
  for r in rows: f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
 auto=sum(r['decision']=='auto_handle' for r in rows); esc=len(rows)-auto
 summary={'phase':7,'total_queries':len(rows),'auto_handle_count':auto,'auto_handle_percentage':round(100*auto/len(rows),2),'escalation_count':esc,'escalation_percentage':round(100*esc/len(rows),2),'escalation_reason_distribution':dict(Counter(r['escalation_reason'] for r in rows if r['escalation_reason'])),'evidence_availability_distribution':dict(Counter('available' if r['selected_evidence_id'] else 'unavailable' for r in rows)),'response_type_distribution':dict(Counter(r['response_type'] for r in rows)),'decision_distribution':dict(Counter(r['decision'] for r in rows)),'methodology':{'decision_method':'deterministic_rule_based','threshold':0.35,'phase3e_should_escalate':'comparison-only preliminary_annotated_reference; never used to determine decisions','human_validation':False}}
 SUMMARY.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
if __name__=='__main__': main()
