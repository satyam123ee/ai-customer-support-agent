"""LLM-as-judge harness using an OpenAI-compatible HTTP endpoint.

Environment:
  LLM_API_KEY       required
  LLM_API_URL       optional, defaults to https://api.openai.com/v1/chat/completions
  LLM_MODEL         optional, defaults to gpt-4o-mini

The script only sends the 30 human-calibration examples by default. It can be
extended to all 200 with --all after calibration.
"""
from pathlib import Path
import argparse, csv, json, os, time, urllib.request

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = {
  'retrieval_relevance_1_5':'Does the historical evidence address the customer\'s actual issue? 1=irrelevant, 5=directly relevant.',
  'response_grounding_1_5':'Is the generated reply supported by the supplied historical evidence, without invented facts? 1=unsupported, 5=fully grounded.',
  'response_quality_1_5':'Would this be a useful, clear, brand-appropriate support reply? 1=poor, 5=excellent.',
  'escalation_correct':'Should the agent\'s auto-handle/escalate decision be trusted for this case? true/false.',
  'overall_acceptable':'Is the complete agent output acceptable for deployment as-is? true/false.'
}

def call_api(url,key,model,payload):
    req=urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {key}'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"\nAPI ERROR: HTTP {e.code}")
        print(body)
        raise

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--all',action='store_true'); ap.add_argument('--limit',type=int,default=30); args=ap.parse_args()
    key=os.getenv('LLM_API_KEY')
    if not key: raise SystemExit('Set LLM_API_KEY in your environment. Do not commit it.')
    url=os.getenv('LLM_API_URL','https://api.openai.com/v1/chat/completions'); model=os.getenv('LLM_MODEL','gpt-4o-mini')
    path=ROOT/'outputs/phase8/human/human_judge_sample.csv'
    rows=list(csv.DictReader(path.open(encoding='utf-8')))
    if args.all:
        # Use the full Phase 7/6 set, while keeping the same schema.
        decisions={x['query_id']:x for x in (json.loads(l) for l in (ROOT/'outputs/phase7/decisions/escalation_decisions.jsonl').open(encoding='utf8')) if l.strip()}
        phase6={x['query_id']:x for x in (json.loads(l) for l in (ROOT/'outputs/phase6/generation/golden_grounded_responses.jsonl').open(encoding='utf8')) if l.strip()}
        rows=[]
        for qid,d in decisions.items():
            ev=(phase6.get(qid,{}).get('selected_evidence') or [])
            rows.append({'query_id':qid,'customer_message':phase6.get(qid,{}).get('customer_message',''),'historical_evidence':ev[0].get('historical_response','') if ev else '','generated_response':phase6.get(qid,{}).get('generated_response') or '','decision':d.get('decision','')})
    else: rows=rows[:args.limit]
    out=ROOT/'outputs/phase8/judge/llm_judge_results.jsonl'; out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf8') as f:
      for row in rows:
        prompt={'customer_message':row.get('customer_message',''),'historical_evidence':row.get('historical_evidence',''),'generated_response':row.get('generated_response',''),'agent_decision':row.get('decision',''),'rubric':RUBRIC,'output_schema':'Return ONLY JSON with integer 1-5 scores for the three rating fields and boolean values for the two boolean fields, plus a short reason.'}
        payload={'model':model,'temperature':0,'messages':[{'role':'system','content':'You are a strict customer-support evaluation judge. Evaluate only the supplied evidence. Do not infer missing facts.'},{'role':'user','content':json.dumps(prompt,ensure_ascii=False)}]}
        data=call_api(url,key,model,payload); content=data['choices'][0]['message']['content'].strip()
        if content.startswith('```'): content=content.strip('`').replace('json\n','',1).strip()
        result=json.loads(content); result['query_id']=row['query_id']; f.write(json.dumps(result,ensure_ascii=False)+'\n'); f.flush(); time.sleep(0.1)
    print(f'Wrote {out}')

if __name__=='__main__': main()
