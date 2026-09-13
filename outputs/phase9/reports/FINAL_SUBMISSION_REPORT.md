# Hiver SDE Intern — Final Evaluation & Proof

## Scope
Completed deterministic baseline workflow for the AppleSupport slice of the Customer Support on Twitter dataset through Phase 9. No human validation is claimed where labels are absent.

## Completed phases
- Phase 1: Brand selection — AppleSupport.
- Phase 2: Streaming/chunked data preparation.
- Phase 3A–3E: intent discovery, candidate pool, golden set, preliminary annotation, and deterministic review-queue resolution.
- Phase 4: TF-IDF historical retrieval baseline.
- Phase 5: deterministic historical-evidence scoring.
- Phase 6: grounded historical-response baseline.
- Phase 7: conservative auto-handle vs escalation decision system.
- Phase 8: deterministic evaluation/proof and preliminary-reference comparison.
- Phase 9: final submission/evidence package.

## Phase 7 results
- Total queries: 200
- Auto-handle: 117 (58.5%)
- Escalate: 83 (41.5%)
- Escalation reasons: {"account_or_security_sensitive": 14, "ambiguous_request": 25, "billing_or_payment_case_specific": 18, "insufficient_historical_evidence": 15, "order_repair_case_specific": 11}

## Phase 8 proof
- All 200 queries covered: True
- Auto-handled responses present: True
- Escalations contain no generated response: True
- Preliminary Phase 3E reference agreement: 86.14% across 166 comparable records. Diagnostic only; not accuracy.

## Human evaluation required
Retrieval relevance, response quality, response grounding correctness, and escalation correctness still require human evaluation. Deterministic checks establish provenance, consistency, reproducibility, and policy execution; they do not prove every response is correct.

## Submission safety
- `twcs.csv` is not included.
- No external API or LLM dependency is required for this baseline.
- Phase 1–6 artifacts are treated as immutable inputs.
- Review the final diff before committing/pushing.
