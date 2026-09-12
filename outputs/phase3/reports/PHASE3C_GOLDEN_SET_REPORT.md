# Phase 3C: Golden Evaluation Set

## Objective

Create a manually reviewable evaluation set from the locked Phase 3B candidate pool. This phase does not generate model answers, gold labels, retrieval judgments, response judgments, or escalation decisions.

## Selection methodology

- Source: the final 700-record Phase 3B candidate pool.
- Target: exactly 200 records.
- Random seed: 20260912.
- Allocation is deliberately coverage-first rather than proportional: 150 primary-intent records, 20 unclassified records, 15 multi-intent records, and 15 ambiguous records.
- Primary-intent quotas guarantee representation for every intent, including all 6 available Apple Watch primary-intent records.
- Candidates are ranked by difficulty-signal coverage, then resolved with seeded random tie-breaking and stable tweet IDs.
- Exact duplicates and clearly redundant near-duplicates are excluded against the complete selected set.
- Original source text and source metadata are copied without modification.

## Final counts

- Total golden examples: 200
- primary_intent: 150
- unclassified: 20
- multi_intent: 15
- ambiguous: 15
- Multi-intent examples: 15
- Ambiguous examples: 15

## Primary-intent distribution

- app_store_media_services: 16
- apple_id_icloud_account: 10
- apple_watch: 6
- battery_power_charging: 12
- billing_purchases_subscriptions: 9
- connectivity_network: 12
- device_setup_activation_migration: 10
- hardware_accessories: 10
- keyboard_text_rendering: 11
- mac_computer: 8
- messaging_calls_facetime: 11
- performance_stability: 13
- software_update_os: 37
- store_orders_repairs: 8
- support_contact_experience: 7

## Quality checks

- JSONL output is generated with one JSON object per line.
- Evaluation fields are null or empty placeholders and contain no guessed labels.
- No model answers, retrieval judgments, grounding judgments, response-quality judgments, or escalation decisions were generated.
- Independent validation is performed by work/phase3c_validate.py.

## Limitations

- Primary intents reflect Phase 3A discovery labels and are not human gold labels.
- Unclassified records intentionally have no guessed intent label.
- Difficulty tags are sampling metadata, not evaluation judgments.
- The golden set is drawn only from the 700-record Phase 3B pool.

## Files

- Golden set: outputs\phase3\golden_set\golden_evaluation_set.jsonl
- Summary: outputs\phase3\golden_set\golden_set_summary.json
- Builder: outputs/phase3/scripts/build_golden_set.py
