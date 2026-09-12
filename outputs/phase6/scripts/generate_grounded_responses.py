#!/usr/bin/env python3
"""Generate deterministic responses copied only from usable historical evidence."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_GOLDEN = Path("outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl")
DEFAULT_EVIDENCE = Path("outputs/phase5/evidence/historical_evidence_results.jsonl")
DEFAULT_OUTPUT = Path("outputs/phase6/generation/golden_grounded_responses.jsonl")
DEFAULT_SUMMARY = Path("outputs/phase6/generation/phase6_generation_summary.json")
DEFAULT_REPORT = Path("outputs/phase6/reports/PHASE6_GROUNDED_RESPONSE_REPORT.md")
USABLE_RESPONSE_TYPES = {"diagnostic_question", "direct_guidance"}
MIN_EVIDENCE_SCORE = 0.35


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def choose_evidence(rows: list[dict]) -> dict | None:
    usable = [
        row for row in rows
        if row.get("historical_response")
        and row.get("deterministic_evidence_score", 0.0) >= MIN_EVIDENCE_SCORE
        and row.get("response_type") in USABLE_RESPONSE_TYPES
    ]
    usable.sort(key=lambda row: (-row.get("deterministic_evidence_score", 0.0), row.get("retrieval_rank", 999999), str(row.get("retrieved_message_id"))))
    return usable[0] if usable else None


def build(golden_path: Path, evidence_path: Path, output_path: Path, summary_path: Path, report_path: Path) -> dict:
    golden = load_jsonl(golden_path)
    evidence = load_jsonl(evidence_path)
    evidence_by_query = defaultdict(list)
    for row in evidence:
        evidence_by_query[row["golden_id"]].append(row)

    outputs = []
    statuses = Counter()
    response_types = Counter()
    for record in golden:
        candidates = evidence_by_query.get(record["golden_id"], [])
        selected = choose_evidence(candidates)
        existing_escalation = record.get("evaluation", {}).get("should_escalate")
        if selected:
            generated_response = selected["historical_response"]
            grounding_status = "grounded_historical_response"
            needs_escalation = False
            status = "usable_evidence_selected"
            selected_evidence = [{
                "retrieval_rank": selected["retrieval_rank"],
                "retrieved_message_id": selected["retrieved_message_id"],
                "retrieved_conversation_id": selected["retrieved_conversation_id"],
                "historical_response": selected["historical_response"],
                "deterministic_evidence_score": selected["deterministic_evidence_score"],
                "response_type": selected["response_type"],
                "retrieved_intent_ids": selected.get("retrieved_intent_ids", []),
                "retrieved_primary_intent": selected.get("retrieved_primary_intent"),
            }]
            response_types[selected["response_type"]] += 1
        else:
            generated_response = None
            grounding_status = "insufficient_historical_evidence"
            needs_escalation = True if existing_escalation is True or not candidates else None
            status = "weak_or_no_usable_evidence"
            selected_evidence = []
        statuses[status] += 1
        outputs.append({
            "query_id": record["golden_id"],
            "customer_message": record["text"],
            "selected_evidence": selected_evidence,
            "generated_response": generated_response,
            "generation_method": "deterministic_historical_grounding",
            "grounding_status": grounding_status,
            "evidence_score": selected["deterministic_evidence_score"] if selected else None,
            "needs_escalation": needs_escalation,
            "diagnostics": {
                "status": status,
                "candidate_count": len(candidates),
                "usable_response_types": sorted(USABLE_RESPONSE_TYPES),
                "minimum_evidence_score": MIN_EVIDENCE_SCORE,
                "response_copied_verbatim": bool(selected),
                "unsupported_content_risk": "low" if selected else "not_applicable",
                "human_response_quality_label": None,
            },
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        for row in outputs:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    escalation_counts = Counter(str(row["needs_escalation"]).lower() for row in outputs)
    summary = {
        "phase": "6",
        "total_queries": len(outputs),
        "usable_evidence_selected": statuses["usable_evidence_selected"],
        "weak_or_no_usable_evidence": statuses["weak_or_no_usable_evidence"],
        "responses_copied_verbatim": sum(row["generated_response"] is not None for row in outputs),
        "grounding_status_distribution": dict(sorted(Counter(row["grounding_status"] for row in outputs).items())),
        "response_type_distribution": dict(sorted(response_types.items())),
        "needs_escalation_distribution": {"true": escalation_counts["true"], "false": escalation_counts["false"], "null": escalation_counts["none"]},
        "unsupported_content_risk_distribution": dict(sorted(Counter(row["diagnostics"]["unsupported_content_risk"] for row in outputs).items())),
        "methodology": {
            "selection": "Choose the highest deterministic Phase 5 evidence score among candidates with historical response, score >= 0.35, and response_type diagnostic_question or direct_guidance.",
            "generation": "Copy the selected historical response verbatim; no new troubleshooting steps or product claims are generated.",
            "insufficient_evidence": "Return generated_response null and mark grounding insufficient when no usable historical response exists.",
            "human_labels": "No human response-quality labels are assigned.",
        },
        "limitations": [
            "This is a deterministic historical-response copying baseline, not an LLM response generator.",
            "A historically useful response may still be wrong for the current query; semantic human review remains necessary.",
            "Generic routing responses are not selected as generated answers.",
            "No external API or LLM was used.",
        ],
        "output_files": {"responses": str(output_path), "summary": str(summary_path), "report": str(report_path)},
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Phase 6: Grounded AI Response Generation",
        "",
        "## Architecture",
        "",
        "Golden query -> Phase 4 retrieval candidates -> Phase 5 deterministic evidence signals -> conservative evidence selection -> verbatim historical response or null.",
        "",
        "## Generation method",
        "",
        "- Select the highest-scoring Phase 5 candidate with a response, score >= 0.35, and response type `diagnostic_question` or `direct_guidance`.",
        "- Copy the selected historical AppleSupport response verbatim.",
        "- Do not invent troubleshooting steps, product claims, escalation labels, or human quality labels.",
        "- Generic routing-only responses are not emitted as generated answers.",
        "",
        "## Results",
        "",
        f"- Total queries: {len(outputs)}",
        f"- Usable evidence selected: {summary['usable_evidence_selected']}",
        f"- Weak/no usable evidence: {summary['weak_or_no_usable_evidence']}",
        f"- Responses copied verbatim: {summary['responses_copied_verbatim']}",
        f"- Needs escalation true: {summary['needs_escalation_distribution']['true']}",
        f"- Needs escalation false: {summary['needs_escalation_distribution']['false']}",
        f"- Needs escalation null: {summary['needs_escalation_distribution']['null']}",
        "",
        "## Grounding and safety diagnostics",
        "",
        *[f"- {key}: {value}" for key, value in sorted(summary["grounding_status_distribution"].items())],
        *[f"- response_type_{key}: {value}" for key, value in sorted(summary["response_type_distribution"].items())],
        "",
        "No human response-quality labels were generated. Phase 6 is a deterministic prototype only; Phase 7 is not started.",
        "",
        "## Limitations",
        "",
        *[f"- {limitation}" for limitation in summary["limitations"]],
        "",
        "## Files",
        "",
        f"- Responses: {output_path}",
        f"- Summary: {summary_path}",
        f"- Validator: work/phase6_validate.py",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    summary = build(args.golden, args.evidence, args.output, args.summary, args.report)
    print(json.dumps({"phase": summary["phase"], "total_queries": summary["total_queries"], "usable_evidence_selected": summary["usable_evidence_selected"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
