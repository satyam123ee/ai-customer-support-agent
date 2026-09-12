#!/usr/bin/env python3
"""Independently validate Phase 3D preliminary annotations and review queue."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "outputs/phase3/golden_set/golden_evaluation_set.jsonl"
ANNOTATIONS_PATH = ROOT / "outputs/phase3/golden_set/golden_set_preliminary_annotations.jsonl"
REVIEW_QUEUE_PATH = ROOT / "outputs/phase3/golden_set/golden_set_review_queue.jsonl"
SUMMARY_PATH = ROOT / "outputs/phase3/golden_set/golden_set_annotation_summary.json"
ANNOTATOR_PATH = ROOT / "outputs/phase3/scripts/annotate_golden_set.py"
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records = []
    errors = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            errors.append(f"{path.name}:{line_number}: {error}")
    return records, errors


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    source, source_errors = load_jsonl(INPUT_PATH)
    annotations, annotation_errors = load_jsonl(ANNOTATIONS_PATH)
    review_queue, review_errors = load_jsonl(REVIEW_QUEUE_PATH)
    source_by_golden = {row["golden_id"]: row for row in source}
    annotation_by_golden = {row.get("golden_id"): row for row in annotations}
    annotation_ids = [row.get("golden_id") for row in annotations]
    message_ids = [row.get("message_id") for row in annotations]
    review_ids = [row.get("golden_id") for row in review_queue]

    missing_source = [golden_id for golden_id in annotation_ids if golden_id not in source_by_golden]
    unexpected_ids = sorted(set(source_by_golden) - set(annotation_by_golden))
    modified_text = [
        golden_id for golden_id, row in annotation_by_golden.items()
        if golden_id in source_by_golden and row.get("text") != source_by_golden[golden_id].get("text")
    ]
    annotation_shape_errors = []
    evaluation_errors = []
    expected_review_ids = []
    for row in annotations:
        golden_id = row.get("golden_id")
        annotation = row.get("preliminary_annotation")
        if not isinstance(annotation, dict):
            annotation_shape_errors.append(golden_id)
            continue
        if annotation.get("confidence") not in ALLOWED_CONFIDENCE:
            annotation_shape_errors.append(golden_id)
        if not isinstance(annotation.get("review_required"), bool):
            annotation_shape_errors.append(golden_id)
        escalation = annotation.get("preliminary_escalation")
        if escalation is not None and not isinstance(escalation, bool):
            annotation_shape_errors.append(golden_id)
        if annotation.get("review_required"):
            expected_review_ids.append(golden_id)
        evaluation = row.get("evaluation", {})
        for field in ("gold_response", "retrieval_relevance", "response_grounding", "response_quality"):
            if evaluation.get(field) is not None:
                evaluation_errors.append((golden_id, field))

    checks = {
        "exactly_200_output_records": len(annotations) == 200,
        "unique_golden_ids": len(annotation_ids) == len(set(annotation_ids)),
        "unique_message_ids": len(message_ids) == len(set(message_ids)),
        "original_text_unchanged": not modified_text,
        "all_source_records_from_phase_3c": not missing_source and not unexpected_ids,
        "no_records_added_or_removed": len(annotations) == len(source) == 200 and not missing_source and not unexpected_ids,
        "all_records_have_preliminary_annotation": len(annotation_shape_errors) == 0,
        "confidence_values_valid": len(annotation_shape_errors) == 0,
        "review_required_is_boolean": len(annotation_shape_errors) == 0,
        "preliminary_escalation_values_valid": len(annotation_shape_errors) == 0,
        "gold_response_remains_null": not any(field == "gold_response" for _, field in evaluation_errors),
        "retrieval_relevance_remains_null": not any(field == "retrieval_relevance" for _, field in evaluation_errors),
        "response_grounding_remains_null": not any(field == "response_grounding" for _, field in evaluation_errors),
        "response_quality_remains_null": not any(field == "response_quality" for _, field in evaluation_errors),
        "review_queue_matches_review_required": sorted(review_ids) == sorted(expected_review_ids),
        "review_queue_has_no_duplicates": len(review_ids) == len(set(review_ids)),
        "jsonl_valid": not source_errors and not annotation_errors and not review_errors,
    }

    before = {path: digest(path) for path in (ANNOTATIONS_PATH, REVIEW_QUEUE_PATH, SUMMARY_PATH)}
    subprocess.run([sys.executable, str(ANNOTATOR_PATH)], cwd=ROOT, check=True, capture_output=True, text=True)
    after = {path: digest(path) for path in (ANNOTATIONS_PATH, REVIEW_QUEUE_PATH, SUMMARY_PATH)}
    checks["deterministic_output_across_repeated_runs"] = before == after

    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    confidence_counts = Counter(row["preliminary_annotation"]["confidence"] for row in annotations)
    intent_counts = Counter(
        row["preliminary_annotation"]["preliminary_intent"]
        for row in annotations
        if row["preliminary_annotation"]["preliminary_intent"] is not None
    )
    escalation_counts = Counter(str(row["preliminary_annotation"]["preliminary_escalation"]).lower() for row in annotations)

    print("total_records", len(annotations))
    print("review_queue_size", len(review_queue))
    print("confidence_counts", dict(sorted(confidence_counts.items())))
    print("preliminary_intent_distribution", dict(sorted(intent_counts.items())))
    print("null_preliminary_intent_count", sum(row["preliminary_annotation"]["preliminary_intent"] is None for row in annotations))
    print("escalation_distribution", {"true": escalation_counts["true"], "false": escalation_counts["false"], "null": escalation_counts["none"]})
    print("summary_review_required_count", summary.get("review_required_count"))
    print("summary_no_review_required_count", summary.get("no_review_required_count"))
    print("validation", checks)
    print("--- first_10_review_queue_examples ---")
    for row in review_queue[:10]:
        print(json.dumps(row, ensure_ascii=False))
    print("--- warnings_and_limitations ---")
    print("Preliminary annotations are deterministic heuristics, not human gold labels.")
    print("Phase 3A-derived intents are discovery labels and remain subject to human review.")
    print("No model answers or retrieval/response judgments were generated.")

    if not all(checks.values()):
        raise SystemExit("Phase 3D validation failed")


if __name__ == "__main__":
    main()
