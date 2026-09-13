from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def main():
 s=load(ROOT/'outputs/phase8/evaluation/phase8_evaluation_summary.json'); rows=load(ROOT/'outputs/phase8/evaluation/phase8_evaluation_results.json')
 assert len(rows)==200 and s['total_queries']==200
 assert s['proof_checks']['all_queries_covered'] is True
 assert s['proof_checks']['auto_handle_responses_present'] is True
 assert s['proof_checks']['escalations_have_no_generated_response'] is True
 assert s['human_evaluation']['gold_labels'] is False
 assert 'warning' in s['preliminary_reference_comparison']
 print('PHASE 8 VALIDATION: PASS')
if __name__=='__main__': main()
