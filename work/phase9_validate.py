from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
'outputs/phase7/scripts/decide_escalation.py','outputs/phase7/decisions/escalation_decisions.jsonl','outputs/phase7/decisions/phase7_decision_summary.json','outputs/phase7/reports/PHASE7_ESCALATION_DECISION_REPORT.md','work/phase7_validate.py',
'outputs/phase8/scripts/evaluate_phase7.py','outputs/phase8/evaluation/phase8_evaluation_results.json','outputs/phase8/evaluation/phase8_evaluation_summary.json','outputs/phase8/reports/PHASE8_EVALUATION_REPORT.md','work/phase8_validate.py',
'outputs/phase9/generate_final_report.py','outputs/phase9/reports/FINAL_SUBMISSION_REPORT.md','outputs/phase9/reports/FINAL_SUBMISSION_CHECKLIST.md','outputs/phase9/reports/FINAL_SUBMISSION_MANIFEST.md']
assert all((ROOT/x).exists() for x in required)
assert not any(p.name=='twcs.csv' for p in ROOT.rglob('twcs.csv'))
print('PHASE 9 VALIDATION: PASS')
print(f'{len(required)} required Phase 7–9 artifacts present; twcs.csv excluded from the final package.')
