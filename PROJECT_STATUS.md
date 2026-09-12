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

## CURRENT TASK

### Phase 3B — Candidate Pool

STATUS: NOT STARTED

Goal:

Create a high-quality candidate pool of approximately 500–1000 real AppleSupport customer messages.

The pool should support later human labeling and construction of a golden evaluation set.

Candidate pool should include:

1. Examples from each discovered intent
2. Ambiguous examples
3. Unclassified examples
4. Multi-intent examples
5. Short but meaningful messages
6. Different conversation lengths
7. Different dates
8. Real customer → AppleSupport interactions

Do NOT manually invent customer messages.

Use actual messages from twcs.csv / prepared AppleSupport data.

## NEXT STEPS

1. Inspect existing Phase 3A taxonomy.
2. Inspect AppleSupport conversation data.
3. Design a reproducible candidate-sampling strategy.
4. Generate approximately 500–1000 candidate examples.
5. Save candidate data in a structured format.
6. Generate a report describing the sampling methodology.
7. Later create a 150–250 example golden evaluation set.
8. Later implement/evaluate intent classification.
9. Later implement response generation and escalation decisions.
10. Produce final Hiver assignment evaluation/proof.

## Important Constraints

- Use the full dataset.
- Do not restart completed phases.
- Do not overwrite useful existing outputs.
- Use streaming/chunked processing for large CSV files.
- Keep generated large files local when possible.
- Every major result should be reproducible from a script.