# Phase 5: Historical-Evidence Evaluation

## Objective

Evaluate whether Phase 4 historical retrieval results contain deterministic evidence useful for later grounded response work. This is not a human relevance evaluation and does not generate answers.

## Inputs

- Phase 3E annotated golden set.
- Phase 4 retrieval results and summary.
- Phase 2 conversation corpus through the Phase 4 retrieval outputs.
- Phase 3A taxonomy metadata through the Phase 4 retrieval outputs.

## Deterministic scoring

- Historical response availability: 0.35.
- Query/customer lexical overlap: 0.25.
- Query/historical-response lexical overlap: 0.25.
- Curated Phase 3E gold-intent agreement is retained as diagnostic metadata only and is excluded from the score.
- Response-type diagnostics classify responses as none, generic_routing, diagnostic_question, direct_guidance, or acknowledgement_or_other.
- Strong evidence is score >= 0.65; moderate evidence is >= 0.35; otherwise weak. The 0.35 cutoff is provisional and heuristic, not calibrated.
- These scores and flags are transparent evidence signals, not human relevance labels.

## Results

- Total golden queries: 200
- Eligible queries: 174
- Excluded null-gold-intent queries: 26
- Total retrieved candidates: 1000
- Candidates with historical responses: 883
- Queries with no usable historical response: 1

## Examples

The examples below show deterministic evidence only. Human relevance remains pending.

### GS-001
- QUERY: @applesupport MacPro 2013. Yosemite. iTunes 12.7.
- TOP RETRIEVAL: @AppleSupport OS X Yosemite and 10.2.1 ...thank you!
- SIMILARITY: 0.5820503012822607
- EVIDENCE SCORE: 0.475
- RESPONSE TYPE: acknowledgement_or_other
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-002
- QUERY: @AppleSupport 2/2 song from itunes https://t.co/xJ1yBfxuvJ
- TOP RETRIEVAL: UM I WAS CHARGED ON MY ITUNES FOR A SONG BUT THE SONG ISNT THERE ????? @AppleSupport help
- SIMILARITY: 0.7527154067108326
- EVIDENCE SCORE: 0.508114
- RESPONSE TYPE: diagnostic_question
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-003
- QUERY: @AppleSupport Same for music
- TOP RETRIEVAL: @357201 @AppleSupport Same on the 6😡😡😡😡
- SIMILARITY: 0.7211268363554486
- EVIDENCE SCORE: 0.526777
- RESPONSE TYPE: generic_routing
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-004
- QUERY: @AppleSupport Battery down! Please🙏
- TOP RETRIEVAL: tf is up with my battery @AppleSupport
- SIMILARITY: 1.0
- EVIDENCE SCORE: 0.702062
- RESPONSE TYPE: diagnostic_question
- FLAGS: historical_response_available, strong_query_customer_overlap, response_lexically_related, curated_intent_mismatch_or_unavailable, strong_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-005
- QUERY: @AppleSupport yes the battery
- TOP RETRIEVAL: tf is up with my battery @AppleSupport
- SIMILARITY: 1.0
- EVIDENCE SCORE: 0.702062
- RESPONSE TYPE: diagnostic_question
- FLAGS: historical_response_available, strong_query_customer_overlap, response_lexically_related, curated_intent_mismatch_or_unavailable, strong_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-006
- QUERY: @AppleSupport WiFi and streaming.
- TOP RETRIEVAL: @AppleSupport Streaming, and yes it happens on WiFi and cellular,
- SIMILARITY: 0.7338363245295046
- EVIDENCE SCORE: 0.589277
- RESPONSE TYPE: diagnostic_question
- FLAGS: historical_response_available, strong_query_customer_overlap, response_lexically_related, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-007
- QUERY: @AppleSupport Just Bluetooth Audio
- TOP RETRIEVAL: @AppleSupport No they’re no audio at all. It’s an iPhone 7
- SIMILARITY: 0.7852903232667279
- EVIDENCE SCORE: 0.526777
- RESPONSE TYPE: diagnostic_question
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-008
- QUERY: @AppleSupport AirPort, over WiFi.
- TOP RETRIEVAL: @AppleSupport It used to show the name of the airport, the wifi. Now it only shows ‘airport music’.
- SIMILARITY: 0.7657671097004725
- EVIDENCE SCORE: 0.467851
- RESPONSE TYPE: generic_routing
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-009
- QUERY: @AppleSupport Standard keyboard; iPhone6s
- TOP RETRIEVAL: @AppleSupport iPhone6s https://t.co/ormsJ8CcZ7
- SIMILARITY: 0.5967875573129073
- EVIDENCE SCORE: 0.494338
- RESPONSE TYPE: generic_routing
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, intent_metric_ineligible, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

### GS-010
- QUERY: @AppleSupport It doesn't work!
- TOP RETRIEVAL: @AppleSupport Yes and it still doesn’t work
- SIMILARITY: 1.0
- EVIDENCE SCORE: 0.6
- RESPONSE TYPE: generic_routing
- FLAGS: historical_response_available, strong_query_customer_overlap, no_response_overlap, curated_intent_mismatch_or_unavailable, moderate_deterministic_evidence
- HUMAN RELEVANCE: pending

## Limitations

- Lexical overlap does not establish semantic relevance or answer correctness.
- Retrieved intent metadata is Phase 3A heuristic evidence, not human truth.
- Null gold-intent queries are excluded from intent-based metrics but still receive evidence signals.
- Human relevance judgments remain pending.

## Use in grounded response work

This layer identifies which retrieved examples contain explicit historical-response and lexical evidence. A later grounded response system can use these signals for inspection and candidate selection, but must still verify semantic relevance and avoid treating retrieved text as an answer without appropriate grounding.

## Files

- Evidence results: outputs\phase5\evidence\historical_evidence_results.jsonl
- Summary: outputs\phase5\evidence\historical_evidence_summary.json
- Validator: work/phase5_validate.py
