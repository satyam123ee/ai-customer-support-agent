#!/usr/bin/env python3
"""Validate Phase 6 deterministic grounded-response generation."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl"
EVIDENCE = ROOT / "outputs/phase5/evidence/historical_evidence_results.jsonl"
OUTPUT = ROOT / "outputs/phase6/generation/golden_grounded_responses.jsonl"
SUMMARY = ROOT / "outputs/phase6/generation/phase6_generation_summary.json"
REPORT = ROOT / "outputs/phase6/reports/PHASE6_GROUNDED_RESPONSE_REPORT.md"
SCRIPT = ROOT / "outputs/phase6/scripts/generate_grounded_responses.py"
ALLOWED_IMPORTS = {"__future__", "argparse", "collections", "json", "pathlib"}
VALID_STATUS = {"grounded_historical_response", "insufficient_historical_evidence"}


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
    golden = load(GOLDEN)
    evidence = load(EVIDENCE)
    outputs = load(OUTPUT)
    golden_by_id = {row["golden_id"]: row for row in golden}
    evidence_by_id = {}
    for row in evidence:
        evidence_by_id.setdefault(row["golden_id"], []).append(row)
    evidence_keys = {
        (row["golden_id"], row["retrieval_rank"], row.get("retrieved_message_id"))
        for row in evidence
    }
    output_ids = [row.get("query_id") for row in outputs]
    invalid = []
    for row in outputs:
        query_id = row.get("query_id")
        source = golden_by_id.get(query_id)
        if source is None or row.get("customer_message") != source.get("text"):
            invalid.append(query_id)
        if row.get("grounding_status") not in VALID_STATUS:
            invalid.append(query_id)
        selected = row.get("selected_evidence", [])
        response = row.get("generated_response")
        if response is not None:
            if len(selected) != 1:
                invalid.append(query_id)
            else:
                evidence_row = selected[0]
                key = (query_id, evidence_row.get("retrieval_rank"), evidence_row.get("retrieved_message_id"))
                if key not in evidence_keys or response != evidence_row.get("historical_response"):
                    invalid.append(query_id)
                if evidence_row.get("response_type") not in {"diagnostic_question", "direct_guidance"}:
                    invalid.append(query_id)
                if evidence_row.get("deterministic_evidence_score", 0) < 0.35:
                    invalid.append(query_id)
        else:
            if selected:
                invalid.append(query_id)
        if row.get("diagnostics", {}).get("human_response_quality_label") is not None:
            invalid.append(query_id)

    before = {path: digest(path) for path in (OUTPUT, SUMMARY, REPORT)}
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    after = {path: digest(path) for path in (OUTPUT, SUMMARY, REPORT)}
    checks = {
        "exactly_200_queries": len(outputs) == 200,
        "unique_query_ids": len(output_ids) == len(set(output_ids)),
        "source_query_text_matches_golden": not invalid,
        "selected_evidence_originates_from_phase5": not invalid,
        "responses_use_supported_historical_evidence": not invalid,
        "no_fabricated_evidence_ids": not invalid,
        "no_external_api_dependency": imports(SCRIPT).issubset(ALLOWED_IMPORTS),
        "deterministic_rerun_identical": before == after,
        "human_quality_labels_absent": not invalid,
    }
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    print("total_queries", len(outputs))
    print("usable_evidence_selected", summary.get("usable_evidence_selected"))
    print("weak_or_no_usable_evidence", summary.get("weak_or_no_usable_evidence"))
    print("grounding_status_distribution", summary.get("grounding_status_distribution"))
    print("needs_escalation_distribution", summary.get("needs_escalation_distribution"))
    print("validation", checks)
    if not all(checks.values()):
        raise SystemExit("Phase 6 validation failed")


if __name__ == "__main__":
    main()
