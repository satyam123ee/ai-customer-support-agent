#!/usr/bin/env python3
"""Build a deterministic, manually reviewable Phase 3C golden set."""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

SEED = 20260912
TARGET_TOTAL = 200
BUCKET_QUOTAS = {
    "primary_intent": 150,
    "unclassified": 20,
    "multi_intent": 15,
    "ambiguous": 15,
}
PRIMARY_INTENT_QUOTAS = {
    "app_store_media_services": 10,
    "apple_id_icloud_account": 9,
    "apple_watch": 6,
    "battery_power_charging": 10,
    "billing_purchases_subscriptions": 8,
    "connectivity_network": 9,
    "device_setup_activation_migration": 9,
    "hardware_accessories": 10,
    "keyboard_text_rendering": 10,
    "mac_computer": 8,
    "messaging_calls_facetime": 10,
    "performance_stability": 10,
    "software_update_os": 26,
    "store_orders_repairs": 8,
    "support_contact_experience": 7,
}
INTENT_ORDER = list(PRIMARY_INTENT_QUOTAS)
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
MENTION_URL_RE = re.compile(r"@\w+|https?://\S+", re.I)
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


def normalized(text: str) -> str:
    return " ".join(MENTION_URL_RE.sub(" ", text or "").lower().split())


def canonical(text: str) -> str:
    value = normalized(text)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return " ".join(value.split())


def content_tokens(text: str) -> set[str]:
    return {
        token for token in canonical(text).split()
        if len(token) > 2 and token not in STOP_WORDS
    }


def near_duplicate(left: set[str], right: set[str]) -> bool:
    if len(left) < 6 or len(right) < 6:
        return False
    overlap = len(left & right)
    return overlap >= 4 and overlap / min(len(left), len(right)) >= 0.7 and len(left | right) >= 6


def difficulty_tags(item: dict) -> list[str]:
    text = item["text"] or ""
    normalized_text = normalized(text)
    tags = []
    if item["bucket"] == "primary_intent" and len(item["matched_intent_ids"]) == 1:
        tags.append("clear_single_intent")
    if item["content_word_count"] <= 8 or item["conversation_length"] <= 2:
        tags.append("incomplete_context")
    if re.search(r"\b(?:how|why|can|could|help|won'?t|doesn'?t|not working|unable|stuck|fix)\b", normalized_text):
        tags.append("troubleshooting_request")
    if re.search(r"\b(?:annoyed|frustrat|angry|hate|seriously|bullshit|ridiculous|upset|disappointed|wtf|damn)\b|!{1,}", normalized_text):
        tags.append("complaint_or_frustration")
    if re.search(r"\b(?:employee|refund|charged|billing|lawsuit|manager|repair|appointment|store|customer service|escalat)\b", normalized_text):
        tags.append("possible_escalation_context")
    if item["conversation_length"] >= 4 or re.search(r"\b(?:already|again|still|tried|before|past|previous|every time|keeps?)\b", normalized_text):
        tags.append("historical_retrieval_context")
    if re.search(r"\b(?:what|which|where|when|who)\b|\?", normalized_text):
        tags.append("question_or_missing_detail")
    return tags


def quality_ok(item: dict) -> bool:
    text = item.get("text", "")
    tokens = TOKEN_RE.findall(text)
    if not text.strip() or not tokens:
        return False
    if len(tokens) >= 8 and len(set(token.lower() for token in tokens)) / len(tokens) < 0.2:
        return False
    return True


def select_group(candidates: list[dict], limit: int, rng: random.Random, selected: list[dict]) -> list[dict]:
    ranked = []
    for item in sorted(candidates, key=lambda value: str(value["tweet_id"])):
        tags = difficulty_tags(item)
        item["_selection_tags"] = tags
        item["_selection_score"] = len(tags)
        ranked.append((len(tags), rng.random(), str(item["tweet_id"]), item))
    ranked.sort(key=lambda value: (-value[0], -value[1], value[2]))

    selected_content = [content_tokens(item["text"]) for item in selected]
    selected_canonicals = {canonical(item["text"]) for item in selected}
    chosen = []
    for _, _, _, item in ranked:
        item_canonical = canonical(item["text"])
        item_content = content_tokens(item["text"])
        if item_canonical in selected_canonicals:
            continue
        if any(near_duplicate(item_content, existing) for existing in selected_content):
            continue
        chosen.append(item)
        selected_content.append(item_content)
        selected_canonicals.add(item_canonical)
        if len(chosen) == limit:
            break
    if len(chosen) != limit:
        raise ValueError(f"Could not select {limit} quality-diverse records; selected {len(chosen)}")
    return chosen


def make_output_record(item: dict, golden_id: str) -> dict:
    evaluation = {
        "gold_intent": None,
        "acceptable_intents": [],
        "gold_response": None,
        "retrieval_relevance": None,
        "response_grounding": None,
        "response_quality": None,
        "should_escalate": None,
        "escalation_reason": None,
    }
    return {
        "golden_id": golden_id,
        "message_id": item["tweet_id"],
        "candidate_id": item["candidate_id"],
        "tweet_id": item["tweet_id"],
        "conversation_id": item["conversation_id"],
        "author_id": item["author_id"],
        "created_at_utc": item["created_at_utc"],
        "text": item["text"],
        "bucket": item["bucket"],
        "primary_intent": item["primary_intent"],
        "matched_intent_ids": item["matched_intent_ids"],
        "evidence_by_intent": item["evidence_by_intent"],
        "evidence_strength": item["evidence_strength"],
        "content_word_count": item["content_word_count"],
        "conversation_length": item["conversation_length"],
        "selection_metadata": {
            "seed": SEED,
            "difficulty_tags": item["_selection_tags"],
            "difficulty_score": item["_selection_score"],
        },
        "evaluation": evaluation,
    }


def build(source_path: Path, output_path: Path, summary_path: Path, report_path: Path) -> dict:
    source_rows = [json.loads(line) for line in source_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    source_by_id = {row["tweet_id"]: row for row in source_rows}
    if len(source_by_id) != len(source_rows):
        raise ValueError("Phase 3B source contains duplicate tweet IDs")
    if any(not quality_ok(row) for row in source_rows):
        raise ValueError("Phase 3B source contains an obvious empty or low-diversity record")

    rng = random.Random(SEED)
    selected = []
    primary_rows = [row for row in source_rows if row["bucket"] == "primary_intent"]
    for intent_id in INTENT_ORDER:
        candidates = [row for row in primary_rows if row["primary_intent"] == intent_id]
        selected.extend(select_group(candidates, PRIMARY_INTENT_QUOTAS[intent_id], rng, selected))

    for bucket, quota in (("unclassified", 20), ("multi_intent", 15), ("ambiguous", 15)):
        candidates = [row for row in source_rows if row["bucket"] == bucket]
        selected.extend(select_group(candidates, quota, rng, selected))

    if len(selected) != TARGET_TOTAL:
        raise ValueError(f"Golden set size mismatch: {len(selected)} != {TARGET_TOTAL}")

    selected.sort(key=lambda row: (row["bucket"], row["primary_intent"] or "", row["created_at_utc"] or "", str(row["tweet_id"])))
    output_records = [make_output_record(row, f"GS-{index:03d}") for index, row in enumerate(selected, start=1)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        for record in output_records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    intent_counts = Counter(row["primary_intent"] for row in output_records if row["primary_intent"])
    bucket_counts = Counter(row["bucket"] for row in output_records)
    tag_counts = Counter(tag for row in output_records for tag in row["selection_metadata"]["difficulty_tags"])
    summary = {
        "phase": "3C",
        "total_golden_examples": len(output_records),
        "source_candidate_count": len(source_rows),
        "random_seed": SEED,
        "bucket_quotas": BUCKET_QUOTAS,
        "primary_intent_quotas": PRIMARY_INTENT_QUOTAS,
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "primary_intent_counts": dict((intent, intent_counts.get(intent, 0)) for intent in INTENT_ORDER),
        "multi_intent_examples": bucket_counts["multi_intent"],
        "ambiguous_examples": bucket_counts["ambiguous"],
        "selection_methodology": {
            "allocation": "Coverage-first quotas: 150 primary-intent records with explicit rare-intent guarantees, plus 20 unclassified, 15 multi-intent, and 15 ambiguous records.",
            "ranking": "Difficulty-tag coverage, seeded random tie-breaking, stable tweet-id ordering, and greedy exact/near-duplicate avoidance.",
            "source_text": "Copied exactly from the Phase 3B candidate pool; no rewriting or annotation was performed.",
        },
        "difficulty_tag_counts": dict(sorted(tag_counts.items())),
        "quality_checks": {
            "evaluation_fields_are_placeholders": True,
            "model_answers_generated": False,
            "source_text_modified": False,
        },
        "limitations": [
            "Primary intents reflect Phase 3A discovery labels and are not human gold labels.",
            "Unclassified records intentionally have no guessed intent label.",
            "Difficulty tags are sampling metadata, not evaluation judgments.",
            "The golden set is drawn only from the 700-record Phase 3B pool.",
        ],
        "output_files": {
            "golden_set": str(output_path),
            "summary": str(summary_path),
            "report": str(report_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report_lines = [
        "# Phase 3C: Golden Evaluation Set",
        "",
        "## Objective",
        "",
        "Create a manually reviewable evaluation set from the locked Phase 3B candidate pool. This phase does not generate model answers, gold labels, retrieval judgments, response judgments, or escalation decisions.",
        "",
        "## Selection methodology",
        "",
        "- Source: the final 700-record Phase 3B candidate pool.",
        f"- Target: exactly {TARGET_TOTAL} records.",
        f"- Random seed: {SEED}.",
        "- Allocation is deliberately coverage-first rather than proportional: 150 primary-intent records, 20 unclassified records, 15 multi-intent records, and 15 ambiguous records.",
        "- Primary-intent quotas guarantee representation for every intent, including all 6 available Apple Watch primary-intent records.",
        "- Candidates are ranked by difficulty-signal coverage, then resolved with seeded random tie-breaking and stable tweet IDs.",
        "- Exact duplicates and clearly redundant near-duplicates are excluded against the complete selected set.",
        "- Original source text and source metadata are copied without modification.",
        "",
        "## Final counts",
        "",
        f"- Total golden examples: {len(output_records)}",
        *[f"- {bucket}: {bucket_counts[bucket]}" for bucket in BUCKET_QUOTAS],
        f"- Multi-intent examples: {bucket_counts['multi_intent']}",
        f"- Ambiguous examples: {bucket_counts['ambiguous']}",
        "",
        "## Primary-intent distribution",
        "",
        *[f"- {intent}: {intent_counts.get(intent, 0)}" for intent in INTENT_ORDER],
        "",
        "## Quality checks",
        "",
        "- JSONL output is generated with one JSON object per line.",
        "- Evaluation fields are null or empty placeholders and contain no guessed labels.",
        "- No model answers, retrieval judgments, grounding judgments, response-quality judgments, or escalation decisions were generated.",
        "- Independent validation is performed by work/phase3c_validate.py.",
        "",
        "## Limitations",
        "",
        *[f"- {limitation}" for limitation in summary["limitations"]],
        "",
        "## Files",
        "",
        f"- Golden set: {output_path}",
        f"- Summary: {summary_path}",
        f"- Builder: outputs/phase3/scripts/build_golden_set.py",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("outputs/phase3/candidate_pool/candidate_pool.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("outputs/phase3/golden_set/golden_evaluation_set.jsonl"))
    parser.add_argument("--summary", type=Path, default=Path("outputs/phase3/golden_set/golden_set_summary.json"))
    parser.add_argument("--report", type=Path, default=Path("outputs/phase3/reports/PHASE3C_GOLDEN_SET_REPORT.md"))
    args = parser.parse_args()
    summary = build(args.source, args.output, args.summary, args.report)
    print(json.dumps({
        "phase": summary["phase"],
        "total_golden_examples": summary["total_golden_examples"],
        "golden_set": str(args.output),
        "summary": str(args.summary),
        "report": str(args.report),
    }, indent=2))


if __name__ == "__main__":
    main()
