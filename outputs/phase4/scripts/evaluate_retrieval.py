#!/usr/bin/env python3
"""Evaluate the Phase 4 lexical retrieval baseline without fabricating relevance labels."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

DEFAULT_RESULTS = Path("outputs/phase4/retrieval/retrieval_results.jsonl")
DEFAULT_GOLDEN = Path("outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl")
DEFAULT_SUMMARY = Path("outputs/phase4/retrieval/retrieval_summary.json")
DEFAULT_REPORT = Path("outputs/phase4/reports/PHASE4_RETRIEVAL_REPORT.md")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(results_path: Path, golden_path: Path, summary_path: Path, report_path: Path) -> dict:
    results = load_jsonl(results_path)
    golden = load_jsonl(golden_path)
    golden_by_id = {record["golden_id"]: record for record in golden}
    grouped = defaultdict(list)
    for row in results:
        grouped[row["golden_id"]].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: row["retrieved_rank"] if row["retrieved_rank"] is not None else 999999)

    eligible_ids = [record["golden_id"] for record in golden if record.get("evaluation", {}).get("gold_intent") is not None]
    excluded_ids = [record["golden_id"] for record in golden if record.get("evaluation", {}).get("gold_intent") is None]
    agreements = {1: [], 3: [], 5: []}
    reciprocal_ranks = []
    eligible_failures = 0
    top1_scores = []
    all_scores = []
    for golden_id in eligible_ids:
        gold_intent = golden_by_id[golden_id]["evaluation"]["gold_intent"]
        rows = grouped.get(golden_id, [])
        valid_rows = [row for row in rows if row.get("retrieved_rank") is not None]
        all_scores.extend(row["similarity_score"] for row in valid_rows if isinstance(row.get("similarity_score"), (int, float)))
        if not valid_rows:
            eligible_failures += 1
            for cutoff in agreements:
                agreements[cutoff].append(False)
            continue
        top1_scores.append(valid_rows[0]["similarity_score"])
        for cutoff in agreements:
            hit = any(gold_intent in (row.get("retrieved_intent_ids") or []) for row in valid_rows[:cutoff])
            agreements[cutoff].append(hit)
        first_rank = next((row["retrieved_rank"] for row in valid_rows if gold_intent in (row.get("retrieved_intent_ids") or [])), None)
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)

    def rate(values: list[bool]) -> float | None:
        return sum(values) / len(values) if values else None

    top1 = rate(agreements[1])
    top3 = rate(agreements[3])
    top5 = rate(agreements[5])
    summary = {
        "phase": "4",
        "retrieval_method": "standard-library sparse TF-IDF cosine similarity",
        "top_k": 5,
        "golden_queries": len(golden),
        "eligible_evaluation_records": len(eligible_ids),
        "excluded_records_null_gold_intent": len(excluded_ids),
        "retrieval_failures_total": sum(not any(row.get("retrieved_rank") is not None for row in grouped.get(record["golden_id"], [])) for record in golden),
        "retrieval_failures_eligible": eligible_failures,
        "top_1_intent_agreement": top1,
        "top_3_intent_agreement": top3,
        "top_5_intent_agreement": top5,
        "mean_reciprocal_rank": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else None,
        "average_top_1_similarity": sum(top1_scores) / len(top1_scores) if top1_scores else None,
        "average_retrieved_similarity": sum(all_scores) / len(all_scores) if all_scores else None,
        "human_relevance_evaluation": "pending; no deterministic relevance labels were fabricated",
        "evaluation_rule": "Intent agreement uses only non-null curated Phase 3E gold_intent values; Phase 3A corpus intent metadata remains heuristic.",
        "excluded_golden_ids": excluded_ids,
        "sample_queries": [],
        "limitations": [
            "Lexical TF-IDF similarity does not understand synonyms, paraphrases, or conversation semantics.",
            "Retrieved intent metadata is derived from Phase 3A lexical rules and is not human gold truth.",
            "Same-message and same-conversation records are excluded to reduce source leakage.",
            "Human relevance judgments remain pending.",
        ],
        "output_files": {"results": str(results_path), "summary": str(summary_path), "report": str(report_path)},
    }

    sample_ids = [record["golden_id"] for record in golden[:10]]
    for golden_id in sample_ids:
        record = golden_by_id[golden_id]
        rows = [row for row in grouped.get(golden_id, []) if row.get("retrieved_rank") == 1]
        if not rows:
            continue
        top = rows[0]
        gold_intent = record.get("evaluation", {}).get("gold_intent")
        summary["sample_queries"].append({
            "golden_id": golden_id,
            "query": record.get("text"),
            "top_retrieval": top.get("retrieved_customer_text"),
            "similarity": top.get("similarity_score"),
            "gold_intent": gold_intent,
            "retrieved_intent": top.get("retrieved_primary_intent"),
            "deterministic_intent_agreement": bool(gold_intent and gold_intent in (top.get("retrieved_intent_ids") or [])),
            "human_relevance": "pending",
        })

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = [
        "# Phase 4: Historical Retrieval Baseline",
        "",
        "## Objective",
        "",
        "Establish a deterministic retrieval-only baseline over the Phase 2 AppleSupport conversation corpus. This phase does not generate responses, perform RAG, or make escalation decisions.",
        "",
        "## Method",
        "",
        "- Retrieval units are individual Phase 2 customer messages with their immediate historical AppleSupport response when available.",
        "- Text is normalized conservatively by removing handles/URLs, lowercasing, tokenizing, and removing a small stop-word list.",
        "- Similarity uses standard-library sparse TF-IDF vectors and cosine similarity.",
        "- Default top_k is 5.",
        "- The same customer message and same conversation are excluded from its own retrieval results to reduce leakage.",
        "- Corpus intent metadata is derived from Phase 3A lexical rules and is used only for diagnostic agreement, not as human truth.",
        "",
        "## Metrics",
        "",
        f"- Golden queries: {len(golden)}",
        f"- Eligible evaluation records: {len(eligible_ids)}",
        f"- Excluded null-gold-intent records: {len(excluded_ids)}",
        f"- Retrieval failures: {summary['retrieval_failures_total']}",
        f"- Top-1 intent agreement: {top1}",
        f"- Top-3 intent agreement: {top3}",
        f"- Top-5 intent agreement: {top5}",
        f"- Mean reciprocal rank: {summary['mean_reciprocal_rank']}",
        f"- Average top-1 similarity: {summary['average_top_1_similarity']}",
        f"- Average retrieved similarity: {summary['average_retrieved_similarity']}",
        "",
        "## Inspection samples",
        "",
        "Human relevance is pending; the following deterministic intent agreement is not a relevance judgment.",
        "",
    ]
    for sample in summary["sample_queries"]:
        report.extend([
            f"### {sample['golden_id']}",
            f"- QUERY: {sample['query']}",
            f"- TOP RETRIEVAL: {sample['top_retrieval']}",
            f"- SIMILARITY: {sample['similarity']}",
            f"- GOLD INTENT: {sample['gold_intent']}",
            f"- RETRIEVED INTENT: {sample['retrieved_intent']}",
            f"- DETERMINISTIC INTENT AGREEMENT: {sample['deterministic_intent_agreement']}",
            "- HUMAN RELEVANCE: pending",
            "",
        ])
    report.extend([
        "## Limitations",
        "",
        *[f"- {limitation}" for limitation in summary["limitations"]],
        "",
        "## Files",
        "",
        f"- Corpus: outputs/phase4/retrieval/retrieval_corpus.jsonl",
        f"- Results: {results_path}",
        f"- Summary: {summary_path}",
        "- Validator: work/phase4_validate.py",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    summary = evaluate(args.results, args.golden, args.summary, args.report)
    print(json.dumps({
        "phase": summary["phase"],
        "eligible_evaluation_records": summary["eligible_evaluation_records"],
        "top_1_intent_agreement": summary["top_1_intent_agreement"],
        "top_3_intent_agreement": summary["top_3_intent_agreement"],
        "top_5_intent_agreement": summary["top_5_intent_agreement"],
        "summary": str(args.summary),
        "report": str(args.report),
    }, indent=2))


if __name__ == "__main__":
    main()
