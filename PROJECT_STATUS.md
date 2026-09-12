# Hiver Internship Project Status

Last updated: 2026-09-12

## Repository

GitHub repository:

https://github.com/satyam123ee/hiver-intern-repo.git

Branch:

main

The project has been successfully pushed to GitHub.

## Local Project

The project is located at:

C:\Users\DELL\Documents\Codex\2026-09-12\excellent-the-new-dataset-is-much

## Dataset

Full TWCS dataset:

twcs.csv

Approximate size:

493 MB

The dataset is local and ignored by Git.

Do not upload twcs.csv to GitHub.

## Progress

### Phase 1 — Brand Selection

STATUS: COMPLETE

Selected brand:

AppleSupport

Full dataset:
- 2,811,774 rows
- 108 brands
- 106,860 AppleSupport outbound tweets

Files:

outputs/BRAND_SELECTION_REPORT.md
outputs/brand_config.json
outputs/phase1_brand_selection.py

### Phase 2 — Data Preparation

STATUS: COMPLETE

Results:
- 106,860 AppleSupport outbound tweets
- 119,895 related inbound customer tweets
- 77,431 unique customers
- 83,449 customer conversations
- 106,623 usable direct customer → brand interactions
- 88.93% response coverage
- Average conversation length: 2.717
- Median: 2
- Maximum: 266

Files:

outputs/phase2/scripts/prepare_applesupport_data.py
outputs/phase2/outputs/applesupport_stats.json
outputs/phase2/reports/PHASE2_DATA_PREPARATION_REPORT.md
outputs/phase2/data/applesupport_conversations.jsonl

### Phase 3A — Intent Discovery

STATUS: COMPLETE

15 candidate intents discovered.

72,598 messages classified.

Classification coverage:

60.55%

Unclassified:

39.45%

Multi-intent:

23.77%

Files:

outputs/phase3/scripts/discover_intents.py
outputs/phase3/taxonomy/intent_taxonomy.json
outputs/phase3/taxonomy/INTENT_TAXONOMY_REPORT.md

### Phase 3B — Candidate Pool

STATUS: COMPLETE

Goal achieved:

Created a reproducible candidate pool of 700 real AppleSupport customer messages for later labeling and golden-set construction.

Quality filtering complete:
- Exact quotas preserved: 520 primary-intent, 60 unclassified, 80 multi-intent, and 40 ambiguous.
- All 15 primary intents remain represented.
- Deterministic same-bucket quality filtering removed low-diversity noise, exact duplicates, clearly redundant near-duplicates, and Unicode artifacts.
- Replacements were sourced only from the same bucket or primary-intent quota.
- Raw pre-filter output backed up as outputs/phase3/candidate_pool/candidate_pool.pre_quality_filter_backup.jsonl.

The final pool includes:

1. Coverage across the discovered intents
2. Ambiguous examples
3. Unclassified examples
4. Multi-intent examples
5. Short but meaningful messages
6. Different conversation lengths and dates
7. Real customer → AppleSupport interactions

Files:

outputs/phase3/scripts/build_candidate_pool.py
outputs/phase3/candidate_pool/candidate_pool.jsonl
outputs/phase3/candidate_pool/candidate_pool_summary.json
outputs/phase3/reports/PHASE3B_CANDIDATE_POOL_REPORT.md

## CURRENT TASK

### Phase 3C — Golden Evaluation Set

STATUS: COMPLETE

Goal achieved:

Created a deterministic 200-record golden evaluation set from the locked Phase 3B candidate pool.

Results:
- 200 records selected with coverage across all 15 primary intents.
- Bucket distribution: 150 primary-intent, 20 unclassified, 15 multi-intent, and 15 ambiguous.
- Original source text and metadata preserved exactly.
- Evaluation fields remain empty placeholders for later human annotation.
- Independent validation passed for JSONL validity, source membership, text preservation, duplicate safety, bucket totals, and intent coverage.

Files:

outputs/phase3/scripts/build_golden_set.py
outputs/phase3/golden_set/golden_evaluation_set.jsonl
outputs/phase3/golden_set/golden_set_summary.json
outputs/phase3/reports/PHASE3C_GOLDEN_SET_REPORT.md
work/phase3c_validate.py

## NEXT STEPS

1. Inspect existing Phase 3A taxonomy.
2. Inspect AppleSupport conversation data.
3. Design a reproducible candidate-sampling strategy.
4. Later annotate the golden evaluation set manually.
5. Later implement/evaluate intent classification.
6. Later implement retrieval and RAG grounding evaluation.
7. Later implement response generation and escalation decisions.
8. Produce final Hiver assignment evaluation/proof.

## Important Constraints

- Use the full dataset.
- Do not restart completed phases.
- Do not overwrite useful existing outputs.
- Use streaming/chunked processing for large CSV files.
- Keep generated large files local when possible.
- Every major result should be reproducible from a script.