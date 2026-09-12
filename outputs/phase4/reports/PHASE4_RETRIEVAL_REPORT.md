# Phase 4: Historical Retrieval Baseline

## Objective

Establish a deterministic retrieval-only baseline over the Phase 2 AppleSupport conversation corpus. This phase does not generate responses, perform RAG, or make escalation decisions.

## Method

- Retrieval units are individual Phase 2 customer messages with their immediate historical AppleSupport response when available.
- Text is normalized conservatively by removing handles/URLs, lowercasing, tokenizing, and removing a small stop-word list.
- Similarity uses standard-library sparse TF-IDF vectors and cosine similarity.
- Default top_k is 5.
- The same customer message and same conversation are excluded from its own retrieval results to reduce leakage.
- Corpus intent metadata is derived from Phase 3A lexical rules and is used only for diagnostic agreement, not as human truth.

## Metrics

- Golden queries: 200
- Eligible evaluation records: 174
- Excluded null-gold-intent records: 26
- Retrieval failures: 0
- Top-1 intent agreement: 0.5919540229885057
- Top-3 intent agreement: 0.7586206896551724
- Top-5 intent agreement: 0.8218390804597702
- Mean reciprocal rank: 0.6737547892720307
- Average top-1 similarity: 0.4603922555022518
- Average retrieved similarity: 0.41871354782725684

## Inspection samples

Human relevance is pending; the following deterministic intent agreement is not a relevance judgment.

### GS-001
- QUERY: @applesupport MacPro 2013. Yosemite. iTunes 12.7.
- TOP RETRIEVAL: @AppleSupport OS X Yosemite and 10.2.1 ...thank you!
- SIMILARITY: 0.5820503012822607
- GOLD INTENT: None
- RETRIEVED INTENT: None
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-002
- QUERY: @AppleSupport 2/2 song from itunes https://t.co/xJ1yBfxuvJ
- TOP RETRIEVAL: UM I WAS CHARGED ON MY ITUNES FOR A SONG BUT THE SONG ISNT THERE ????? @AppleSupport help
- SIMILARITY: 0.7527154067108326
- GOLD INTENT: None
- RETRIEVED INTENT: app_store_media_services
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-003
- QUERY: @AppleSupport Same for music
- TOP RETRIEVAL: @357201 @AppleSupport Same on the 6😡😡😡😡
- SIMILARITY: 0.7211268363554486
- GOLD INTENT: None
- RETRIEVED INTENT: None
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-004
- QUERY: @AppleSupport Battery down! Please🙏
- TOP RETRIEVAL: tf is up with my battery @AppleSupport
- SIMILARITY: 1.0
- GOLD INTENT: software_update_os
- RETRIEVED INTENT: battery_power_charging
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-005
- QUERY: @AppleSupport yes the battery
- TOP RETRIEVAL: tf is up with my battery @AppleSupport
- SIMILARITY: 1.0
- GOLD INTENT: performance_stability
- RETRIEVED INTENT: battery_power_charging
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-006
- QUERY: @AppleSupport WiFi and streaming.
- TOP RETRIEVAL: @AppleSupport Streaming, and yes it happens on WiFi and cellular,
- SIMILARITY: 0.7338363245295046
- GOLD INTENT: None
- RETRIEVED INTENT: connectivity_network
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-007
- QUERY: @AppleSupport Just Bluetooth Audio
- TOP RETRIEVAL: @AppleSupport No they’re no audio at all. It’s an iPhone 7
- SIMILARITY: 0.7852903232667279
- GOLD INTENT: None
- RETRIEVED INTENT: None
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-008
- QUERY: @AppleSupport AirPort, over WiFi.
- TOP RETRIEVAL: @AppleSupport It used to show the name of the airport, the wifi. Now it only shows ‘airport music’.
- SIMILARITY: 0.7657671097004725
- GOLD INTENT: None
- RETRIEVED INTENT: connectivity_network
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-009
- QUERY: @AppleSupport Standard keyboard; iPhone6s
- TOP RETRIEVAL: @AppleSupport iPhone6s https://t.co/ormsJ8CcZ7
- SIMILARITY: 0.5967875573129073
- GOLD INTENT: None
- RETRIEVED INTENT: None
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

### GS-010
- QUERY: @AppleSupport It doesn't work!
- TOP RETRIEVAL: @AppleSupport Yes and it still doesn’t work
- SIMILARITY: 1.0
- GOLD INTENT: apple_id_icloud_account
- RETRIEVED INTENT: None
- DETERMINISTIC INTENT AGREEMENT: False
- HUMAN RELEVANCE: pending

## Limitations

- Lexical TF-IDF similarity does not understand synonyms, paraphrases, or conversation semantics.
- Retrieved intent metadata is derived from Phase 3A lexical rules and is not human gold truth.
- Same-message and same-conversation records are excluded to reduce source leakage.
- Human relevance judgments remain pending.

## Files

- Corpus: outputs/phase4/retrieval/retrieval_corpus.jsonl
- Results: outputs\phase4\retrieval\retrieval_results.jsonl
- Summary: outputs\phase4\retrieval\retrieval_summary.json
- Validator: work/phase4_validate.py
