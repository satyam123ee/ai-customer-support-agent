#!/usr/bin/env python3
"""Reproducible Phase 1 audit and brand selection for the TWCS dataset.

Uses three streaming CSV passes; it never loads the full dataset into memory.
Outputs a JSON configuration and Markdown report based only on observed rows.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


REQUIRED_COLUMNS = {
    "tweet_id", "author_id", "inbound", "created_at", "text",
    "response_tweet_id", "in_response_to_tweet_id",
}
TOKEN_RE = re.compile(r"[a-z][a-z']{2,}")
STOPWORDS = {
    "the", "and", "that", "this", "with", "for", "you", "your", "are",
    "was", "have", "has", "not", "but", "from", "can", "will", "just",
    "please", "help", "thanks", "thank", "http", "https", "com", "www",
    "get", "got", "its", "into", "about", "they", "their", "our", "out",
    "all", "been", "need", "want", "could", "would", "should", "when",
}


def ids(value: str | None) -> list[str]:
    """Return numeric tweet ids from a possibly comma-separated CSV field."""
    return re.findall(r"\d+", value or "")


def is_inbound(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def parse_date(value: str | None):
    try:
        return datetime.strptime((value or "").strip(), "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        return None


def tokens(text: str | None) -> list[str]:
    cleaned = re.sub(r"https?://\S+|@\w+", " ", text or "").lower()
    return [t for t in TOKEN_RE.findall(cleaned) if t not in STOPWORDS]


class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[b] = a


def rows(path: Path):
    with path.open("r", encoding="utf-8", errors="replace", newline="") as source:
        yield from csv.DictReader(source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--candidate-limit", type=int, default=40)
    args = parser.parse_args()
    path = args.csv_path.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Pass 1: schema and global / outbound-brand inventory.
    total = inbound = outbound = invalid_boolean = 0
    first_date = last_date = None
    outbound_by_brand: Counter[str] = Counter()
    with path.open("r", encoding="utf-8", errors="replace", newline="") as source:
        reader = csv.DictReader(source)
        columns = reader.fieldnames or []
        missing = REQUIRED_COLUMNS.difference(columns)
        if missing:
            raise SystemExit(f"Missing required columns: {sorted(missing)}")
        for row in reader:
            total += 1
            flag = (row.get("inbound") or "").strip().lower()
            if flag not in {"true", "false"}:
                invalid_boolean += 1
            if is_inbound(flag):
                inbound += 1
            else:
                outbound += 1
                author = (row.get("author_id") or "").strip()
                if author:
                    outbound_by_brand[author] += 1
            stamp = parse_date(row.get("created_at"))
            if stamp:
                first_date = stamp if first_date is None or stamp < first_date else first_date
                last_date = stamp if last_date is None or stamp > last_date else last_date

    candidates = [brand for brand, _ in outbound_by_brand.most_common(args.candidate_limit)]
    candidate_set = set(candidates)

    # Pass 2: index only candidate-brand outbound tweet ids.
    tweet_brand: dict[str, str] = {}
    for row in rows(path):
        if not is_inbound(row.get("inbound")):
            author = (row.get("author_id") or "").strip()
            tid = (row.get("tweet_id") or "").strip()
            if author in candidate_set and tid:
                tweet_brand[tid] = author

    # Pass 3: customer issues answered by each candidate and local thread edges.
    stats = {brand: {
        "outbound_tweets": outbound_by_brand[brand], "customer_issues": 0,
        "brand_response_links": 0, "linked_customer_replies": 0,
        "issue_tokens": Counter(), "issue_rows": set(), "graph": UnionFind(),
    } for brand in candidates}
    for row in rows(path):
        tid = (row.get("tweet_id") or "").strip()
        reply_to = ids(row.get("in_response_to_tweet_id"))
        response_ids = ids(row.get("response_tweet_id"))
        inbound_row = is_inbound(row.get("inbound"))

        if inbound_row:
            linked_brands = {tweet_brand[rid] for rid in response_ids if rid in tweet_brand}
            for brand in linked_brands:
                item = stats[brand]
                item["customer_issues"] += 1
                item["issue_rows"].add(tid)
                item["issue_tokens"].update(tokens(row.get("text")))
                if tid:
                    for rid in response_ids:
                        if tweet_brand.get(rid) == brand:
                            item["graph"].union(tid, rid)
            for parent in reply_to:
                brand = tweet_brand.get(parent)
                if brand:
                    stats[brand]["linked_customer_replies"] += 1
                    if tid:
                        stats[brand]["graph"].union(tid, parent)
        else:
            brand = tweet_brand.get(tid)
            if brand:
                item = stats[brand]
                item["brand_response_links"] += len(reply_to)
                for parent in reply_to:
                    item["graph"].union(tid, parent)

    results = []
    for brand in candidates:
        item = stats[brand]
        graph = item["graph"]
        component_sizes: Counter[str] = Counter()
        for node in graph.parent:
            component_sizes[graph.find(node)] += 1
        conversations = len(component_sizes)
        average_length = (sum(component_sizes.values()) / conversations) if conversations else 0.0
        issue_count = item["customer_issues"]
        coverage = issue_count / outbound_by_brand[brand] if outbound_by_brand[brand] else 0.0
        topical_tokens = sum(1 for _, count in item["issue_tokens"].items() if count >= 3)
        usable_responses = min(item["brand_response_links"], issue_count)
        results.append({
            "brand": brand, "outbound_tweets": outbound_by_brand[brand],
            "customer_issues_answered": issue_count,
            "outbound_to_inbound_link_rate": coverage,
            "response_links": item["brand_response_links"],
            "usable_historical_brand_responses": usable_responses,
            "linked_customer_replies": item["linked_customer_replies"],
            "reconstructed_components": conversations,
            "average_component_size": round(average_length, 3),
            "topical_tokens_with_frequency_at_least_3": topical_tokens,
            "top_issue_terms": item["issue_tokens"].most_common(12),
        })

    max_issues = max((r["customer_issues_answered"] for r in results), default=1) or 1
    max_responses = max((r["usable_historical_brand_responses"] for r in results), default=1) or 1
    max_components = max((r["reconstructed_components"] for r in results), default=1) or 1
    for r in results:
        # Transparent 100-point score. Eligibility requires enough observed support data
        # to draw a 150-example evaluation subset without reusing all records.
        r["score"] = round(
            25 * math.log1p(r["customer_issues_answered"]) / math.log1p(max_issues)
            + 25 * math.log1p(r["usable_historical_brand_responses"]) / math.log1p(max_responses)
            + 20 * min(r["outbound_to_inbound_link_rate"], 1.0)
            + 15 * math.log1p(r["reconstructed_components"]) / math.log1p(max_components)
            + 15 * min(r["topical_tokens_with_frequency_at_least_3"] / 30, 1.0), 2)
        r["golden_set_eligible"] = r["customer_issues_answered"] >= 250 and r["usable_historical_brand_responses"] >= 250
    results.sort(key=lambda r: (not r["golden_set_eligible"], -r["score"], -r["customer_issues_answered"]))
    selected = results[0] if results else None

    overview = {
        "source_csv": str(path), "file_size_bytes": path.stat().st_size,
        "row_count": total, "columns": columns, "inbound_tweets": inbound,
        "outbound_tweets": outbound, "unique_outbound_brands": len(outbound_by_brand),
        "invalid_inbound_values": invalid_boolean,
        "date_range_utc": [first_date.isoformat() if first_date else None, last_date.isoformat() if last_date else None],
        "candidate_limit": args.candidate_limit,
        "method_note": "Candidates are the top outbound authors; response links use raw tweet-id references. Thread metrics are connected components around candidate-brand tweets.",
    }
    payload = {"dataset": overview, "selection_method": {
        "score_weights": {"customer_issue_volume": 25, "usable_brand_responses": 25, "link_coverage": 20, "conversation_components": 15, "lexical_support_diversity": 15},
        "golden_set_eligibility": "At least 250 answered customer issues and 250 linked brand responses.",
    }, "selected_brand": selected, "ranked_candidates": results}
    (out / "brand_config.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Phase 1: Dataset Audit and Brand Selection", "", "## Dataset used", "",
             f"- Path: `{path}`", f"- Size: {path.stat().st_size:,} bytes", f"- Rows: {total:,}",
             f"- Schema: {', '.join(columns)}", f"- Inbound/customer tweets: {inbound:,}",
             f"- Outbound/brand tweets: {outbound:,}", f"- Unique outbound brands: {len(outbound_by_brand):,}",
             f"- Date range (UTC): {overview['date_range_utc'][0]} to {overview['date_range_utc'][1]}", "",
             "## Method", "", "The script makes three streaming passes. It ranks the 40 largest outbound authors, follows raw tweet-id links to measure answered customer issues and local thread components, and scores candidates with the weights recorded in `brand_config.json`. It does not label intents; lexical diversity is only a Phase 1 proxy.", "",
             "## Top 10 candidates", "", "| Rank | Brand | Score | Answered issues | Usable responses | Link coverage | Components | Avg. component size | Lexical signals | Golden-set eligible |", "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for index, r in enumerate(results[:10], start=1):
        lines.append(f"| {index} | {r['brand']} | {r['score']:.2f} | {r['customer_issues_answered']:,} | {r['usable_historical_brand_responses']:,} | {r['outbound_to_inbound_link_rate']:.1%} | {r['reconstructed_components']:,} | {r['average_component_size']:.2f} | {r['topical_tokens_with_frequency_at_least_3']} | {'Yes' if r['golden_set_eligible'] else 'No'} |")
    lines += ["", "## Selected brand", ""]
    if selected:
        lines += [f"**{selected['brand']}** (score {selected['score']:.2f}/100).", "",
                  f"It is the highest-ranked candidate under the recorded method. Its raw-link evidence includes {selected['customer_issues_answered']:,} answered customer issues, {selected['usable_historical_brand_responses']:,} usable linked brand responses, {selected['reconstructed_components']:,} reconstructed local conversation components, and {selected['outbound_to_inbound_link_rate']:.1%} outbound-to-inbound link coverage.", "",
                  "## Limitations", "", "- Tweet link fields can be missing or contain multiple ids, so components are reconstructed from observed links rather than assumed complete conversations.", "- Inbound messages without an outbound tweet-id link are not attributed to a brand.", "- This analysis is Phase 1 only: no RAG, embeddings, agent, intent taxonomy, golden set, or evaluation harness was created."]
    (out / "BRAND_SELECTION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"dataset": overview, "selected_brand": selected, "top_10": results[:10]}, indent=2))


if __name__ == "__main__":
    main()
