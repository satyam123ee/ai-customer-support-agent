# Hiver SDE Intern — Final Evaluation & Proof

## 1. Problem framing
Brand: **AppleSupport**. The system classifies customer issues, retrieves historically similar AppleSupport interactions, drafts only evidence-backed replies, and escalates cases where evidence or risk is not sufficient.

**Not built:** authenticated account actions, refunds, order changes, private customer-data access, or a production UI. Those require tools/permissions absent from TWCS.

## 2. Headline results
- Golden evaluation set: **200** examples.
- TF-IDF retrieval: top-1 intent agreement **59.20%**, top-3 **75.86%**, top-5 **82.18%** on the eligible retrieval evaluation.
- Phase 6 selected usable grounded historical responses for **177/200** examples; 23 had no usable response selected.
- Phase 7: **117 auto-handle (58.5%)**, **83 escalate (41.5%)**.
- All auto-handled cases have grounded responses; all escalated cases have no generated response.

## 3. Baselines
### Trivial baseline
Always return the single most frequent historical response. It has no query-specific retrieval or safety reasoning.

### Simple baseline
Return the raw TF-IDF top-1 historical response with no evidence threshold, response-type filtering, or escalation policy. Top-1 intent agreement is **59.2%** on 174 comparable examples.

### Our system
Adds evidence scoring, conservative grounded-response selection, and explicit escalation safeguards. Response quality is evaluated separately with the LLM judge rather than treating intent agreement as response quality.

## 4. LLM-as-judge and human agreement
Rubric: retrieval relevance (1–5), response grounding (1–5), response quality (1–5), escalation correctness (boolean), and overall acceptability (boolean).

Calibration status: **PENDING — fill the 30-row human calibration CSV, run the LLM judge, then run the agreement script.**

The repository includes a 30-case human calibration sheet and scripts to run an OpenAI-compatible judge and compute exact/within-one agreement, MAE, Pearson correlation, and binary agreement. **No human agreement number is fabricated.**

## 5. Failure analysis
See `outputs/phase8/reports/FAILURE_ANALYSIS.md`. The five observed risk modes are: ambiguous/incomplete requests, billing/payment cases, insufficient historical evidence, account/security-sensitive cases, and order/repair/service cases. These are not all proven model errors; several are deliberate safety escalations.

## 6. What is misleading about my headline number?
The **86.14% Phase 3E escalation-reference agreement** is *not* 86.14% accuracy. It is agreement with an internal deterministic/reference annotation process, and only 166 records were comparable. It is not independently human-validated ground truth. Similarly, retrieval intent agreement is not response quality, and the 58.5% auto-handle rate is not a success rate. The defensible claim is that the pipeline is reproducible and policy-consistent; independent human evaluation is required for quality claims.

## 7. Reproducibility and safety
The Phase 7–9 proof can be rerun from committed intermediate artifacts without the 493 MB raw dataset. `twcs.csv` remains local/ignored. The LLM judge is optional for the deterministic baseline and its API key is never stored in the repository.
