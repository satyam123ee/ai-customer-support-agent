# Hiver SDE Intern — AI Support Agent

A reproducible, conservative customer-support agent built on the **Customer Support on Twitter (TWCS)** dataset for the **AppleSupport** brand.

## What it does

1. Discovers a small AppleSupport intent taxonomy.
2. Builds a 200-example golden evaluation set.
3. Retrieves historically similar customer-support interactions with TF-IDF.
4. Scores historical evidence.
5. Copies only historically grounded diagnostic/guidance responses.
6. Escalates ambiguous, sensitive, transaction-specific, or weak-evidence cases.
7. Evaluates retrieval, grounding/provenance, escalation policy, baselines, and LLM-judge/human calibration.

## Reproduce the headline Phase 7–9 results

These commands use committed intermediate artifacts and do **not** require the 493 MB raw dataset:

```powershell
python outputs/phase7/scripts/decide_escalation.py
python work/phase7_validate.py
python outputs/phase8/scripts/build_baselines.py
python outputs/phase8/scripts/evaluate_phase7.py
python work/phase8_validate.py
python outputs/phase9/generate_final_report.py
python work/phase9_validate.py
```

Expected Phase 7 headline:

- 200 golden queries
- 117 auto-handle (58.5%)
- 83 escalate (41.5%)
- 177 cases have usable historical evidence in Phase 6
- 23 cases have no usable response selected

## LLM-as-judge + human agreement

The assignment requires an LLM judge **and evidence that the judge agrees with a human**. This repository includes the full calibration harness without fabricating human labels.

### 1. Create the 30-case human calibration sheet

```powershell
python outputs/phase8/scripts/build_human_judge_sample.py
```

Open:

`outputs/phase8/human/human_judge_sample.csv`

Fill these columns independently for all 30 rows:

- `human_retrieval_relevance_1_5`
- `human_response_grounding_1_5`
- `human_response_quality_1_5`
- `human_escalation_correctness_0_1`
- `human_overall_acceptable_0_1`
- `human_notes`

### 2. Run the LLM judge

Set an OpenAI-compatible API key without committing it:

```powershell
$env:LLM_API_KEY="YOUR_KEY"
python outputs/phase8/scripts/run_llm_judge.py
```

Optional:

```powershell
$env:LLM_MODEL="gpt-4o-mini"
$env:LLM_API_URL="https://api.openai.com/v1/chat/completions"
```

### 3. Calculate human-vs-judge agreement

```powershell
python outputs/phase8/scripts/score_human_judge_agreement.py
```

This reports MAE, exact agreement, within-one-point agreement, Pearson correlation for 1–5 dimensions, and binary agreement for escalation/overall acceptability.

**Do not claim judge/human agreement until these 30 rows have actually been human-labelled.**

## Baselines

- **Trivial:** always return the most frequent historical response.
- **Simple:** raw TF-IDF top-1 historical retrieval with no evidence threshold, response-type filter, or escalation policy.
- **Our system:** evidence scoring + conservative grounded response selection + escalation safeguards.

Generate the baseline artifacts with:

```powershell
python outputs/phase8/scripts/build_baselines.py
```

## Reports

- `outputs/phase9/reports/FINAL_SUBMISSION_REPORT.md`
- `outputs/phase8/reports/FAILURE_ANALYSIS.md`
- `outputs/phase8/baselines/baseline_summary.json`
- `outputs/phase8/human/human_judge_sample.csv`

## Important limitations

The raw TWCS data is noisy and the project does not have authenticated account/order/payment tools. Therefore the agent is intentionally conservative. Deterministic agreement numbers are not presented as human accuracy. Human evaluation is required before claiming production-level response quality.

## Data safety

`twcs.csv`, `.env`, virtual environments, caches, and other local-only artifacts are ignored and are not part of the submission.
