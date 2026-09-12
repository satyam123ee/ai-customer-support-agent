#!/usr/bin/env python3
"""Phase 2: streaming AppleSupport conversation preparation for TWCS.

This is deliberately limited to data extraction and observed-link reconstruction.
It does not create embeddings, RAG, an agent, intents, or evaluations.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_COLUMNS = [
    "tweet_id", "author_id", "inbound", "created_at", "text",
    "response_tweet_id", "in_response_to_tweet_id",
]


def parse_ids(value: str | None) -> list[str]:
    """TWCS links can contain one or more numeric IDs represented as text."""
    return re.findall(r"\d+", value or "")


def inbound(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def parse_timestamp(value: str | None):
    try:
        return datetime.strptime((value or "").strip(), "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        return None


def read_rows(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
        yield from csv.DictReader(stream)


class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: str, right: str) -> None:
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[right] = left


def clean_row(row: dict[str, str], role: str) -> dict[str, object]:
    """Preserve the original required TWCS fields and add only a preparation role."""
    record = {key: row.get(key, "") for key in REQUIRED_COLUMNS}
    record["inbound"] = inbound(record["inbound"])
    record["role"] = role
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--brand", default="AppleSupport")
    args = parser.parse_args()

    source = args.csv_path.resolve()
    root = args.output_root.resolve()
    data_dir, outputs_dir, reports_dir = root / "data", root / "outputs", root / "reports"
    for directory in (data_dir, outputs_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)

    # First streaming pass: retain all selected-brand tweets, and the customer ids
    # explicitly named as parents of those brand replies.
    apples: dict[str, dict[str, str]] = {}
    apple_parent_ids: set[str] = set()
    graph = UnionFind()
    source_rows = invalid_flags = duplicate_apple_ids = 0
    missing_apple_text = missing_apple_author = 0
    columns: list[str] | None = None

    with source.open("r", encoding="utf-8", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        missing = set(REQUIRED_COLUMNS).difference(columns)
        if missing:
            raise SystemExit(f"Missing required columns: {sorted(missing)}")
        for row in reader:
            source_rows += 1
            flag = (row.get("inbound") or "").strip().lower()
            if flag not in {"true", "false"}:
                invalid_flags += 1
            if not inbound(flag) and (row.get("author_id") or "").strip() == args.brand:
                tweet_id = (row.get("tweet_id") or "").strip()
                if not tweet_id:
                    continue
                if tweet_id in apples:
                    duplicate_apple_ids += 1
                apples[tweet_id] = {key: row.get(key, "") for key in REQUIRED_COLUMNS}
                graph.find(tweet_id)
                if not (row.get("text") or "").strip():
                    missing_apple_text += 1
                if not (row.get("author_id") or "").strip():
                    missing_apple_author += 1
                for parent_id in parse_ids(row.get("in_response_to_tweet_id")):
                    apple_parent_ids.add(parent_id)
                    graph.union(tweet_id, parent_id)

    apple_ids = set(apples)
    related_inbound: dict[str, dict[str, str]] = {}
    directly_answered: set[str] = set()
    customer_reply_to_apple: set[str] = set()
    missing_inbound_text = missing_inbound_author = 0

    # Second streaming pass: retain an inbound row only when raw link fields connect
    # it directly to an AppleSupport tweet (or it is the parent of one). This makes
    # the boundaries explainable and avoids assigning unrelated customer messages.
    for row in read_rows(source):
        if not inbound(row.get("inbound")):
            continue
        tweet_id = (row.get("tweet_id") or "").strip()
        if not tweet_id:
            continue
        response_targets = set(parse_ids(row.get("response_tweet_id")))
        parent_targets = set(parse_ids(row.get("in_response_to_tweet_id")))
        has_response_from_apple = bool(response_targets.intersection(apple_ids))
        is_parent_of_apple_reply = tweet_id in apple_parent_ids
        replies_to_apple = bool(parent_targets.intersection(apple_ids))
        if not (has_response_from_apple or is_parent_of_apple_reply or replies_to_apple):
            continue
        related_inbound[tweet_id] = {key: row.get(key, "") for key in REQUIRED_COLUMNS}
        graph.find(tweet_id)
        if not (row.get("text") or "").strip():
            missing_inbound_text += 1
        if not (row.get("author_id") or "").strip():
            missing_inbound_author += 1
        if has_response_from_apple or is_parent_of_apple_reply:
            directly_answered.add(tweet_id)
        if replies_to_apple:
            customer_reply_to_apple.add(tweet_id)
        for target in response_targets.intersection(apple_ids):
            graph.union(tweet_id, target)
        for target in parent_targets.intersection(apple_ids):
            graph.union(tweet_id, target)

    # Group retained records into components. Apple tweets with no observed customer
    # link remain as a brand-only component, rather than being discarded or guessed.
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for tweet_id, row in apples.items():
        grouped[graph.find(tweet_id)].append(clean_row(row, "brand_response"))
    for tweet_id, row in related_inbound.items():
        grouped[graph.find(tweet_id)].append(clean_row(row, "customer_message"))

    def timestamp_key(message: dict[str, object]):
        parsed = parse_timestamp(str(message["created_at"]))
        return parsed or datetime.max.replace(tzinfo=timezone.utc)

    records = []
    conversation_lengths: list[int] = []
    usable_interactions = 0
    brand_only_components = 0
    dated_messages = []
    for index, messages in enumerate(grouped.values(), start=1):
        messages.sort(key=timestamp_key)
        brand_messages = sum(m["role"] == "brand_response" for m in messages)
        customer_messages = sum(m["role"] == "customer_message" for m in messages)
        usable = brand_messages > 0 and customer_messages > 0
        if usable:
            usable_interactions += 1
            conversation_lengths.append(len(messages))
        else:
            brand_only_components += 1
        dated_messages.extend(parse_timestamp(str(m["created_at"])) for m in messages if parse_timestamp(str(m["created_at"])))
        records.append({
            "conversation_id": f"{args.brand.lower()}_{index:06d}",
            "has_customer_to_brand_interaction": usable,
            "message_count": len(messages),
            "customer_message_count": customer_messages,
            "brand_response_count": brand_messages,
            "messages": messages,
        })

    # Stable output ordering makes reruns easy to compare.
    records.sort(key=lambda item: (str(item["messages"][0]["tweet_id"]) if item["messages"] else ""))
    conversation_path = data_dir / "applesupport_conversations.jsonl"
    with conversation_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    customers = {row.get("author_id", "").strip() for row in related_inbound.values() if row.get("author_id", "").strip()}
    message_dates = [stamp for stamp in dated_messages if stamp]
    stats = {
        "phase": 2,
        "brand": args.brand,
        "source_csv": str(source),
        "source_file_size_bytes": source.stat().st_size,
        "source_csv_rows_scanned": source_rows,
        "schema": columns,
        "extraction_boundary": "All outbound AppleSupport tweets, plus inbound customer tweets directly connected through response_tweet_id or in_response_to_tweet_id, or directly named as the parent of an AppleSupport reply.",
        "total_applesupport_tweets": len(apples),
        "outbound_applesupport_tweets": len(apples),
        "inbound_customer_tweets_in_retained_conversations": len(related_inbound),
        "unique_customers": len(customers),
        "reconstructed_components_including_brand_only": len(records),
        "customer_brand_conversation_count": usable_interactions,
        "brand_only_component_count": brand_only_components,
        "customer_messages_with_direct_applesupport_response": len(directly_answered),
        "response_coverage": (len(directly_answered) / len(related_inbound)) if related_inbound else None,
        "customer_replies_to_applesupport": len(customer_reply_to_apple),
        "conversation_length_unit": "retained messages per customer-brand component",
        "average_conversation_length": (sum(conversation_lengths) / len(conversation_lengths)) if conversation_lengths else None,
        "median_conversation_length": statistics.median(conversation_lengths) if conversation_lengths else None,
        "maximum_conversation_length": max(conversation_lengths) if conversation_lengths else None,
        "retained_message_date_range_utc": [min(message_dates).isoformat(), max(message_dates).isoformat()] if message_dates else [None, None],
        "data_quality": {
            "invalid_inbound_values_in_source": invalid_flags,
            "duplicate_applesupport_tweet_ids": duplicate_apple_ids,
            "applesupport_rows_with_missing_text": missing_apple_text,
            "applesupport_rows_with_missing_author": missing_apple_author,
            "related_inbound_rows_with_missing_text": missing_inbound_text,
            "related_inbound_rows_with_missing_author": missing_inbound_author,
            "limitations": [
                "TWCS relationship fields may be absent or contain multiple ids.",
                "Only directly observed links are used; missing links are not inferred.",
                "Brand-only components are retained but excluded from customer-brand conversation-length statistics.",
            ],
        },
        "outputs": {"conversations_jsonl": str(conversation_path)},
    }
    stats_path = outputs_dir / "applesupport_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    report = [
        "# Phase 2: AppleSupport Data Preparation",
        "",
        "## Source and method",
        "",
        f"- Source: `{source}`",
        f"- Source rows streamed: {source_rows:,}",
        f"- Source size: {source.stat().st_size:,} bytes",
        "- Method: two streaming CSV passes; the full file is never loaded into memory.",
        "- Boundary: all outbound AppleSupport tweets plus inbound messages directly linked by the dataset's relationship columns.",
        "",
        "## Prepared data statistics",
        "",
        f"- AppleSupport tweets (outbound): {len(apples):,}",
        f"- Related inbound customer messages: {len(related_inbound):,}",
        f"- Unique customers: {len(customers):,}",
        f"- Customer → AppleSupport conversation components: {usable_interactions:,}",
        f"- Brand-only components retained: {brand_only_components:,}",
        f"- Customer messages with a directly observed AppleSupport response: {len(directly_answered):,}",
        f"- Response coverage: {stats['response_coverage']:.2%}" if stats["response_coverage"] is not None else "- Response coverage: unavailable",
        f"- Average customer-brand conversation length: {stats['average_conversation_length']:.3f}" if stats["average_conversation_length"] is not None else "- Average customer-brand conversation length: unavailable",
        f"- Median customer-brand conversation length: {stats['median_conversation_length']}" if stats["median_conversation_length"] is not None else "- Median customer-brand conversation length: unavailable",
        f"- Maximum customer-brand conversation length: {stats['maximum_conversation_length']}" if stats["maximum_conversation_length"] is not None else "- Maximum customer-brand conversation length: unavailable",
        f"- Retained-message date range (UTC): {stats['retained_message_date_range_utc'][0]} to {stats['retained_message_date_range_utc'][1]}",
        "",
        "## Data-quality observations",
        "",
        f"- Invalid inbound flags in source: {invalid_flags:,}",
        f"- Duplicate AppleSupport IDs: {duplicate_apple_ids:,}",
        f"- AppleSupport rows missing text: {missing_apple_text:,}; related inbound rows missing text: {missing_inbound_text:,}",
        "- Relationship fields are not guaranteed to describe a complete thread. This output retains only observed direct links and does not fabricate missing conversation context.",
        "",
        "## Files produced",
        "",
        f"- `{conversation_path}`",
        f"- `{stats_path}`",
        "",
        "## Scope boundary",
        "",
        "This completes only selected-brand extraction and preparation. No RAG, embeddings, LLM agent, intent taxonomy, golden set, or evaluation was created.",
    ]
    report_path = reports_dir / "PHASE2_DATA_PREPARATION_REPORT.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"stats": stats, "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
