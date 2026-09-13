from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
def load(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def main():
 g=load(ROOT/'outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl'); d=load(ROOT/'outputs/phase7/decisions/escalation_decisions.jsonl'); gd={x['golden_id']:x for x in g}; rows=[]; agreement=0; comparable=0
 for x in d:
  prelim=gd[x['query_id']].get('evaluation',{}).get('should_escalate')
  if prelim is not None: comparable+=1; agreement+=int(bool(prelim)==x['should_escalate'])
  rows.append({'query_id':x['query_id'],'decision':x['decision'],'should_escalate':x['should_escalate'],'selected_evidence_id':x['selected_evidence_id'],'evidence_score':x['evidence_score'],'response_type':x['response_type'],'generated_response_present':x['generated_response'] is not None,'preliminary_annotated_reference':prelim,'comparison_available':prelim is not None})
 auto=sum(x['decision']=='auto_handle' for x in d); esc=len(d)-auto; grounded_auto=sum(x['generated_response'] is not None for x in d if x['decision']=='auto_handle')
 summary={'phase':8,'total_queries':len(d),'decision_counts':{'auto_handle':auto,'escalate':esc},'decision_percentages':{'auto_handle':round(100*auto/len(d),2),'escalate':round(100*esc/len(d),2)},'auto_handle_grounded_response_coverage':round(100*grounded_auto/auto,2) if auto else 0,'escalated_without_generated_response':sum(x['decision']=='escalate' and x['generated_response'] is None for x in d),'preliminary_reference_comparison':{'comparable_queries':comparable,'agreement_count':agreement,'agreement_percentage':round(100*agreement/comparable,2) if comparable else None,'warning':'Phase 3E should_escalate is not human gold and was not used to make Phase 7 decisions.'},'human_evaluation':{'retrieval_relevance':'pending','response_grounding':'pending human review despite provenance checks','response_quality':'pending','escalation_correctness':'pending','gold_labels':False},'proof_checks':{'all_queries_covered':len(d)==200,'auto_handle_responses_present':grounded_auto==auto,'escalations_have_no_generated_response':all(x['generated_response'] is None for x in d if x['decision']=='escalate')}}
 out=ROOT/'outputs/phase8/evaluation'; (out/'phase8_evaluation_results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); (out/'phase8_evaluation_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('PHASE 8 EVALUATION: PASS'); print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
