#!/usr/bin/env python3
"""Evaluate deterministic historical evidence signals over Phase 4 retrieval results."""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_GOLDEN = Path("outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl")
DEFAULT_RESULTS = Path("outputs/phase4/retrieval/retrieval_results.jsonl")
DEFAULT_OUTPUT = Path("outputs/phase5/evidence/historical_evidence_results.jsonl")
DEFAULT_SUMMARY = Path("outputs/phase5/evidence/historical_evidence_summary.json")
DEFAULT_REPORT = Path("outputs/phase5/reports/PHASE5_HISTORICAL_EVIDENCE_REPORT.md")
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
GENERIC_RESPONSE_RE = re.compile(r"\b(?:dm|direct message|look into this|continue from there|continue looking|let us know|we(?:'|’)d be happy to help|we(?:'|’)d like to look into)\b", re.I)
DIAGNOSTIC_RESPONSE_RE = re.compile(r"\?|\b(?:what happens|which app|what version|how often|does it continue|are you using|have you tried|is this happening)\b", re.I)
DIRECT_GUIDANCE_RE = re.compile(r"\b(?:go to|open|tap|select|choose|update|restart|reset|enable|disable|install|contact|use this link|here(?:'|’)s how)\b", re.I)


def tokens(text: str) -> set[str]:
    value = MENTION_URL_RE.sub(" ", text or "").lower()
    return {token for token in TOKEN_RE.findall(value) if len(token) > 2 and token not in STOP_WORDS}


def overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / math.sqrt(len(left) * len(right))


def response_type(response: str | None) -> str:
    if not (response or '').strip():
        return 'none'
    if DIAGNOSTIC_RESPONSE_RE.search(response):
        return 'diagnostic_question'
    if DIRECT_GUIDANCE_RE.search(response):
        return 'direct_guidance'
    if GENERIC_RESPONSE_RE.search(response):
        return 'generic_routing'
    return 'acknowledgement_or_other'


def score_candidate(query: str, result: dict, gold_intent: str | None) -> tuple[float, list[str], dict]:
    query_tokens = tokens(query)
    customer_tokens = tokens(result.get("retrieved_customer_text"))
    response_tokens = tokens(result.get("retrieved_historical_response"))
    query_customer_overlap = overlap_score(query_tokens, customer_tokens)
    query_response_overlap = overlap_score(query_tokens, response_tokens)
    response_available = bool((result.get("retrieved_historical_response") or "").strip())
    intent_agreement = bool(
        gold_intent
        and gold_intent in (result.get("retrieved_intent_ids") or [])
    )
    historical_response_type = response_type(result.get("retrieved_historical_response"))

    # Provisional diagnostic score, not a human relevance label. Intent agreement
    # is intentionally excluded from this score and retained as metadata only.
    components = {
        "response_availability": 0.35 if response_available else 0.0,
        "query_customer_overlap": 0.25 * min(query_customer_overlap, 1.0),
        "query_response_overlap": 0.25 * min(query_response_overlap, 1.0),
    }
    score = round(sum(components.values()), 6)
    flags = []
    if response_available:
        flags.append("historical_response_available")
    else:
        flags.append("no_historical_response")
    if query_customer_overlap >= 0.35:
        flags.append("strong_query_customer_overlap")
    elif query_customer_overlap >= 0.15:
        flags.append("some_query_customer_overlap")
    else:
        flags.append("weak_query_customer_overlap")
    if query_response_overlap >= 0.25:
        flags.append("response_lexically_related")
    elif query_response_overlap > 0.0:
        flags.append("limited_response_overlap")
    else:
        flags.append("no_response_overlap")
    if gold_intent is None:
        flags.append("intent_metric_ineligible")
    elif intent_agreement:
        flags.append("curated_intent_agreement")
    else:
        flags.append("curated_intent_mismatch_or_unavailable")
    if score >= 0.65:
        flags.append("strong_deterministic_evidence")
    elif score >= 0.35:
        flags.append("moderate_deterministic_evidence")
    else:
        flags.append("weak_deterministic_evidence")
    return score, flags, {
        "response_available": response_available,
        "query_customer_overlap": round(query_customer_overlap, 6),
        "query_response_overlap": round(query_response_overlap, 6),
        "curated_intent_agreement": intent_agreement if gold_intent else None,
        "retrieved_intent_ids": result.get("retrieved_intent_ids", []),
        "retrieved_primary_intent": result.get("retrieved_primary_intent"),
        "response_type": historical_response_type,
        "components": components,
    }


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build(golden_path: Path, results_path: Path, output_path: Path, summary_path: Path, report_path: Path) -> dict:
    golden = load_jsonl(golden_path)
    results = load_jsonl(results_path)
    golden_by_id = {row["golden_id"]: row for row in golden}
    grouped = defaultdict(list)
    for result in results:
        grouped[result["golden_id"]].append(result)
    for rows in grouped.values():
        rows.sort(key=lambda row: row.get("retrieved_rank") or 999999)

    evidence_rows = []
    for golden_record in golden:
        golden_id = golden_record["golden_id"]
        gold_intent = golden_record.get("evaluation", {}).get("gold_intent")
        for result in grouped.get(golden_id, []):
            score, flags, signals = score_candidate(golden_record.get("text", ""), result, gold_intent)
            notes = (
                "Deterministic evidence signals only; human relevance remains pending. "
                f"Components: response_available={signals['response_available']}, "
                f"query_customer_overlap={signals['query_customer_overlap']}, "
                f"query_response_overlap={signals['query_response_overlap']}, "
                f"curated_intent_agreement={signals['curated_intent_agreement']}."
            )
            evidence_rows.append({
                "golden_id": golden_id,
                "query": golden_record.get("text"),
                "original_gold_intent": gold_intent,
                "retrieval_rank": result.get("retrieved_rank"),
                "retrieved_message_id": result.get("retrieved_message_id"),
                "retrieved_conversation_id": result.get("retrieved_conversation_id"),
                "retrieved_customer_text": result.get("retrieved_customer_text"),
                "historical_response": result.get("retrieved_historical_response"),
                "similarity_score": result.get("similarity_score"),
                "deterministic_evidence_score": score,
                "evidence_flags": flags,
                "evidence_signals": signals,
                "retrieved_intent_ids": result.get("retrieved_intent_ids", []),
                "retrieved_primary_intent": result.get("retrieved_primary_intent"),
                "response_type": signals["response_type"],
                "human_relevance": None,
                "notes": notes,
            })

    eligible_ids = {row["golden_id"] for row in golden if row.get("evaluation", {}).get("gold_intent") is not None}
    score_distribution = Counter(
        "strong" if row["deterministic_evidence_score"] >= 0.65 else
        "moderate" if row["deterministic_evidence_score"] >= 0.35 else
        "weak"
        for row in evidence_rows
    )
    response_rows = [row for row in evidence_rows if row["historical_response"]]
    coverage = {}
    for cutoff in (1, 3, 5):
        covered = 0
        for golden_id in eligible_ids:
            candidates = [row for row in evidence_rows if row["golden_id"] == golden_id and row["retrieval_rank"] <= cutoff]
            if any(row["historical_response"] and row["deterministic_evidence_score"] >= 0.35 for row in candidates):
                covered += 1
        coverage[f"top_{cutoff}"] = {
            "covered_eligible_queries": covered,
            "eligible_queries": len(eligible_ids),
            "coverage": covered / len(eligible_ids) if eligible_ids else None,
            "rule": "At least one retrieved candidate in the cutoff has a historical response and provisional heuristic evidence score >= 0.35.",
        }
    no_response_queries = [
        golden_id for golden_id in golden_by_id
        if not any(row["golden_id"] == golden_id and row["historical_response"] for row in evidence_rows)
    ]
    summary = {
        "phase": "5",
        "total_golden_queries": len(golden),
        "eligible_queries": len(eligible_ids),
        "excluded_null_gold_intent_queries": len(golden) - len(eligible_ids),
        "total_retrieved_candidates": len(evidence_rows),
        "candidates_with_historical_responses": len(response_rows),
        "distribution_of_deterministic_evidence_scores": dict(sorted(score_distribution.items())),
        "heuristic_evidence_coverage": coverage,
        "response_type_distribution": dict(sorted(Counter(row["response_type"] for row in evidence_rows).items())),
        "queries_with_no_usable_historical_response": no_response_queries,
        "human_relevance": "pending; deterministic evidence is not a human relevance judgment",
        "deterministic_scoring_rules": {
            "response_availability": 0.35,
            "query_customer_overlap": 0.25,
            "query_response_overlap": 0.25,
            "curated_intent_agreement": "diagnostic metadata only; excluded from score",
            "strong_threshold": 0.65,
            "moderate_threshold": 0.35,
            "threshold_status": "provisional heuristic; not calibrated against human judgments",
        },
        "limitations": [
            "Lexical overlap does not establish semantic relevance or answer correctness.",
            "Retrieved intent metadata is Phase 3A heuristic evidence, not human truth.",
            "Null gold-intent queries are excluded from intent-based metrics but still receive evidence signals.",
            "Human relevance judgments remain pending.",
        ],
        "output_files": {
            "results": str(output_path),
            "summary": str(summary_path),
            "report": str(report_path),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        for row in evidence_rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Phase 5: Historical-Evidence Evaluation",
        "",
        "## Objective",
        "",
        "Evaluate whether Phase 4 historical retrieval results contain deterministic evidence useful for later grounded response work. This is not a human relevance evaluation and does not generate answers.",
        "",
        "## Inputs",
        "",
        "- Phase 3E annotated golden set.",
        "- Phase 4 retrieval results and summary.",
        "- Phase 2 conversation corpus through the Phase 4 retrieval outputs.",
        "- Phase 3A taxonomy metadata through the Phase 4 retrieval outputs.",
        "",
        "## Deterministic scoring",
        "",
        "- Historical response availability: 0.35.",
        "- Query/customer lexical overlap: 0.25.",
        "- Query/historical-response lexical overlap: 0.25.",
        "- Curated Phase 3E gold-intent agreement is retained as diagnostic metadata only and is excluded from the score.",
        "- Response-type diagnostics classify responses as none, generic_routing, diagnostic_question, direct_guidance, or acknowledgement_or_other.",
        "- Strong evidence is score >= 0.65; moderate evidence is >= 0.35; otherwise weak. The 0.35 cutoff is provisional and heuristic, not calibrated.",
        "- These scores and flags are transparent evidence signals, not human relevance labels.",
        "",
        "## Results",
        "",
        f"- Total golden queries: {len(golden)}",
        f"- Eligible queries: {len(eligible_ids)}",
        f"- Excluded null-gold-intent queries: {len(golden) - len(eligible_ids)}",
        f"- Total retrieved candidates: {len(evidence_rows)}",
        f"- Candidates with historical responses: {len(response_rows)}",
        f"- Queries with no usable historical response: {len(no_response_queries)}",
        "",
        "## Examples",
        "",
        "The examples below show deterministic evidence only. Human relevance remains pending.",
        "",
    ]
    for golden_id in [row["golden_id"] for row in golden[:10]]:
        top = next((row for row in evidence_rows if row["golden_id"] == golden_id and row["retrieval_rank"] == 1), None)
        if not top:
            continue
        report.extend([
            f"### {golden_id}",
            f"- QUERY: {top['query']}",
            f"- TOP RETRIEVAL: {top['retrieved_customer_text']}",
            f"- SIMILARITY: {top['similarity_score']}",
                f"- EVIDENCE SCORE: {top['deterministic_evidence_score']}",
                f"- RESPONSE TYPE: {top['response_type']}",
            f"- FLAGS: {', '.join(top['evidence_flags'])}",
            "- HUMAN RELEVANCE: pending",
            "",
        ])
    report.extend([
        "## Limitations",
        "",
        *[f"- {limitation}" for limitation in summary["limitations"]],
        "",
        "## Use in grounded response work",
        "",
        "This layer identifies which retrieved examples contain explicit historical-response and lexical evidence. A later grounded response system can use these signals for inspection and candidate selection, but must still verify semantic relevance and avoid treating retrieved text as an answer without appropriate grounding.",
        "",
        "## Files",
        "",
        f"- Evidence results: {output_path}",
        f"- Summary: {summary_path}",
        f"- Validator: work/phase5_validate.py",
    ])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    summary = build(args.golden, args.results, args.output, args.summary, args.report)
    print(json.dumps({
        "phase": summary["phase"],
        "total_golden_queries": summary["total_golden_queries"],
        "total_retrieved_candidates": summary["total_retrieved_candidates"],
        "summary": str(args.summary),
        "report": str(args.report),
    }, indent=2))


if __name__ == "__main__":
    main()
