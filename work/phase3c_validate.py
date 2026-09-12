#!/usr/bin/env python3
"""Independent validation for the Phase 3C golden evaluation set."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

SOURCE_PATH = Path("outputs/phase3/candidate_pool/candidate_pool.jsonl")
GOLDEN_PATH = Path("outputs/phase3/golden_set/golden_evaluation_set.jsonl")
EXPECTED_INTENTS = {
    "app_store_media_services",
    "apple_id_icloud_account",
    "apple_watch",
    "battery_power_charging",
    "billing_purchases_subscriptions",
    "connectivity_network",
    "device_setup_activation_migration",
    "hardware_accessories",
    "keyboard_text_rendering",
    "mac_computer",
    "messaging_calls_facetime",
    "performance_stability",
    "software_update_os",
    "store_orders_repairs",
    "support_contact_experience",
}
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "when", "while", "for", "with", "without",
    "this", "that", "these", "those", "from", "into", "onto", "over", "under", "about", "after",
    "before", "between", "through", "during", "because", "please", "help", "my", "your", "our", "i",
    "me", "you", "we", "they", "them", "is", "are", "was", "were", "be", "been", "being", "to", "of",
    "in", "on", "at", "it", "its", "as", "so", "not", "no", "yes", "can", "could", "would", "should",
    "have", "has", "had", "do", "does", "did", "im", "apple", "support", "thanks", "thank", "hi", "hello",
    "issue", "problem", "fix", "bug", "app", "apps", "phone", "iphone", "ipad", "watch", "just", "very",
    "really", "too", "also", "still", "again", "out", "up", "down", "all", "any", "some", "few", "many",
    "more", "most", "ever",
}


def canonical(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+|#\w+", " ", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text)).strip()


def content(text: str) -> set[str]:
    return {token for token in canonical(text).split() if len(token) > 2 and token not in STOP_WORDS}


def near_duplicate(left: set[str], right: set[str]) -> bool:
    if len(left) < 6 or len(right) < 6:
        return False
    overlap = len(left & right)
    return overlap >= 4 and overlap / min(len(left), len(right)) >= 0.7 and len(left | right) >= 6


def load_jsonl(path: Path) -> tuple[list[dict], list[str]]:
    records = []
    errors = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            errors.append(f"line {line_number}: {error}")
    return records, errors


def main() -> None:
    source, source_errors = load_jsonl(SOURCE_PATH)
    golden, golden_errors = load_jsonl(GOLDEN_PATH)
    source_by_id = {row["tweet_id"]: row for row in source}
    golden_ids = [row.get("golden_id") for row in golden]
    message_ids = [row.get("message_id") for row in golden]
    texts = [row.get("text") for row in golden]

    exact_duplicate_groups = Counter(canonical(text) for text in texts if canonical(text))
    exact_duplicate_count = sum(count for count in exact_duplicate_groups.values() if count > 1)
    near_duplicate_pairs = []
    content_sets = [content(text) for text in texts]
    for left_index in range(len(content_sets)):
        for right_index in range(left_index + 1, len(content_sets)):
            if near_duplicate(content_sets[left_index], content_sets[right_index]):
                near_duplicate_pairs.append((left_index, right_index))

    missing_source = [row.get("message_id") for row in golden if row.get("message_id") not in source_by_id]
    modified_text = [
        row.get("message_id") for row in golden
        if row.get("message_id") in source_by_id and row.get("text") != source_by_id[row["message_id"]].get("text")
    ]
    intent_counts = Counter(row.get("primary_intent") for row in golden if row.get("primary_intent"))
    bucket_counts = Counter(row.get("bucket") for row in golden)
    placeholder_violations = []
    for row in golden:
        evaluation = row.get("evaluation", {})
        if any(evaluation.get(key) not in (None, []) for key in evaluation):
            placeholder_violations.append(row.get("golden_id"))

    checks = {
        "exactly_200_records": len(golden) == 200,
        "jsonl_valid": not source_errors and not golden_errors,
        "unique_golden_ids": len(golden_ids) == len(set(golden_ids)),
        "unique_message_ids": len(message_ids) == len(set(message_ids)),
        "no_exact_duplicate_texts": exact_duplicate_count == 0,
        "no_obvious_near_duplicates": not near_duplicate_pairs,
        "all_15_primary_intents_present": EXPECTED_INTENTS.issubset(intent_counts),
        "bucket_counts_sum_to_200": sum(bucket_counts.values()) == 200,
        "every_source_record_exists": not missing_source,
        "original_text_unmodified": not modified_text,
        "evaluation_fields_are_placeholders": not placeholder_violations,
    }

    print("total_golden_examples", len(golden))
    print("intent_distribution", dict(sorted(intent_counts.items())))
    print("bucket_distribution", dict(sorted(bucket_counts.items())))
    print("quality_validation", checks)
    print("exact_duplicate_text_count", exact_duplicate_count)
    print("near_duplicate_pair_count", len(near_duplicate_pairs))
    print("missing_source_record_count", len(missing_source))
    print("modified_text_count", len(modified_text))
    print("jsonl_error_count", len(source_errors) + len(golden_errors))
    print("--- first_10_golden_records ---")
    for row in golden[:10]:
        print(json.dumps(row, ensure_ascii=False))
    print("--- warnings_and_limitations ---")
    print("Phase 3A primary_intent values are inherited candidate-pool labels, not human gold labels.")
    print("Unclassified examples intentionally retain null primary_intent values.")
    print("Evaluation fields remain empty placeholders; no model answers or decisions were generated.")
    if not all(checks.values()):
        raise SystemExit("Phase 3C validation failed")


if __name__ == "__main__":
    main()
