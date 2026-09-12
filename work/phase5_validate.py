#!/usr/bin/env python3
"""Independently validate Phase 5 historical-evidence outputs."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl"
RETRIEVAL_PATH = ROOT / "outputs/phase4/retrieval/retrieval_results.jsonl"
EVIDENCE_PATH = ROOT / "outputs/phase5/evidence/historical_evidence_results.jsonl"
SUMMARY_PATH = ROOT / "outputs/phase5/evidence/historical_evidence_summary.json"
REPORT_PATH = ROOT / "outputs/phase5/reports/PHASE5_HISTORICAL_EVIDENCE_REPORT.md"
SCRIPT_PATH = ROOT / "outputs/phase5/scripts/evaluate_historical_evidence.py"
ALLOWED_IMPORTS = {"__future__", "argparse", "collections", "json", "math", "pathlib", "re"}


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


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def main() -> None:
    golden, golden_errors = load_jsonl(GOLDEN_PATH)
    retrieval, retrieval_errors = load_jsonl(RETRIEVAL_PATH)
    evidence, evidence_errors = load_jsonl(EVIDENCE_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    golden_by_id = {row["golden_id"]: row for row in golden}
    retrieval_by_id = defaultdict(list)
    for row in retrieval:
        retrieval_by_id[row["golden_id"]].append(row)
    evidence_by_id = defaultdict(list)
    for row in evidence:
        evidence_by_id[row["golden_id"]].append(row)

    invalid_source = []
    text_changed = []
    response_changed = []
    human_labels = []
    for row in evidence:
        golden_record = golden_by_id.get(row.get("golden_id"))
        if golden_record is None:
            invalid_source.append(row.get("golden_id"))
            continue
        if row.get("query") != golden_record.get("text"):
            text_changed.append(row.get("golden_id"))
        if row.get("human_relevance") is not None:
            human_labels.append(row.get("golden_id"))
        retrieval_candidates = retrieval_by_id[row["golden_id"]]
        matching = [candidate for candidate in retrieval_candidates if candidate.get("retrieved_rank") == row.get("retrieval_rank")]
        if not matching:
            invalid_source.append(row.get("retrieved_message_id"))
            continue
        candidate = matching[0]
        for field in ("retrieved_message_id", "retrieved_conversation_id", "retrieved_customer_text", "historical_response", "similarity_score"):
            evidence_field = "historical_response" if field == "historical_response" else field
            candidate_field = "retrieved_historical_response" if field == "historical_response" else field
            if row.get(evidence_field) != candidate.get(candidate_field):
                if field == "retrieved_customer_text":
                    text_changed.append(row.get("golden_id"))
                elif field == "historical_response":
                    response_changed.append(row.get("golden_id"))
                else:
                    invalid_source.append(row.get("golden_id"))

    exact_five = all(len(retrieval_by_id[golden_id]) == 5 for golden_id in golden_by_id if retrieval_by_id[golden_id])
    all_represented = set(evidence_by_id) == set(golden_by_id)
    eligible_ids = {row["golden_id"] for row in golden if row.get("evaluation", {}).get("gold_intent") is not None}
    null_gold_intent_violation = any(
        row.get("original_gold_intent") is None and row.get("evidence_signals", {}).get("curated_intent_agreement") is True
        for row in evidence
    )
    response_types_valid = all(
        row.get("response_type") in {"none", "generic_routing", "diagnostic_question", "direct_guidance", "acknowledgement_or_other"}
        for row in evidence
    )
    checks = {
        "jsonl_valid": not golden_errors and not retrieval_errors and not evidence_errors,
        "exactly_200_golden_queries_represented": len(evidence_by_id) == 200 and all_represented,
        "exactly_5_retrieval_candidates_where_available": exact_five,
        "retrieved_ids_originate_from_phase4": not invalid_source,
        "source_text_unchanged": not text_changed,
        "historical_responses_unchanged": not response_changed,
        "no_fabricated_human_relevance": not human_labels,
        "null_gold_intents_excluded_from_intent_signals": not null_gold_intent_violation,
        "response_type_diagnostics_valid": response_types_valid,
        "intent_agreement_excluded_from_score": all("curated_intent_agreement" not in row.get("evidence_signals", {}).get("components", {}) for row in evidence),
        "no_external_api_dependency": imports(SCRIPT_PATH).issubset(ALLOWED_IMPORTS),
    }
    before = {path: digest(path) for path in (EVIDENCE_PATH, SUMMARY_PATH, REPORT_PATH)}
    subprocess.run([sys.executable, str(SCRIPT_PATH)], cwd=ROOT, check=True, capture_output=True, text=True)
    after = {path: digest(path) for path in (EVIDENCE_PATH, SUMMARY_PATH, REPORT_PATH)}
    checks["deterministic_rerun_identical"] = before == after

    score_counts = Counter(
        "strong" if row["deterministic_evidence_score"] >= 0.65 else
        "moderate" if row["deterministic_evidence_score"] >= 0.35 else
        "weak"
        for row in evidence
    )
    print("total_golden_queries", len(golden))
    print("total_evidence_rows", len(evidence))
    print("eligible_queries", summary.get("eligible_queries"))
    print("excluded_null_gold_intent_queries", summary.get("excluded_null_gold_intent_queries"))
    print("candidates_with_historical_responses", summary.get("candidates_with_historical_responses"))
    print("score_distribution", dict(sorted(score_counts.items())))
    print("heuristic_evidence_coverage", summary.get("heuristic_evidence_coverage"))
    print("response_type_distribution", summary.get("response_type_distribution"))
    print("queries_with_no_usable_historical_response", len(summary.get("queries_with_no_usable_historical_response", [])))
    print("validation", checks)
    print("human_relevance", summary.get("human_relevance"))
    if not all(checks.values()):
        raise SystemExit("Phase 5 validation failed")


if __name__ == "__main__":
    main()
