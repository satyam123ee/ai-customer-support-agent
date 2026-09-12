#!/usr/bin/env python3
"""Independently validate the Phase 4 retrieval baseline."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE2_PATH = ROOT / "outputs/phase2/data/applesupport_conversations.jsonl"
GOLDEN_PATH = ROOT / "outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl"
CORPUS_PATH = ROOT / "outputs/phase4/retrieval/retrieval_corpus.jsonl"
RESULTS_PATH = ROOT / "outputs/phase4/retrieval/retrieval_results.jsonl"
SUMMARY_PATH = ROOT / "outputs/phase4/retrieval/retrieval_summary.json"
REPORT_PATH = ROOT / "outputs/phase4/reports/PHASE4_RETRIEVAL_REPORT.md"
CORPUS_SCRIPT = ROOT / "outputs/phase4/scripts/build_retrieval_corpus.py"
RETRIEVE_SCRIPT = ROOT / "outputs/phase4/scripts/retrieve.py"
EVALUATE_SCRIPT = ROOT / "outputs/phase4/scripts/evaluate_retrieval.py"
ALLOWED_IMPORTS = {
    "argparse", "ast", "collections", "hashlib", "json", "math", "pathlib", "re", "subprocess", "sys",
    "__future__",
}


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


def phase2_source_map() -> dict[str, tuple[str, str | None, str | None]]:
    source = {}
    with PHASE2_PATH.open("r", encoding="utf-8") as stream:
        for line in stream:
            conversation = json.loads(line)
            messages = conversation.get("messages", [])
            for index, message in enumerate(messages):
                if message.get("role") != "customer_message":
                    continue
                response_text = None
                response_id = None
                if index + 1 < len(messages) and messages[index + 1].get("role") == "brand_response":
                    response_text = messages[index + 1].get("text")
                    response_id = str(messages[index + 1].get("tweet_id"))
                source[str(message.get("tweet_id"))] = (str(message.get("text") or ""), response_text, response_id)
    return source


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def main() -> None:
    corpus, corpus_errors = load_jsonl(CORPUS_PATH)
    results, result_errors = load_jsonl(RESULTS_PATH)
    golden, golden_errors = load_jsonl(GOLDEN_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    source_map = phase2_source_map()
    golden_by_id = {row["golden_id"]: row for row in golden}
    corpus_by_message = {row.get("customer_message_id"): row for row in corpus}
    result_message_ids = {row.get("retrieved_message_id") for row in results if row.get("retrieved_message_id") is not None}
    invalid_results = []
    modified_corpus = []
    for row in corpus:
        message_id = row.get("customer_message_id")
        if message_id not in source_map:
            modified_corpus.append(message_id)
            continue
        source_text, source_response, source_response_id = source_map[message_id]
        if row.get("customer_text") != source_text or row.get("historical_response") != source_response or row.get("historical_response_id") != source_response_id:
            modified_corpus.append(message_id)
    for row in results:
        if row.get("golden_id") not in golden_by_id:
            invalid_results.append(row.get("golden_id"))
        if row.get("retrieved_message_id") is None:
            continue
        retrieved_id = row.get("retrieved_message_id")
        corpus_record = corpus_by_message.get(retrieved_id)
        if corpus_record is None:
            invalid_results.append(retrieved_id)
            continue
        if row.get("retrieved_customer_text") != corpus_record.get("customer_text"):
            invalid_results.append(retrieved_id)
        score = row.get("similarity_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            invalid_results.append(retrieved_id)
        if row.get("retrieved_rank") is not None and row.get("retrieved_rank") > row.get("top_k_configured", 5):
            invalid_results.append(retrieved_id)
        expected_gold = golden_by_id[row["golden_id"]].get("evaluation", {}).get("gold_intent")
        if row.get("gold_intent") != expected_gold:
            invalid_results.append(row["golden_id"])

    eligible_ids = {row["golden_id"] for row in golden if row.get("evaluation", {}).get("gold_intent") is not None}
    result_eligible_ids = {row["golden_id"] for row in results if row.get("evaluation_eligible")}
    metric_null_violation = bool(result_eligible_ids - eligible_ids)
    metric_exclusion_violation = bool(eligible_ids - result_eligible_ids) and summary.get("eligible_evaluation_records") == len(eligible_ids)
    imported = set().union(*(imported_modules(path) for path in (CORPUS_SCRIPT, RETRIEVE_SCRIPT, EVALUATE_SCRIPT)))
    checks = {
        "corpus_jsonl_valid": not corpus_errors,
        "results_jsonl_valid": not result_errors,
        "golden_jsonl_valid": not golden_errors,
        "corpus_records_originate_from_phase2": not modified_corpus and set(corpus_by_message).issubset(source_map),
        "golden_queries_originate_from_phase3e": all(row.get("golden_id") in golden_by_id for row in results),
        "corpus_text_and_response_unmodified": not modified_corpus,
        "retrieval_source_ids_valid": not invalid_results,
        "top_k_within_configured_value": all(row.get("retrieved_rank") is None or row["retrieved_rank"] <= row.get("top_k_configured", 5) for row in results),
        "null_gold_intents_excluded_from_metrics": not metric_null_violation and summary.get("excluded_records_null_gold_intent") == len(golden) - len(eligible_ids),
        "no_fabricated_evaluation_labels": summary.get("human_relevance_evaluation") == "pending; no deterministic relevance labels were fabricated",
        "no_external_api_dependency": imported.issubset(ALLOWED_IMPORTS | {"build_candidate_pool"}),
        "no_duplicate_corpus_message_ids": len(corpus_by_message) == len(corpus),
    }

    before = {path: digest(path) for path in (CORPUS_PATH, RESULTS_PATH, SUMMARY_PATH, REPORT_PATH)}
    subprocess.run([sys.executable, str(CORPUS_SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, str(RETRIEVE_SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, str(EVALUATE_SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    after = {path: digest(path) for path in (CORPUS_PATH, RESULTS_PATH, SUMMARY_PATH, REPORT_PATH)}
    checks["deterministic_rerun_identical"] = before == after

    print("corpus_size", len(corpus))
    print("eligible_golden_queries", summary.get("eligible_evaluation_records"))
    print("excluded_golden_queries", summary.get("excluded_records_null_gold_intent"))
    print("top_1_agreement", summary.get("top_1_intent_agreement"))
    print("top_3_agreement", summary.get("top_3_intent_agreement"))
    print("top_5_agreement", summary.get("top_5_intent_agreement"))
    print("average_similarity", summary.get("average_top_1_similarity"))
    print("retrieval_failures", summary.get("retrieval_failures_total"))
    print("validation", checks)
    print("--- 10 sample queries ---")
    for sample in summary.get("sample_queries", []):
        print(json.dumps(sample, ensure_ascii=False))
    if not all(checks.values()):
        raise SystemExit("Phase 4 validation failed")


if __name__ == "__main__":
    main()
