#!/usr/bin/env python3
"""Resolve Phase 3D review records using exact Phase 2 historical context."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from annotate_golden_set import ESCALATION_PATTERNS, normalized  # noqa: E402
from build_candidate_pool import classify  # noqa: E402

GOLDEN_PATH = Path("outputs/phase3/golden_set/golden_evaluation_set.jsonl")
PRELIMINARY_PATH = Path("outputs/phase3/golden_set/golden_set_preliminary_annotations.jsonl")
REVIEW_PATH = Path("outputs/phase3/golden_set/golden_set_review_queue.jsonl")
CONVERSATIONS_PATH = Path("outputs/phase2/data/applesupport_conversations.jsonl")
ANNOTATED_PATH = Path("outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl")
DECISIONS_PATH = Path("outputs/phase3/golden_set/golden_set_annotation_decisions.jsonl")
SUMMARY_PATH = Path("outputs/phase3/golden_set/golden_set_annotation_summary.json")
REPORT_PATH = Path("outputs/phase3/reports/PHASE3E_REVIEW_RESOLUTION_REPORT.md")
TAXONOMY_PATH = Path("outputs/phase3/taxonomy/intent_taxonomy.json")
VALID_STATUSES = {"resolved_from_context", "resolved_from_text", "genuinely_ambiguous", "insufficient_evidence"}
GENERIC_RESPONSE_RE = re.compile(r"(?:dm|direct message|look into this|continue looking|continue in|thanks for letting us know|let us know|we'?d like to look into)", re.I)
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
STOP_WORDS = {"the", "a", "an", "and", "or", "but", "if", "then", "when", "while", "for", "with", "this", "that", "from", "about", "please", "help", "my", "your", "our", "i", "me", "you", "we", "they", "is", "are", "was", "were", "to", "of", "in", "on", "at", "it", "as", "so", "not", "no", "yes", "can", "could", "would", "should", "have", "has", "had", "do", "does", "did", "im", "apple", "support", "issue", "problem", "fix", "app", "apps", "phone", "just", "very", "really", "too", "also", "still", "again", "all", "any", "some", "more"}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def content_tokens(text: str) -> set[str]:
    value = re.sub(r"https?://\S+|@\w+|#\w+", " ", normalized(text))
    return {token for token in TOKEN_RE.findall(value) if len(token) > 2 and token not in STOP_WORDS}


def collect_contexts(conversation_path: Path, target_ids: set[str]) -> dict[str, dict]:
    contexts = {}
    with conversation_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            conversation = json.loads(line)
            messages = conversation.get("messages", [])
            matched = [message for message in messages if str(message.get("tweet_id")) in target_ids]
            if not matched:
                continue
            context = {
                "conversation_id": conversation.get("conversation_id"),
                "messages": messages,
            }
            for message in matched:
                contexts[str(message["tweet_id"])] = context
    return contexts


def context_evidence(messages: list[dict]) -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    evidence = defaultdict(set)
    evidence_messages = defaultdict(list)
    for message in messages:
        if message.get("role") != "customer_message":
            continue
        matches, _ = classify(str(message.get("text") or ""))
        for match in matches:
            intent_id = match["intent_id"]
            evidence[intent_id].update(match["evidence_patterns"])
            evidence_messages[intent_id].append(str(message.get("tweet_id")))
    return evidence, evidence_messages


def resolve_intent(record: dict, context: dict | None, taxonomy_ids: set[str]) -> tuple[str | None, list[str], str, str, dict]:
    existing = record.get("primary_intent")
    target_matches = record.get("matched_intent_ids", [])
    target_evidence = record.get("evidence_by_intent", {})
    evidence = defaultdict(set)
    evidence_messages = defaultdict(list)
    for intent_id, patterns in target_evidence.items():
        evidence[intent_id].update(patterns)
        evidence_messages[intent_id].append(record["message_id"])
    context_message_ids = []
    if context:
        context_evidence_map, context_message_map = context_evidence(context["messages"])
        for intent_id, patterns in context_evidence_map.items():
            evidence[intent_id].update(patterns)
            evidence_messages[intent_id].extend(context_message_map[intent_id])
        context_message_ids = [str(message.get("tweet_id")) for message in context["messages"]]

    scores = {intent_id: len(patterns) for intent_id, patterns in evidence.items() if intent_id in taxonomy_ids}
    strong = {intent_id: score for intent_id, score in scores.items() if score >= 2}
    ranked = sorted(strong.items(), key=lambda item: (-item[1], item[0]))
    provenance = {
        "conversation_id": context.get("conversation_id") if context else record.get("conversation_id"),
        "context_message_ids": context_message_ids,
        "intent_evidence_pattern_counts": dict(sorted(scores.items())),
        "intent_evidence_message_ids": {key: sorted(set(value)) for key, value in sorted(evidence_messages.items())},
    }

    if not ranked:
        return None, [], "insufficient_evidence", "low", provenance
    top_intent, top_score = ranked[0]
    alternatives = [intent_id for intent_id, score in ranked[1:] if score == top_score]
    if alternatives:
        acceptable = sorted(set(alternatives))
        if existing in {top_intent, *acceptable}:
            chosen = existing
        else:
            chosen = top_intent
        return chosen, acceptable, "genuinely_ambiguous", "medium", provenance
    if context and len(context.get("messages", [])) > 1:
        return top_intent, [], "resolved_from_context", "high", provenance
    if target_matches and top_intent in target_matches:
        return top_intent, [], "resolved_from_text", "medium", provenance
    return top_intent, [], "resolved_from_context", "medium", provenance


def escalation_for_context(record: dict, context: dict | None, status: str, confidence: str) -> tuple[bool | None, str]:
    texts = [record.get("text", "")]
    if context:
        texts.extend(str(message.get("text") or "") for message in context["messages"] if message.get("role") == "customer_message")
    combined = " ".join(texts).lower()
    reasons = [reason for reason, pattern in ESCALATION_PATTERNS if re.search(pattern, combined, re.I)]
    if reasons and status in {"resolved_from_context", "resolved_from_text"}:
        return True, "Historical context contains deterministic escalation indicators: " + "; ".join(reasons) + "."
    if status in {"genuinely_ambiguous", "insufficient_evidence"} or confidence == "low":
        return None, "Insufficient evidence for a final escalation decision."
    return False, "No deterministic escalation indicator found in the resolved historical context."


def historical_response(record: dict, context: dict | None) -> tuple[str | None, str | None, dict]:
    if not context:
        return None, None, {}
    messages = context["messages"]
    target_index = next((index for index, message in enumerate(messages) if str(message.get("tweet_id")) == str(record["message_id"])), None)
    if target_index is None:
        return None, None, {}
    if target_index + 1 >= len(messages) or messages[target_index + 1].get("role") != "brand_response":
        return None, None, {}
    response = messages[target_index + 1]
    response_text = str(response.get("text") or "")
    target_tokens = content_tokens(record.get("text", ""))
    response_tokens = content_tokens(response_text)
    overlap = target_tokens & response_tokens
    if len(response_text) < 30 or GENERIC_RESPONSE_RE.search(response_text) and len(overlap) < 2:
        return None, None, {}
    if not overlap and not re.search(r"\?", response_text):
        return None, None, {}
    evidence = {
        "response_tweet_id": str(response.get("tweet_id")),
        "response_role": response.get("role"),
        "response_text": response_text,
        "selection_rule": "Immediate brand_response after the target customer_message with non-generic direct overlap or a specific diagnostic question.",
        "content_token_overlap": sorted(overlap),
    }
    return response_text, "historical_conversation", evidence


def decision_for(record: dict, preliminary: dict, context: dict | None, taxonomy_ids: set[str]) -> dict:
    if record["golden_id"] not in {item["golden_id"] for item in []}:
        pass
    preliminary_annotation = preliminary.get("preliminary_annotation", {})
    if not preliminary_annotation.get("review_required"):
        gold_intent = preliminary_annotation.get("preliminary_intent")
        acceptable = []
        status = "resolved_from_text"
        confidence = "high" if gold_intent else "low"
        provenance = {
            "method": "phase3d_preliminary_inheritance",
            "source": "Phase 3A-derived primary_intent and original golden-set text",
            "human_reviewed": False,
        }
        escalation = preliminary_annotation.get("preliminary_escalation")
        escalation_reason = preliminary_annotation.get("preliminary_escalation_reason")
        response = None
        response_source = None
        response_evidence = {}
    else:
        gold_intent, acceptable, status, confidence, evidence = resolve_intent(record, context, taxonomy_ids)
        escalation, escalation_reason = escalation_for_context(record, context, status, confidence)
        response, response_source, response_evidence = historical_response(record, context)
        provenance = {
            "method": "phase3e_context_resolution",
            "source": "Exact Phase 2 conversation matched by message_id, plus Phase 3A taxonomy evidence",
            "human_reviewed": False,
            "historical_context": evidence,
        }
    return {
        "golden_id": record["golden_id"],
        "message_id": record["message_id"],
        "gold_intent": gold_intent,
        "acceptable_intents": acceptable,
        "annotation_status": status,
        "annotation_confidence": confidence,
        "should_escalate": escalation,
        "escalation_reason": escalation_reason,
        "gold_response": response,
        "gold_response_source": response_source,
        "retrieval_relevance": None,
        "response_grounding": None,
        "response_quality": None,
        "annotation_provenance": provenance,
        "historical_response_evidence": response_evidence or None,
    }


def build(golden_path: Path, preliminary_path: Path, review_path: Path, conversation_path: Path, taxonomy_path: Path, annotated_path: Path, decisions_path: Path, summary_path: Path, report_path: Path) -> dict:
    golden = read_jsonl(golden_path)
    preliminary_records = {row["golden_id"]: row for row in read_jsonl(preliminary_path)}
    review_ids = {row["golden_id"] for row in read_jsonl(review_path)}
    taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
    taxonomy_ids = {intent["intent_id"] for intent in taxonomy["intents"]}
    target_ids = {str(row["message_id"]) for row in golden if row["golden_id"] in review_ids}
    contexts = collect_contexts(conversation_path, target_ids)

    decisions = []
    annotated = []
    for record in golden:
        preliminary = preliminary_records[record["golden_id"]]
        context = contexts.get(str(record["message_id"]))
        decision = decision_for(record, preliminary, context, taxonomy_ids)
        decisions.append(decision)
        output = dict(record)
        evaluation = dict(record.get("evaluation", {}))
        evaluation.update({
            "gold_intent": decision["gold_intent"],
            "acceptable_intents": decision["acceptable_intents"],
            "gold_response": decision["gold_response"],
            "gold_response_source": decision["gold_response_source"],
            "retrieval_relevance": None,
            "response_grounding": None,
            "response_quality": None,
            "should_escalate": decision["should_escalate"],
            "escalation_reason": decision["escalation_reason"],
            "annotation_status": decision["annotation_status"],
            "annotation_confidence": decision["annotation_confidence"],
            "annotation_provenance": decision["annotation_provenance"],
        })
        output["evaluation"] = evaluation
        output["phase3e_historical_response_evidence"] = decision["historical_response_evidence"]
        annotated.append(output)

    annotated_path.parent.mkdir(parents=True, exist_ok=True)
    with annotated_path.open("w", encoding="utf-8") as stream:
        for row in annotated:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    review_decisions = [row for row in decisions if row["golden_id"] in review_ids]
    with decisions_path.open("w", encoding="utf-8") as stream:
        for row in review_decisions:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    status_counts = Counter(row["annotation_status"] for row in decisions)
    intent_counts = Counter(row["gold_intent"] for row in decisions if row["gold_intent"] is not None)
    escalation_counts = Counter(str(row["should_escalate"]).lower() for row in decisions)
    historical_count = sum(row["gold_response_source"] == "historical_conversation" for row in decisions)
    summary = {
        "phase": "3E",
        "total_records": len(annotated),
        "review_queue_records": len(review_ids),
        "context_matches": len(contexts),
        "resolved_count": sum(status_counts[state] for state in ("resolved_from_context", "resolved_from_text")),
        "unresolved_count": status_counts["genuinely_ambiguous"] + status_counts["insufficient_evidence"],
        "resolved_from_context_count": status_counts["resolved_from_context"],
        "resolved_from_text_count": status_counts["resolved_from_text"],
        "genuinely_ambiguous_count": status_counts["genuinely_ambiguous"],
        "insufficient_evidence_count": status_counts["insufficient_evidence"],
        "gold_intent_distribution": dict(sorted(intent_counts.items())),
        "escalation_distribution": {"true": escalation_counts["true"], "false": escalation_counts["false"], "null": escalation_counts["none"]},
        "historical_response_availability": {"available": historical_count, "null": len(decisions) - historical_count},
        "remaining_null_fields": {
            "gold_intent": sum(row["gold_intent"] is None for row in decisions),
            "gold_response": sum(row["gold_response"] is None for row in decisions),
            "should_escalate": sum(row["should_escalate"] is None for row in decisions),
            "retrieval_relevance": len(decisions),
            "response_grounding": len(decisions),
            "response_quality": len(decisions),
        },
        "annotation_provenance": "Phase 3D inheritance for high-confidence records; otherwise exact Phase 2 conversation context plus Phase 3A taxonomy evidence. No external model or human review was used.",
        "limitations": [
            "Phase 3A taxonomy labels remain discovery labels, not independently human-validated truth.",
            "Historical responses are copied only when the immediate brand response passes a conservative direct-relevance rule.",
            "Null gold intents and responses are retained when historical evidence is insufficient.",
            "This phase does not evaluate retrieval, grounding, or response quality.",
        ],
        "output_files": {"annotated_golden_set": str(annotated_path), "decisions": str(decisions_path), "summary": str(summary_path), "report": str(report_path)},
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = [
        "# Phase 3E: Review-Queue Resolution",
        "",
        "## Objective",
        "",
        "Resolve Phase 3D review records using exact Phase 2 conversation context and existing Phase 3A taxonomy evidence. No external model or fabricated support answer was used.",
        "",
        "## Results",
        "",
        f"- Total annotated records: {len(annotated)}",
        f"- Review-queue records: {len(review_ids)}",
        f"- Resolved: {summary['resolved_count']}",
        f"- Unresolved: {summary['unresolved_count']}",
        f"- Resolved from context: {summary['resolved_from_context_count']}",
        f"- Resolved from text: {summary['resolved_from_text_count']}",
        f"- Genuinely ambiguous: {summary['genuinely_ambiguous_count']}",
        f"- Insufficient evidence: {summary['insufficient_evidence_count']}",
        f"- Historical responses available: {historical_count}",
        "",
        "## Provenance",
        "",
        "Each decision records whether it came from Phase 3D inheritance or exact Phase 2 conversation context. Historical gold responses, when present, are copied verbatim from an observed brand_response record.",
        "",
        "## Limitations",
        "",
        *[f"- {limitation}" for limitation in summary["limitations"]],
        "",
        "## Files",
        "",
        f"- Annotated golden set: {annotated_path}",
        f"- Decisions: {decisions_path}",
        f"- Summary: {summary_path}",
        f"- Validator: work/phase3e_validate.py",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("--preliminary", type=Path, default=PRELIMINARY_PATH)
    parser.add_argument("--review", type=Path, default=REVIEW_PATH)
    parser.add_argument("--conversations", type=Path, default=CONVERSATIONS_PATH)
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    parser.add_argument("--annotated", type=Path, default=ANNOTATED_PATH)
    parser.add_argument("--decisions", type=Path, default=DECISIONS_PATH)
    parser.add_argument("--summary", type=Path, default=SUMMARY_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    summary = build(args.golden, args.preliminary, args.review, args.conversations, args.taxonomy, args.annotated, args.decisions, args.summary, args.report)
    print(json.dumps({"phase": summary["phase"], "total_records": summary["total_records"], "resolved_count": summary["resolved_count"], "unresolved_count": summary["unresolved_count"]}, indent=2))


if __name__ == "__main__":
    main()
