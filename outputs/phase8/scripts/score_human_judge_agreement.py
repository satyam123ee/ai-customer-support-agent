from pathlib import Path
import csv, json, math

ROOT = Path(__file__).resolve().parents[3]


def mean(xs): return sum(xs)/len(xs) if xs else None

def pearson(a,b):
    if len(a) < 2: return None
    ma, mb = mean(a), mean(b)
    num = sum((x-ma)*(y-mb) for x,y in zip(a,b))
    da = math.sqrt(sum((x-ma)**2 for x in a)); db = math.sqrt(sum((y-mb)**2 for y in b))
    return num/(da*db) if da and db else None

def main():
    path = ROOT / 'outputs/phase8/human/human_judge_sample.csv'
    if not path.exists():
        raise SystemExit(f'Missing {path}. Run build_human_judge_sample.py first.')
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    required = ['human_retrieval_relevance_1_5','human_response_grounding_1_5','human_response_quality_1_5','human_escalation_correctness_0_1','human_overall_acceptable_0_1']
    if any(not all(r.get(k,'').strip() for k in required) for r in rows):
        raise SystemExit('Human labels are incomplete. Fill every rubric column before scoring agreement.')

    judge_path = ROOT / 'outputs/phase8/judge/llm_judge_results.jsonl'
    judge = {x['query_id']: x for x in (json.loads(line) for line in judge_path.open(encoding='utf-8')) if line.strip()}
    paired = [r for r in rows if r['query_id'] in judge]
    if not paired: raise SystemExit('No overlapping human/LLM judge rows found.')

    metrics = {}
    for dim, human_col, judge_col in [
        ('retrieval_relevance','human_retrieval_relevance_1_5','retrieval_relevance_1_5'),
        ('response_grounding','human_response_grounding_1_5','response_grounding_1_5'),
        ('response_quality','human_response_quality_1_5','response_quality_1_5'),
    ]:
        h=[float(r[human_col]) for r in paired]; j=[float(judge[r['query_id']][judge_col]) for r in paired]
        mae=mean([abs(a-b) for a,b in zip(h,j)])
        exact=sum(abs(a-b)<1e-9 for a,b in zip(h,j))/len(h)
        adjacent=sum(abs(a-b)<=1 for a,b in zip(h,j))/len(h)
        metrics[dim]={'n':len(h),'mean_absolute_error':round(mae,4),'exact_agreement':round(exact,4),'within_one_point':round(adjacent,4),'pearson_r':round(pearson(h,j),4) if pearson(h,j) is not None else None}

    h=[int(r['human_escalation_correctness_0_1']) for r in paired]; j=[int(bool(judge[r['query_id']]['escalation_correct'])) for r in paired]
    metrics['escalation_correctness']={'n':len(h),'agreement':round(sum(a==b for a,b in zip(h,j))/len(h),4)}
    h=[int(r['human_overall_acceptable_0_1']) for r in paired]; j=[int(bool(judge[r['query_id']]['overall_acceptable'])) for r in paired]
    metrics['overall_acceptable']={'n':len(h),'agreement':round(sum(a==b for a,b in zip(h,j))/len(h),4)}

    out=ROOT/'outputs/phase8/human/human_llm_agreement_summary.json'
    out.write_text(json.dumps({'sample_size':len(paired),'metrics':metrics,'interpretation':'Agreement on a small manually reviewed subset is calibration evidence, not proof of universal judge accuracy.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
