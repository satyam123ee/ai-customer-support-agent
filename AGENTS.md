# Hiver SDE Internship Assignment

## Project Goal

Build an AI support agent using the Customer Support on Twitter (TWCS) dataset for the Hiver SDE Intern take-home assignment.

The selected brand is AppleSupport.

## Dataset

The full dataset is available locally as:

twcs.csv

Important:
- The dataset is approximately 493 MB.
- Do NOT commit twcs.csv to GitHub.
- It is already excluded through .gitignore.

## Completed Work

### Phase 1 — Brand Selection

Selected brand:

AppleSupport

Full dataset statistics:
- Total data rows: 2,811,774
- Brands analyzed: 108
- AppleSupport outbound tweets: 106,860

Relevant report:

outputs/BRAND_SELECTION_REPORT.md

Configuration:

outputs/brand_config.json

Script:

outputs/phase1_brand_selection.py

### Phase 2 — Data Preparation

AppleSupport data prepared from the full TWCS dataset.

Results:
- AppleSupport outbound tweets: 106,860
- Related inbound customer tweets: 119,895
- Unique customers: 77,431
- Customer → AppleSupport conversations: 83,449
- Usable direct customer → brand interactions: 106,623
- Response coverage: 88.93%
- Average conversation length: 2.717
- Median conversation length: 2
- Maximum conversation length: 266
- Date range: 2016-03-03 to 2017-12-03 UTC

Relevant files:

outputs/phase2/scripts/prepare_applesupport_data.py
outputs/phase2/outputs/applesupport_stats.json
outputs/phase2/reports/PHASE2_DATA_PREPARATION_REPORT.md

Derived conversation data:

outputs/phase2/data/applesupport_conversations.jsonl

Note:
This file is approximately 88 MB. It is currently stored in GitHub, but future large generated files should preferably remain local if reproducible.

### Phase 3A — Intent Discovery

15 candidate intents were discovered.

Classification:
- Classified: 72,598 / 119,895 = 60.55%
- Unclassified: 47,297 = 39.45%
- Multi-intent: 28,505 = 23.77%
- Too short: 9,306 = 7.76%
- Non-support-like: 619 = 0.52%

Main intents include:
- Software/OS updates
- Battery/power/charging
- App Store/media services
- Performance/stability
- Keyboard/text rendering
- Hardware/accessories
- Messaging/calls/FaceTime
- Apple ID/iCloud/account
- Connectivity/network
- Device setup/activation/migration
- Billing/purchases/subscriptions
- Mac support
- Store/orders/repairs
- Support-contact experience
- Apple Watch

Important:
The current taxonomy is a discovery taxonomy, NOT yet a production-quality classifier.

Relevant files:

outputs/phase3/scripts/discover_intents.py
outputs/phase3/taxonomy/intent_taxonomy.json
outputs/phase3/taxonomy/INTENT_TAXONOMY_REPORT.md

## Current Phase

Next task:

Phase 3B — Build a candidate pool of real AppleSupport customer messages for human/golden-set labeling.

Target:
- Approximately 500–1000 candidate examples
- Stratify across discovered intents
- Include ambiguous/unclassified examples
- Include multi-intent examples
- Include different conversation lengths and dates
- Prepare a smaller golden evaluation set later, approximately 150–250 examples

## Critical Rules

1. Do NOT start the project from scratch.
2. Read PROJECT_STATUS.md before making changes.
3. Inspect existing scripts and reports before creating new ones.
4. Use the full local twcs.csv when dataset processing is required.
5. Do not load the entire 493 MB CSV into memory at once.
6. Prefer streaming/chunked processing.
7. Preserve reproducibility.
8. Do not delete existing outputs unless explicitly necessary.
9. Update PROJECT_STATUS.md after completing a major phase.
10. Keep generated large datasets out of GitHub when they can be reproduced from scripts.