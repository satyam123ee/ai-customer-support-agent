from pathlib import Path
import csv, json, random

ROOT = Path(__file__).resolve().parents[3]
SEED = 20260913
SAMPLE_SIZE = 30

def load_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def main():
    decisions = {x['query_id']: x for x in load_jsonl(ROOT / 'outputs/phase7/decisions/escalation_decisions.jsonl')}
    golden = {x['golden_id']: x for x in load_jsonl(ROOT / 'outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl')}
    phase6 = {x['query_id']: x for x in load_jsonl(ROOT / 'outputs/phase6/generation/golden_grounded_responses.jsonl')}
    ids = list(golden)
    random.Random(SEED).shuffle(ids)
    selected = ids[:SAMPLE_SIZE]

    out = ROOT / 'outputs/phase8/human'
    path = out / 'human_judge_sample.csv'
    fields = [
        'query_id','customer_message','historical_evidence','generated_response','decision',
        'human_retrieval_relevance_1_5','human_response_grounding_1_5','human_response_quality_1_5',
        'human_escalation_correctness_0_1','human_overall_acceptable_0_1','human_notes'
    ]
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for qid in selected:
            p6 = phase6.get(qid, {})
            ev = p6.get('selected_evidence') or []
            evidence = ev[0].get('historical_response') if ev else ''
            d = decisions.get(qid, {})
            w.writerow({
                'query_id': qid,
                'customer_message': golden[qid]['text'],
                'historical_evidence': evidence or '',
                'generated_response': p6.get('generated_response') or '',
                'decision': d.get('decision',''),
                'human_retrieval_relevance_1_5':'',
                'human_response_grounding_1_5':'',
                'human_response_quality_1_5':'',
                'human_escalation_correctness_0_1':'',
                'human_overall_acceptable_0_1':'',
                'human_notes':''
            })
    print(f'Created {path} with {SAMPLE_SIZE} rows.')
    print('Human rubric: relevance/grounding/quality are 1-5; escalation correctness and overall acceptable are 0/1.')

if __name__ == '__main__': main()
