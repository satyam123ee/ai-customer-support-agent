#!/usr/bin/env python3
"""Independently validate Phase 3E review resolution outputs."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "outputs/phase3/golden_set/golden_evaluation_set.jsonl"
REVIEW_PATH = ROOT / "outputs/phase3/golden_set/golden_set_review_queue.jsonl"
ANNOTATED_PATH = ROOT / "outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl"
DECISIONS_PATH = ROOT / "outputs/phase3/golden_set/golden_set_annotation_decisions.jsonl"
SUMMARY_PATH = ROOT / "outputs/phase3/golden_set/golden_set_annotation_summary.json"
CONVERSATIONS_PATH = ROOT / "outputs/phase2/data/applesupport_conversations.jsonl"
TAXONOMY_PATH = ROOT / "outputs/phase3/taxonomy/intent_taxonomy.json"
RESOLVER_PATH = ROOT / "outputs/phase3/scripts/resolve_review_queue.py"
VALID_STATUSES = {"resolved_from_context", "resolved_from_text", "genuinely_ambiguous", "insufficient_evidence"}
VALID_CONFIDENCES = {"high", "medium", "low"}


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records, errors = [], []
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


def historical_response_evidence(annotated: list[dict]) -> tuple[int, list[str]]:
    targets = {
        row["message_id"]: row["evaluation"].get("gold_response")
        for row in annotated
        if row.get("evaluation", {}).get("gold_response") is not None
    }
    found = 0
    fabricated = []
    if not targets:
        return 0, fabricated
    with CONVERSATIONS_PATH.open("r", encoding="utf-8") as stream:
        for line in stream:
            conversation = json.loads(line)
            messages = conversation.get("messages", [])
            for index, message in enumerate(messages):
                message_id = str(message.get("tweet_id"))
                if message_id not in targets:
                    continue
                if index + 1 < len(messages) and messages[index + 1].get("role") == "brand_response":
                    response = messages[index + 1]
                    if response.get("text") == targets[message_id]:
                        found += 1
                    else:
                        fabricated.append(message_id)
                else:
                    fabricated.append(message_id)
    missing = set(targets) - {
        row["message_id"] for row in annotated if row.get("evaluation", {}).get("gold_response") is not None and row["message_id"] not in fabricated
    }
    fabricated.extend(sorted(missing))
    return found, fabricated


def main() -> None:
    golden, golden_errors = load_jsonl(GOLDEN_PATH)
    review, review_errors = load_jsonl(REVIEW_PATH)
    annotated, annotated_errors = load_jsonl(ANNOTATED_PATH)
    decisions, decision_errors = load_jsonl(DECISIONS_PATH)
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    intent_ids = {item["intent_id"] for item in taxonomy["intents"]}
    source_by_id = {row["golden_id"]: row for row in golden}
    annotated_by_id = {row.get("golden_id"): row for row in annotated}
    review_ids = {row.get("golden_id") for row in review}
    decision_ids = [row.get("golden_id") for row in decisions]

    invalid_intents = []
    invalid_alternatives = []
    invalid_status = []
    invalid_confidence = []
    invalid_escalation = []
    modified_text = []
    null_retrieval = True
    duplicate_records = len([row.get("golden_id") for row in annotated]) != len({row.get("golden_id") for row in annotated})
    for row in annotated:
        golden_id = row.get("golden_id")
        evaluation = row.get("evaluation", {})
        gold_intent = evaluation.get("gold_intent")
        if gold_intent is not None and gold_intent not in intent_ids:
            invalid_intents.append(golden_id)
        alternatives = evaluation.get("acceptable_intents", [])
        if any(intent not in intent_ids for intent in alternatives):
            invalid_alternatives.append(golden_id)
        if evaluation.get("annotation_status") not in VALID_STATUSES:
            invalid_status.append(golden_id)
        if evaluation.get("annotation_confidence") not in VALID_CONFIDENCES:
            invalid_confidence.append(golden_id)
        escalation = evaluation.get("should_escalate")
        if escalation is not None and not isinstance(escalation, bool):
            invalid_escalation.append(golden_id)
        if evaluation.get("retrieval_relevance") is not None or evaluation.get("response_grounding") is not None or evaluation.get("response_quality") is not None:
            null_retrieval = False
        if golden_id in source_by_id and row.get("text") != source_by_id[golden_id].get("text"):
            modified_text.append(golden_id)

    response_count, fabricated_responses = historical_response_evidence(annotated)
    checks = {
        "exactly_200_records": len(annotated) == 200,
        "unique_golden_id": not duplicate_records,
        "unique_message_id": len([row.get("message_id") for row in annotated]) == len({row.get("message_id") for row in annotated}),
        "original_text_unchanged": not modified_text,
        "all_records_from_phase_3c": set(annotated_by_id) == set(source_by_id) and not (set(source_by_id) - set(annotated_by_id)),
        "all_annotation_fields_present": len(invalid_status) == 0 and len(invalid_confidence) == 0,
        "gold_intents_valid": not invalid_intents,
        "acceptable_intents_valid": not invalid_alternatives,
        "escalation_values_valid": not invalid_escalation,
        "retrieval_fields_null": null_retrieval,
        "no_fabricated_gold_responses": not fabricated_responses and response_count == sum(row.get("evaluation", {}).get("gold_response") is not None for row in annotated),
        "no_duplicate_decisions": len(decision_ids) == len(set(decision_ids)),
        "decisions_cover_review_queue": set(decision_ids) == review_ids,
        "jsonl_valid": not golden_errors and not review_errors and not annotated_errors and not decision_errors,
    }

    before = {path: digest(path) for path in (ANNOTATED_PATH, DECISIONS_PATH, SUMMARY_PATH)}
    subprocess.run([sys.executable, str(RESOLVER_PATH)], cwd=ROOT, check=True, capture_output=True, text=True)
    after = {path: digest(path) for path in (ANNOTATED_PATH, DECISIONS_PATH, SUMMARY_PATH)}
    checks["deterministic_output_across_repeated_runs"] = before == after

    statuses = Counter(row["evaluation"]["annotation_status"] for row in annotated)
    intents = Counter(row["evaluation"]["gold_intent"] for row in annotated if row["evaluation"]["gold_intent"] is not None)
    escalations = Counter(str(row["evaluation"]["should_escalate"]).lower() for row in annotated)
    print("total_records", len(annotated))
    print("review_queue_records", len(review))
    print("resolved_count", statuses["resolved_from_context"] + statuses["resolved_from_text"])
    print("unresolved_count", statuses["genuinely_ambiguous"] + statuses["insufficient_evidence"])
    print("status_counts", dict(sorted(statuses.items())))
    print("gold_intent_distribution", dict(sorted(intents.items())))
    print("escalation_distribution", {"true": escalations["true"], "false": escalations["false"], "null": escalations["none"]})
    print("historical_response_count", response_count)
    print("remaining_null_fields", {
        "gold_intent": sum(row["evaluation"]["gold_intent"] is None for row in annotated),
        "gold_response": sum(row["evaluation"]["gold_response"] is None for row in annotated),
        "should_escalate": sum(row["evaluation"]["should_escalate"] is None for row in annotated),
        "retrieval_relevance": len(annotated),
        "response_grounding": len(annotated),
        "response_quality": len(annotated),
    })
    print("validation", checks)
    print("--- warnings_and_limitations ---")
    print("Phase 3A-derived and Phase 3E-resolved intents are provenance-tracked and are not silently treated as perfect ground truth.")
    print("Historical gold responses are only copied from exact observed brand_response records; otherwise gold_response is null.")
    print("No retrieval, RAG, response-quality, or human-review metrics were generated.")
    if not all(checks.values()):
        raise SystemExit("Phase 3E validation failed")


if __name__ == "__main__":
    main()
