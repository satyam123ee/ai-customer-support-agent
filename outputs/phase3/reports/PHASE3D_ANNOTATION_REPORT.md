# Phase 3D: Fast Golden-Set Annotation

## Objective

Generate deterministic preliminary annotations and route only uncertain records to a human review queue. These preliminary annotations are not human gold labels.

## Methodology

- Primary-intent records inherit their existing Phase 3A-derived `primary_intent` as a preliminary label only.
- Non-primary records receive a preliminary intent only when exactly one existing Phase 3A intent has at least two matching evidence patterns.
- Confidence is derived from bucket and deterministic evidence counts, never from intuition or a model.
- Ambiguous, multi-intent, unresolved unclassified, low-confidence, conflicting, and incomplete records enter the review queue.
- Escalation is only a preliminary deterministic recommendation; insufficient evidence produces null.
- Original source text, source metadata, and the original `evaluation` placeholders are preserved.

## Results

- Total records: 200
- Review required: 50
- No review required: 150
- High confidence: 150
- Medium confidence: 0
- Low confidence: 50

## Status

Preliminary heuristic labels are not final human gold labels. Human review must resolve the review queue before evaluation metrics are treated as gold-standard results.

## Files

- Preliminary annotations: outputs\phase3\golden_set\golden_set_preliminary_annotations.jsonl
- Review queue: outputs\phase3\golden_set\golden_set_review_queue.jsonl
- Summary: outputs\phase3\golden_set\golden_set_annotation_summary.json
- Validator: work/phase3d_validate.py

## Limitations

- Phase 3A is a discovery taxonomy and its labels are not human-validated ground truth.
- Unclassified messages remain null unless the existing deterministic evidence is strong.
- Escalation values are preliminary recommendations, not operational decisions.
- Gold responses and retrieval, grounding, and response-quality judgments are intentionally absent.
