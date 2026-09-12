#!/usr/bin/env python3
"""Phase 3A: reproducible, corpus-grounded AppleSupport intent discovery.

The input is the Phase 2 JSONL only. The script streams conversations, assigns
transparent evidence rules derived from recurring corpus phrases, and writes a
taxonomy with real examples. It does not build retrieval, embeddings, an agent,
or a golden evaluation set.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


WORD_RE = re.compile(r"[a-z][a-z0-9']*")

# These phrase families were selected after inspecting recurring terms and
# collocations in the Phase 2 customer-message corpus (for example: iOS/update,
# battery/life, App Store, Wi-Fi, Apple Music, question marks, High Sierra).
INTENTS = [
    {
        "intent_id": "software_update_os",
        "name": "Software and operating-system updates",
        "definition": "Problems installing, using, or recovering from iOS, macOS, or software updates.",
        "patterns": [r"\bios\b", r"\bmacos\b", r"\bhigh sierra\b", r"\bsoftware update", r"\bupdate[ds]?\b", r"\bupgrade[ds]?\b", r"\bbeta\b"],
    },
    {
        "intent_id": "battery_power_charging",
        "name": "Battery, power, and charging",
        "definition": "Battery-life, charging, power-on/off, or unexpected shutdown concerns.",
        "patterns": [r"\bbattery\b", r"\bcharg(?:e|ing|er)\b", r"\bpower\b", r"\bshut ?down\b", r"\bturn(?:ed)? off\b", r"\bwon'?t turn on\b"],
    },
    {
        "intent_id": "connectivity_network",
        "name": "Connectivity and network access",
        "definition": "Wi-Fi, Bluetooth, cellular, hotspot, signal, or network connection problems.",
        "patterns": [r"\bwi[ -]?fi\b", r"\bbluetooth\b", r"\bcellular\b", r"\bnetwork\b", r"\bhotspot\b", r"\bsignal\b", r"\b4g\b", r"\blte\b"],
    },
    {
        "intent_id": "apple_id_icloud_account",
        "name": "Apple ID, iCloud, and account access",
        "definition": "Apple ID, iCloud, sign-in, password, verification, or account-access concerns.",
        "patterns": [r"\bapple id\b", r"\bicloud\b", r"\bsign[ -]?in\b", r"\bpassword\b", r"\baccount\b", r"\bverification\b", r"\btwo[ -]?factor\b"],
    },
    {
        "intent_id": "app_store_media_services",
        "name": "App Store and Apple media services",
        "definition": "App Store, iTunes, Apple Music, podcasts, downloads, or media-library issues.",
        "patterns": [r"\bapp store\b", r"\bitunes\b", r"\bapple music\b", r"\bmusic\b", r"\bpodcast\b", r"\bdownload(?:ing|ed)?\b", r"\blibrary\b"],
    },
    {
        "intent_id": "billing_purchases_subscriptions",
        "name": "Billing, purchases, and subscriptions",
        "definition": "Charges, payments, refunds, purchases, subscriptions, or card-related support.",
        "patterns": [r"\bcharged\b", r"\bcharge(?: me| my| for)\b", r"\bbill(?:ing|ed)?\b", r"\bpayment\b", r"\bpurchase[ds]?\b", r"\brefund\b", r"\bsubscription\b", r"\bcredit card\b", r"\bmoney\b"],
    },
    {
        "intent_id": "messaging_calls_facetime",
        "name": "Messages, calls, and FaceTime",
        "definition": "iMessage, SMS/message delivery, calls, or FaceTime problems.",
        "patterns": [r"\bimessage\b", r"\bface ?time\b", r"\bsms\b", r"\btext(?:ing|s)?\b", r"\b(?:send|sent|receive|received|deliver(?:ed|y)?)\s+(?:a )?messages?\b", r"\bmessages?\s+(?:not|won|doesn|aren|isn't|are not|can't)\b", r"\bcalls?\b"],
    },
    {
        "intent_id": "hardware_accessories",
        "name": "Hardware, display, and accessories",
        "definition": "Physical device, screen, camera, audio, button, port, cable, or accessory problems.",
        "patterns": [r"\bscreen\b", r"\bcamera\b", r"\bspeaker\b", r"\bheadphones?\b", r"\bhome button\b", r"\btouch id\b", r"\blightning\b", r"\bcable\b", r"\bport\b", r"\bmicrophone\b"],
    },
    {
        "intent_id": "device_setup_activation_migration",
        "name": "Device setup, activation, and migration",
        "definition": "Setting up, activating, restoring, transferring, or replacing an iPhone/iPad/device.",
        "patterns": [r"\bactivat(?:e|ion|ed)\b", r"\bset ?up\b", r"\brestore\b", r"\btransfer\b", r"\bmigrat(?:e|ion)\b", r"\bnew (?:iphone|ipad|phone)\b", r"\breplacement\b"],
    },
    {
        "intent_id": "mac_computer",
        "name": "Mac computer support",
        "definition": "Mac, MacBook, iMac, or desktop/laptop concerns not primarily described as an OS update.",
        "patterns": [r"\bmacbook\b", r"\bimac\b", r"\bmac\b", r"\bmac mini\b"],
    },
    {
        "intent_id": "apple_watch",
        "name": "Apple Watch support",
        "definition": "Apple Watch or watchOS concerns.",
        "patterns": [r"\bapple watch\b", r"\bwatchos\b", r"\bmy watch\b"],
    },
    {
        "intent_id": "performance_stability",
        "name": "Performance, stability, and unexpected behavior",
        "definition": "Slow, frozen, crashing, stuck, glitching, or otherwise non-working behavior without a more specific primary issue.",
        "patterns": [r"\bslow\b", r"\bfreez(?:e|ing|es|en)\b", r"\bcrash(?:es|ed|ing)?\b", r"\blag(?:gy)?\b", r"\bglitch\b", r"\bstuck\b", r"\bnot working\b", r"\bdoesn'?t work\b"],
    },
    {
        "intent_id": "keyboard_text_rendering",
        "name": "Keyboard, characters, and text rendering",
        "definition": "Question-mark boxes, missing letters, keyboard, emoji, or character-rendering problems.",
        "patterns": [r"\bquestions? marks?\b", r"\bsquares?\b", r"\bkeyboard\b", r"\bletters?\b", r"\bcharacters?\b", r"\bemojis?\b", r"\btext rendering\b"],
    },
    {
        "intent_id": "support_contact_experience",
        "name": "Support contact and service experience",
        "definition": "Waiting, disconnection, direct-message, or customer-service contact problems rather than a specific product issue.",
        "patterns": [r"\bcustomer service\b", r"\bon hold\b", r"\bdisconnected\b", r"\bprivate messages?\b", r"\bcheck dm\b", r"\bwaiting\b", r"\bsupport (?:is|was|has)\b"],
    },
    {
        "intent_id": "store_orders_repairs",
        "name": "Store, order, delivery, and repair service",
        "definition": "Apple Store, repair, Genius Bar, order, delivery, shipping, or appointment concerns.",
        "patterns": [r"\bapple store\b", r"\brepair\b", r"\bgenius bar\b", r"\border\b", r"\bdeliver(?:y|ed)?\b", r"\bship(?:ping|ped)?\b", r"\bappointment\b"],
    },
]
for intent in INTENTS:
    intent["compiled_patterns"] = [re.compile(pattern, re.I) for pattern in intent["patterns"]]

NON_SUPPORT_RE = re.compile(r"^(?:thanks?|thank you|love (?:it|you)|great|awesome|good morning|hello|hi|hey)[! .😊❤️👍]*$", re.I)
MENTION_RE = re.compile(r"@\w+|https?://\S+", re.I)


def normalize(text: str) -> str:
    return " ".join(MENTION_RE.sub(" ", text).lower().split())


def content_word_count(text: str) -> int:
    return len(WORD_RE.findall(normalize(text)))


def classify(text: str) -> tuple[list[dict], str | None]:
    """Return all matched intent evidence and one deterministic primary label."""
    normalized = normalize(text)
    matches = []
    for intent in INTENTS:
        evidence = [p.pattern for p in intent["compiled_patterns"] if p.search(normalized)]
        if evidence:
            matches.append({"intent_id": intent["intent_id"], "evidence_patterns": evidence})
    if not matches:
        return matches, None
    # A stronger evidence count wins. The fixed INTENTS order resolves ties and
    # is recorded in the output, making aggregate counts reproducible.
    primary = max(enumerate(matches), key=lambda item: (len(item[1]["evidence_patterns"]), -item[0]))[1]["intent_id"]
    return matches, primary


def concise_example(text: str, limit: int = 320) -> str:
    return " ".join(text.split())[:limit]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("conversations_jsonl", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("."))
    parser.add_argument("--examples-per-intent", type=int, default=5)
    args = parser.parse_args()
    source = args.conversations_jsonl.resolve()
    root = args.output_root.resolve()
    taxonomy_dir = root / "taxonomy"
    taxonomy_dir.mkdir(parents=True, exist_ok=True)

    primary_counts: Counter[str] = Counter()
    matched_counts: Counter[str] = Counter()
    evidence_patterns: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)
    total = classified = ambiguous = multi_intent = too_short = non_support = unclassified = 0
    multi_intent_examples: list[dict[str, str]] = []
    unclassified_examples: list[dict[str, str]] = []
    non_support_examples: list[dict[str, str]] = []
    short_examples: list[dict[str, str]] = []

    with source.open("r", encoding="utf-8") as stream:
        for line in stream:
            conversation = json.loads(line)
            for message in conversation.get("messages", []):
                if message.get("role") != "customer_message":
                    continue
                total += 1
                text = str(message.get("text") or "")
                example = {"tweet_id": str(message.get("tweet_id") or ""), "text": concise_example(text)}
                normalized = normalize(text)
                word_count = content_word_count(text)
                if word_count <= 3:
                    too_short += 1
                    if len(short_examples) < 10:
                        short_examples.append(example)
                if NON_SUPPORT_RE.fullmatch(normalized):
                    non_support += 1
                    if len(non_support_examples) < 10:
                        non_support_examples.append(example)
                matches, primary = classify(text)
                if not matches:
                    unclassified += 1
                    if len(unclassified_examples) < 10:
                        unclassified_examples.append(example)
                    continue
                classified += 1
                primary_counts[primary] += 1
                for match in matches:
                    intent_id = match["intent_id"]
                    matched_counts[intent_id] += 1
                    evidence_patterns[intent_id].update(match["evidence_patterns"])
                if len(matches) > 1:
                    multi_intent += 1
                    if len(multi_intent_examples) < 10:
                        multi_intent_examples.append({**example, "matched_intent_ids": [m["intent_id"] for m in matches]})
                if word_count <= 3 or NON_SUPPORT_RE.fullmatch(normalized):
                    ambiguous += 1
                if len(examples[primary]) < args.examples_per_intent:
                    examples[primary].append(example)

    intents_output = []
    for intent in INTENTS:
        intent_id = intent["intent_id"]
        count = primary_counts[intent_id]
        intents_output.append({
            "intent_id": intent_id,
            "name": intent["name"],
            "definition": intent["definition"],
            "inclusion_criteria": "Customer message contains one or more observed corpus evidence patterns: " + ", ".join(intent["patterns"]),
            "exclusion_criteria": "No listed evidence pattern is present; messages matching several patterns retain all matches and are counted under the strongest-evidence primary label for aggregate totals.",
            "observed_evidence_patterns": evidence_patterns[intent_id].most_common(),
            "approximate_number_of_primary_examples": count,
            "percentage_of_all_customer_messages": round((count / total * 100) if total else 0, 3),
            "percentage_of_classified_customer_messages": round((count / classified * 100) if classified else 0, 3),
            "representative_real_customer_examples": examples[intent_id],
        })

    coverage = (classified / total) if total else 0
    diagnostics = {
        "total_customer_messages": total,
        "classified_messages": classified,
        "taxonomy_coverage": coverage,
        "unclassified_messages": unclassified,
        "unclassified_percentage": (unclassified / total) if total else 0,
        "multi_intent_messages": multi_intent,
        "multi_intent_percentage": (multi_intent / total) if total else 0,
        "too_short_messages": too_short,
        "too_short_percentage": (too_short / total) if total else 0,
        "non_support_like_messages": non_support,
        "non_support_like_percentage": (non_support / total) if total else 0,
        "low_information_or_non_support_messages": ambiguous,
        "low_information_or_non_support_percentage": (ambiguous / total) if total else 0,
        "multi_intent_examples": multi_intent_examples,
        "unclassified_examples": unclassified_examples,
        "too_short_examples": short_examples,
        "non_support_like_examples": non_support_examples,
    }
    readiness = {
        "rag_retrieval": "Sufficient volume for later retrieval experiments; use the prepared conversations and preserve direct-link limitations.",
        "automated_response_generation": "Sufficient historical customer-to-brand volume, but later work must separate safe answerable cases from cases requiring escalation.",
        "escalation_decisions": "Potentially sufficient for discovery, but no escalation labels have been created in this phase.",
        "golden_evaluation_set_150_250": "Sufficient source volume; a stratified, human-labelled set must still be created separately and is not produced here.",
    }
    taxonomy = {
        "phase": "3A",
        "scope": "Intent taxonomy discovery only",
        "source": str(source),
        "methodology": {
            "approach": "Streaming, deterministic phrase-family matching over actual Phase 2 customer messages.",
            "intent_count_rationale": "13 recurring phrase families were retained because each appears repeatedly in the corpus and maps to a distinguishable support problem surface. The remaining messages stay explicitly unclassified rather than being forced into a generic label.",
            "primary_label_rule": "Messages retain all matched labels. For totals, the primary label is the match with the most evidence patterns; the declared intent order breaks ties.",
            "limitations": [
                "This is discovery via transparent lexical evidence, not a human-validated final classifier.",
                "A message can legitimately involve more than one support issue.",
                "The Phase 2 extraction includes only directly observed TWCS relationship links.",
            ],
        },
        "intents": intents_output,
        "diagnostics": diagnostics,
        "readiness_assessment": readiness,
    }
    json_path = taxonomy_dir / "intent_taxonomy.json"
    json_path.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")

    report = [
        "# Phase 3A: AppleSupport Intent Taxonomy Discovery",
        "",
        "## Method",
        "",
        "This report is generated from the Phase 2 AppleSupport JSONL. The script streams customer messages, applies transparent phrase families found during corpus inspection, retains multi-intent matches, and leaves unmatched text unclassified rather than inventing a category.",
        "",
        "## Coverage and diagnostics",
        "",
        f"- Customer messages analyzed: {total:,}",
        f"- Classified messages: {classified:,} ({coverage:.2%})",
        f"- Unclassified messages: {unclassified:,} ({diagnostics['unclassified_percentage']:.2%})",
        f"- Multi-intent messages: {multi_intent:,} ({diagnostics['multi_intent_percentage']:.2%})",
        f"- Too-short messages: {too_short:,} ({diagnostics['too_short_percentage']:.2%})",
        f"- Non-support-like messages: {non_support:,} ({diagnostics['non_support_like_percentage']:.2%})",
        "",
        "## Proposed taxonomy",
        "",
    ]
    for intent in intents_output:
        report += [
            f"### {intent['name']} (`{intent['intent_id']}`)",
            "",
            intent["definition"],
            "",
            f"- Primary examples: {intent['approximate_number_of_primary_examples']:,} ({intent['percentage_of_all_customer_messages']:.3f}% of all customer messages)",
            f"- Inclusion: {intent['inclusion_criteria']}",
            f"- Exclusion: {intent['exclusion_criteria']}",
            "- Representative real customer messages:",
        ]
        for example in intent["representative_real_customer_examples"]:
            report.append(f"  - `{example['tweet_id']}` — {example['text']}")
        report.append("")
    report += [
        "## Readiness",
        "",
        f"- RAG retrieval: {readiness['rag_retrieval']}",
        f"- Automated response generation: {readiness['automated_response_generation']}",
        f"- Escalation decisions: {readiness['escalation_decisions']}",
        f"- 150–250 example golden evaluation set: {readiness['golden_evaluation_set_150_250']}",
        "",
        "## Scope boundary",
        "",
        "No RAG system, embeddings, LLM agent, golden set, or evaluation harness was built in this phase.",
    ]
    report_path = taxonomy_dir / "INTENT_TAXONOMY_REPORT.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({
        "intent_count": len(INTENTS), "diagnostics": diagnostics,
        "examples_per_intent": {item["intent_id"]: item["approximate_number_of_primary_examples"] for item in intents_output},
        "outputs": {"taxonomy": str(json_path), "report": str(report_path)},
    }, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
