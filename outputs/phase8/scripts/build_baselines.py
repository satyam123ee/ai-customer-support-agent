from pathlib import Path
import json
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]

def load_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]

def main():
    golden = load_jsonl(ROOT / 'outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl')
    retrieval = load_jsonl(ROOT / 'outputs/phase4/retrieval/retrieval_results.jsonl')
    phase6 = load_jsonl(ROOT / 'outputs/phase6/generation/golden_grounded_responses.jsonl')

    responses = [x['retrieved_historical_response'] for x in retrieval if x.get('retrieved_historical_response')]
    counts = Counter(responses)
    trivial_response = counts.most_common(1)[0][0] if counts else None

    by_query = {}
    for row in retrieval:
        by_query.setdefault(row['golden_id'], []).append(row)
    for rows in by_query.values():
        rows.sort(key=lambda x: x.get('retrieved_rank', x.get('retrieved_rank', 999)))

    phase6_by = {x['query_id']: x for x in phase6}
    rows = []
    for g in golden:
        qid = g['golden_id']
        gold_intent = g.get('evaluation', {}).get('gold_intent')
        top = by_query.get(qid, [None])[0]
        retrieved_intents = (top or {}).get('retrieved_intent_ids') or []
        simple_agreement = bool(gold_intent and gold_intent in retrieved_intents)
        rows.append({
            'query_id': qid,
            'gold_intent': gold_intent,
            'trivial_response': trivial_response,
            'simple_top1_response': top.get('retrieved_historical_response') if top else None,
            'simple_top1_intents': retrieved_intents,
            'simple_top1_intent_agreement': simple_agreement if gold_intent else None,
            'our_response': phase6_by.get(qid, {}).get('generated_response'),
            'our_evidence_score': phase6_by.get(qid, {}).get('evidence_score'),
            'our_grounding_status': phase6_by.get(qid, {}).get('grounding_status'),
        })

    comparable = [r for r in rows if r['simple_top1_intent_agreement'] is not None]
    simple_agreement = sum(r['simple_top1_intent_agreement'] for r in comparable) / len(comparable) if comparable else None
    summary = {
        'trivial_baseline': {
            'definition': 'Always return the single most frequent historical response in the retrieval corpus.',
            'nonempty_response_rate': round(100 * len(responses) / len(retrieval), 2) if retrieval else 0,
            'most_frequent_response_count': counts.most_common(1)[0][1] if counts else 0,
            'most_frequent_response': trivial_response,
        },
        'simple_baseline': {
            'definition': 'Return the raw TF-IDF top-1 historical response without evidence thresholds, response-type filtering, or escalation policy.',
            'intent_agreement_comparable': len(comparable),
            'intent_agreement_percentage': round(simple_agreement * 100, 2) if simple_agreement is not None else None,
            'note': 'Intent agreement uses the gold intent appearing in the retrieved row intent_ids. It is a retrieval diagnostic, not response quality.'
        },
        'our_system': {
            'definition': 'Phase 5 evidence scoring + Phase 6 conservative grounded response + Phase 7 escalation policy.',
        },
        'warning': 'Response-quality comparison is intentionally deferred to the LLM judge/human calibration subset; deterministic intent agreement is not response quality.',
    }
    out = ROOT / 'outputs/phase8/baselines'
    (out / 'baseline_examples.jsonl').write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in rows) + '\n', encoding='utf-8')
    (out / 'baseline_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == '__main__': main()
