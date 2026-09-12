# Phase 3B: Candidate Pool for Human Labeling

## Objective

This candidate pool is built from real AppleSupport customer messages already prepared in Phase 2 and classified with the Phase 3A taxonomy.

## Sampling strategy

- Read the prepared AppleSupport conversation JSONL without reprocessing the full TWCS CSV.
- Reuse the same phrase-based intent logic from Phase 3A to determine each message's matched intents and primary label.
- Allocate the pool into fixed buckets: 520 primary-intent examples, 60 unclassified, 80 multi-intent, and 40 ambiguous.
- Enforce the buckets as mutually exclusive labels to ensure the final sample matches the intended design.
- Sort within each bucket by strongest evidence, content length, conversation length, and tweet id for reproducibility.
- Apply deterministic quality filtering within each bucket: reject empty records, low-diversity/repeated-token noise, clear mojibake artifacts, exact duplicates, and clearly redundant near-duplicates.
- Backfill every rejected candidate from the same bucket; primary-intent records are backfilled within their own intent quota to preserve all 15 intents.

## Candidate counts

- Target candidate count: 700
- Final candidate count: 700
- Primary-intent examples: 520
- Unclassified examples: 60
- Multi-intent examples: 80
- Ambiguous examples: 40

## Quality filtering

- Rejected candidates considered for replacement: 42
- Replacements applied: 42
- Replacements in ambiguous: 7
- Replacements in multi_intent: 1
- Replacements in primary_intent: 8
- Replacements in unclassified: 26
- clearly_redundant_near_duplicate: 6
- exact_duplicate: 8
- low_token_diversity: 22
- mojibake_or_unicode_artifact: 4
- repeated_token_noise: 2

## Intent coverage summary

- App Store and Apple media services: 58
- Apple ID, iCloud, and account access: 28
- Apple Watch support: 6
- Battery, power, and charging: 50
- Billing, purchases, and subscriptions: 12
- Connectivity and network access: 29
- Device setup, activation, and migration: 17
- Hardware, display, and accessories: 35
- Keyboard, characters, and text rendering: 51
- Mac computer support: 12
- Messages, calls, and FaceTime: 31
- Performance, stability, and unexpected behavior: 49
- Software and operating-system updates: 243
- Store, order, delivery, and repair service: 12
- Support contact and service experience: 7

## Files

- Candidate pool: C:\Users\DELL\Documents\Codex\2026-09-12\excellent-the-new-dataset-is-much\outputs\phase3\candidate_pool\candidate_pool.jsonl
- Source conversations: C:\Users\DELL\Documents\Codex\2026-09-12\excellent-the-new-dataset-is-much\outputs\phase2\data\applesupport_conversations.jsonl

## Notes

- The pool is explicitly designed to support future human labeling and a smaller 150-250 example golden evaluation set.
- The sampled messages remain grounded in real customer-to-brand interactions from the working AppleSupport dataset.
- This Phase 3B output is reproducible from the script and should be re-generated if the source data or taxonomy changes.