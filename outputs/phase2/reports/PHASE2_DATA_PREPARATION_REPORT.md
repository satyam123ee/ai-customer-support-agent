# Phase 2: AppleSupport Data Preparation

## Source and method

- Source: `C:\Users\DELL\Desktop\hiver side project\data\twcs.csv`
- Source rows streamed: 2,811,774
- Source size: 516,508,641 bytes
- Method: two streaming CSV passes; the full file is never loaded into memory.
- Boundary: all outbound AppleSupport tweets plus inbound messages directly linked by the dataset's relationship columns.

## Prepared data statistics

- AppleSupport tweets (outbound): 106,860
- Related inbound customer messages: 119,895
- Unique customers: 77,431
- Customer → AppleSupport conversation components: 83,449
- Brand-only components retained: 0
- Customer messages with a directly observed AppleSupport response: 106,623
- Response coverage: 88.93%
- Average customer-brand conversation length: 2.717
- Median customer-brand conversation length: 2
- Maximum customer-brand conversation length: 266
- Retained-message date range (UTC): 2016-03-03T13:00:08+00:00 to 2017-12-03T23:12:28+00:00

## Data-quality observations

- Invalid inbound flags in source: 0
- Duplicate AppleSupport IDs: 0
- AppleSupport rows missing text: 0; related inbound rows missing text: 0
- Relationship fields are not guaranteed to describe a complete thread. This output retains only observed direct links and does not fabricate missing conversation context.

## Files produced

- `C:\Users\DELL\Documents\Codex\2026-09-12\excellent-the-new-dataset-is-much\outputs\phase2\data\applesupport_conversations.jsonl`
- `C:\Users\DELL\Documents\Codex\2026-09-12\excellent-the-new-dataset-is-much\outputs\phase2\outputs\applesupport_stats.json`

## Scope boundary

This completes only selected-brand extraction and preparation. No RAG, embeddings, LLM agent, intent taxonomy, golden set, or evaluation was created.
