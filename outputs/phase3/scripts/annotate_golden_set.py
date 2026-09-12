#!/usr/bin/env python3
"""Create preliminary Phase 3D annotations without claiming human gold labels."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_candidate_pool import classify  # noqa: E402

INPUT_PATH = Path("outputs/phase3/golden_set/golden_evaluation_set.jsonl")
ANNOTATIONS_PATH = Path("outputs/phase3/golden_set/golden_set_preliminary_annotations.jsonl")
REVIEW_QUEUE_PATH = Path("outputs/phase3/golden_set/golden_set_review_queue.jsonl")
SUMMARY_PATH = Path("outputs/phase3/golden_set/golden_set_annotation_summary.json")
REPORT_PATH = Path("outputs/phase3/reports/PHASE3D_ANNOTATION_REPORT.md")
CONFIDENCES = {"high", "medium", "low"}
ESCALATION_PATTERNS = [
    ("financial loss, refund, or disputed charge", r"\b(?:refund|charged|charge|billing|payment|subscription|credit card|money)\b"),
    ("account access or security concern", r"\b(?:stolen|verification|password|disabled|hack|security|account recovery)\b"),
    ("repair, warranty, store, or appointment issue", r"\b(?:repair|warranty|genius bar|appointment|store|replacement)\b"),
    ("explicit complaint or manager request", r"\b(?:manager|complaint|customer service|employee)\b|\b(?:legal|lawsuit)\b"),
    ("safety or emergency indicator", r"\b(?:911|fire|smoke|overheat|overheating|danger|safety)\b"),
]


def normalized(text: str) -> str:
    return " ".join((text or "").lower().split())


def strong_match(matches: list[dict]) -> tuple[str | None, int]:
    if len(matches) != 1:
        return None, 0
    match = matches[0]
    evidence_count = len(match["evidence_patterns"])
    if evidence_count < 2:
        return None, evidence_count
    return match["intent_id"], evidence_count


def classify_preliminary(record: dict) -> tuple[str | None, str, list[dict], list[str]]:
    text = record.get("text", "")
    matches, classifier_primary = classify(text)
    evidence_count = sum(len(match["evidence_patterns"]) for match in matches)
    bucket = record.get("bucket")
    existing_primary = record.get("primary_intent")

    if bucket == "primary_intent":
        preliminary = existing_primary
        confidence = "high" if evidence_count >= 2 else "medium"
    else:
        preliminary, strong_evidence_count = strong_match(matches)
        confidence = "medium" if preliminary and strong_evidence_count >= 2 else "low"
        if bucket == "multi_intent":
            preliminary = None
            confidence = "low"
        if bucket == "unclassified" and not preliminary:
            preliminary = None
            confidence = "low"

    reasons = []
    if bucket == "ambiguous":
        reasons.append("ambiguous bucket")
    if bucket == "multi_intent":
        reasons.append("multi-intent bucket")
    if bucket == "unclassified" and preliminary is None:
        reasons.append("unclassified without strong deterministic intent evidence")
    if confidence == "low":
        reasons.append("low deterministic confidence")
    if record.get("content_word_count", 0) <= 3:
        reasons.append("message is too incomplete for reliable intent determination")
    matched_ids = {match["intent_id"] for match in matches}
    if preliminary and matched_ids and preliminary not in matched_ids:
        reasons.append("preliminary intent conflicts with text evidence")
    if bucket == "primary_intent" and classifier_primary and existing_primary != classifier_primary:
        reasons.append("inherited primary intent conflicts with classifier evidence")
    return preliminary, confidence, matches, reasons


def escalation_recommendation(text: str, bucket: str, confidence: str) -> tuple[bool | None, str]:
    value = normalized(text)
    matched_reasons = [reason for reason, pattern in ESCALATION_PATTERNS if re.search(pattern, value, re.I)]
    if matched_reasons:
        return True, "Deterministic indicator: " + "; ".join(matched_reasons) + "."
    if bucket == "primary_intent" and confidence == "high":
        return False, "No deterministic escalation indicator in a high-confidence routine support request."
    return None, "Insufficient deterministic evidence for an escalation recommendation."


def annotate_record(record: dict) -> tuple[dict, dict]:
    preliminary, confidence, matches, review_reasons = classify_preliminary(record)
    escalation, escalation_reason = escalation_recommendation(record.get("text", ""), record.get("bucket", ""), confidence)
    review_required = bool(review_reasons)
    output = dict(record)
    output["preliminary_annotation"] = {
        "preliminary_intent": preliminary,
        "confidence": confidence,
        "review_required": review_required,
        "preliminary_escalation": escalation,
        "preliminary_escalation_reason": escalation_reason,
        "annotation_method": "deterministic_heuristic",
    }
    review_record = {
        "golden_id": record.get("golden_id"),
        "message_id": record.get("message_id"),
        "text": record.get("text"),
        "bucket": record.get("bucket"),
        "existing_primary_intent": record.get("primary_intent"),
        "preliminary_intent": preliminary,
        "confidence": confidence,
        "reason_for_review": "; ".join(review_reasons),
    }
    return output, review_record


def build(input_path: Path, annotations_path: Path, review_path: Path, summary_path: Path, report_path: Path) -> dict:
    records = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    annotated = []
    review_queue = []
    for record in records:
        annotated_record, review_record = annotate_record(record)
        annotated.append(annotated_record)
        if annotated_record["preliminary_annotation"]["review_required"]:
            review_queue.append(review_record)

    annotations_path.parent.mkdir(parents=True, exist_ok=True)
    with annotations_path.open("w", encoding="utf-8") as stream:
        for record in annotated:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    with review_path.open("w", encoding="utf-8") as stream:
        for record in review_queue:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    confidence_counts = Counter(record["preliminary_annotation"]["confidence"] for record in annotated)
    bucket_counts = Counter(record["bucket"] for record in annotated)
    intent_counts = Counter(
        record["preliminary_annotation"]["preliminary_intent"]
        for record in annotated
        if record["preliminary_annotation"]["preliminary_intent"] is not None
    )
    null_intents = sum(
        record["preliminary_annotation"]["preliminary_intent"] is None
        for record in annotated
    )
    escalation_counts = Counter(
        str(record["preliminary_annotation"]["preliminary_escalation"]).lower()
        for record in annotated
    )
    summary = {
        "phase": "3D",
        "total_records": len(annotated),
        "source_file": str(input_path),
        "preliminary_high_confidence_count": confidence_counts["high"],
        "preliminary_medium_confidence_count": confidence_counts["medium"],
        "preliminary_low_confidence_count": confidence_counts["low"],
        "review_required_count": len(review_queue),
        "no_review_required_count": len(annotated) - len(review_queue),
        "counts_by_bucket": dict(sorted(bucket_counts.items())),
        "counts_by_preliminary_intent": dict(sorted(intent_counts.items())),
        "null_preliminary_intent_count": null_intents,
        "escalation_counts": {
            "true": escalation_counts["true"],
            "false": escalation_counts["false"],
            "null": escalation_counts["none"],
        },
        "methodology": {
            "annotation_method": "deterministic_heuristic",
            "primary_intent_rule": "Primary-intent records inherit the existing Phase 3A-derived primary_intent as preliminary only.",
            "inference_rule": "Non-primary records receive an intent only when exactly one existing Phase 3A intent matches at least two evidence patterns.",
            "confidence_rule": "High means primary-intent evidence has at least two matched patterns; medium means inherited primary evidence is present but weaker or a non-primary record has strong single-intent evidence; low means no strong deterministic intent exists.",
            "review_rule": "Review ambiguous, multi-intent, unresolved unclassified, low-confidence, conflicting, or too-incomplete records.",
            "escalation_rule": "Recommend true only for explicit deterministic financial, security, repair, complaint, manager, legal, safety, or emergency indicators; recommend false only for high-confidence routine primary-intent requests without those indicators; otherwise null.",
        },
        "human_annotation_status": "Preliminary heuristic annotations only; these are not human gold labels.",
        "limitations": [
            "Phase 3A is a discovery taxonomy and its labels are not human-validated ground truth.",
            "Unclassified messages remain null unless the existing deterministic evidence is strong.",
            "Escalation values are preliminary recommendations, not operational decisions.",
            "Gold responses and retrieval, grounding, and response-quality judgments are intentionally absent.",
        ],
        "output_files": {
            "preliminary_annotations": str(annotations_path),
            "review_queue": str(review_path),
            "summary": str(summary_path),
            "report": str(report_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Phase 3D: Fast Golden-Set Annotation",
        "",
        "## Objective",
        "",
        "Generate deterministic preliminary annotations and route only uncertain records to a human review queue. These preliminary annotations are not human gold labels.",
        "",
        "## Methodology",
        "",
        "- Primary-intent records inherit their existing Phase 3A-derived `primary_intent` as a preliminary label only.",
        "- Non-primary records receive a preliminary intent only when exactly one existing Phase 3A intent has at least two matching evidence patterns.",
        "- Confidence is derived from bucket and deterministic evidence counts, never from intuition or a model.",
        "- Ambiguous, multi-intent, unresolved unclassified, low-confidence, conflicting, and incomplete records enter the review queue.",
        "- Escalation is only a preliminary deterministic recommendation; insufficient evidence produces null.",
        "- Original source text, source metadata, and the original `evaluation` placeholders are preserved.",
        "",
        "## Results",
        "",
        f"- Total records: {len(annotated)}",
        f"- Review required: {len(review_queue)}",
        f"- No review required: {len(annotated) - len(review_queue)}",
        f"- High confidence: {confidence_counts['high']}",
        f"- Medium confidence: {confidence_counts['medium']}",
        f"- Low confidence: {confidence_counts['low']}",
        "",
        "## Status",
        "",
        "Preliminary heuristic labels are not final human gold labels. Human review must resolve the review queue before evaluation metrics are treated as gold-standard results.",
        "",
        "## Files",
        "",
        f"- Preliminary annotations: {annotations_path}",
        f"- Review queue: {review_path}",
        f"- Summary: {summary_path}",
        f"- Validator: work/phase3d_validate.py",
        "",
        "## Limitations",
        "",
        *[f"- {limitation}" for limitation in summary["limitations"]],
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS_PATH)
    parser.add_argument("--review-queue", type=Path, default=REVIEW_QUEUE_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    summary = build(args.input, args.annotations, args.review_queue, args.summary, args.report)
    print(json.dumps({
        "phase": summary["phase"],
        "total_records": summary["total_records"],
        "review_required_count": summary["review_required_count"],
        "preliminary_annotations": str(args.annotations),
        "review_queue": str(args.review_queue),
    }, indent=2))


if __name__ == "__main__":
    main()
