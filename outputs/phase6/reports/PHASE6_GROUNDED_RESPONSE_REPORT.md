# Phase 6: Grounded AI Response Generation

## Architecture

Golden query -> Phase 4 retrieval candidates -> Phase 5 deterministic evidence signals -> conservative evidence selection -> verbatim historical response or null.

## Generation method

- Select the highest-scoring Phase 5 candidate with a response, score >= 0.35, and response type `diagnostic_question` or `direct_guidance`.
- Copy the selected historical AppleSupport response verbatim.
- Do not invent troubleshooting steps, product claims, escalation labels, or human quality labels.
- Generic routing-only responses are not emitted as generated answers.

## Results

- Total queries: 200
- Usable evidence selected: 177
- Weak/no usable evidence: 23
- Responses copied verbatim: 177
- Needs escalation true: 10
- Needs escalation false: 177
- Needs escalation null: 13

## Grounding and safety diagnostics

- grounded_historical_response: 177
- insufficient_historical_evidence: 23
- response_type_diagnostic_question: 143
- response_type_direct_guidance: 34

No human response-quality labels were generated. Phase 6 is a deterministic prototype only; Phase 7 is not started.

## Limitations

- This is a deterministic historical-response copying baseline, not an LLM response generator.
- A historically useful response may still be wrong for the current query; semantic human review remains necessary.
- Generic routing responses are not selected as generated answers.
- No external API or LLM was used.

## Files

- Responses: outputs\phase6\generation\golden_grounded_responses.jsonl
- Summary: outputs\phase6\generation\phase6_generation_summary.json
- Validator: work/phase6_validate.py
