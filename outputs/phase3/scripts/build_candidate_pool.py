#!/usr/bin/env python3
"""Phase 3B: build a candidate pool of real AppleSupport customer messages.

This script reads the Phase 2 AppleSupport JSONL, reuses the same transparent
intent rules established in Phase 3A, and creates a reproducible, stratified
candidate pool for later human labeling and golden-set construction.

It intentionally does not invent labels, does not overwrite the earlier outputs,
and does not require loading the full 493 MB TWCS CSV into memory.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


INTENTS = [
    {
        "intent_id": "software_update_os",
        "name": "Software and operating-system updates",
        "patterns": [r"\bios\b", r"\bmacos\b", r"\bhigh sierra\b", r"\bsoftware update", r"\bupdate[ds]?\b", r"\bupgrade[ds]?\b", r"\bbeta\b"],
    },
    {
        "intent_id": "battery_power_charging",
        "name": "Battery, power, and charging",
        "patterns": [r"\bbattery\b", r"\bcharg(?:e|ing|er)\b", r"\bpower\b", r"\bshut ?down\b", r"\bturn(?:ed)? off\b", r"\bwon'?t turn on\b"],
    },
    {
        "intent_id": "connectivity_network",
        "name": "Connectivity and network access",
        "patterns": [r"\bwi[ -]?fi\b", r"\bbluetooth\b", r"\bcellular\b", r"\bnetwork\b", r"\bhotspot\b", r"\bsignal\b", r"\b4g\b", r"\blte\b"],
    },
    {
        "intent_id": "apple_id_icloud_account",
        "name": "Apple ID, iCloud, and account access",
        "patterns": [r"\bapple id\b", r"\bicloud\b", r"\bsign[ -]?in\b", r"\bpassword\b", r"\baccount\b", r"\bverification\b", r"\btwo[ -]?factor\b"],
    },
    {
        "intent_id": "app_store_media_services",
        "name": "App Store and Apple media services",
        "patterns": [r"\bapp store\b", r"\bitunes\b", r"\bapple music\b", r"\bmusic\b", r"\bpodcast\b", r"\bdownload(?:ing|ed)?\b", r"\blibrary\b"],
    },
    {
        "intent_id": "billing_purchases_subscriptions",
        "name": "Billing, purchases, and subscriptions",
        "patterns": [r"\bcharged\b", r"\bcharge(?: me| my| for)\b", r"\bbill(?:ing|ed)?\b", r"\bpayment\b", r"\bpurchase[ds]?\b", r"\brefund\b", r"\bsubscription\b", r"\bcredit card\b", r"\bmoney\b"],
    },
    {
        "intent_id": "messaging_calls_facetime",
        "name": "Messages, calls, and FaceTime",
        "patterns": [r"\bimessage\b", r"\bface ?time\b", r"\bsms\b", r"\btext(?:ing|s)?\b", r"\b(?:send|sent|receive|received|deliver(?:ed|y)?)\s+(?:a )?messages?\b", r"\bmessages?\s+(?:not|won|doesn|aren|isn't|are not|can't)\b", r"\bcalls?\b"],
    },
    {
        "intent_id": "hardware_accessories",
        "name": "Hardware, display, and accessories",
        "patterns": [r"\bscreen\b", r"\bcamera\b", r"\bspeaker\b", r"\bheadphones?\b", r"\bhome button\b", r"\btouch id\b", r"\blightning\b", r"\bcable\b", r"\bport\b", r"\bmicrophone\b"],
    },
    {
        "intent_id": "device_setup_activation_migration",
        "name": "Device setup, activation, and migration",
        "patterns": [r"\bactivat(?:e|ion|ed)\b", r"\bset ?up\b", r"\brestore\b", r"\btransfer\b", r"\bmigrat(?:e|ion)\b", r"\bnew (?:iphone|ipad|phone)\b", r"\breplacement\b"],
    },
    {
        "intent_id": "mac_computer",
        "name": "Mac computer support",
        "patterns": [r"\bmacbook\b", r"\bimac\b", r"\bmac\b", r"\bmac mini\b"],
    },
    {
        "intent_id": "apple_watch",
        "name": "Apple Watch support",
        "patterns": [r"\bapple watch\b", r"\bwatchos\b", r"\bmy watch\b"],
    },
    {
        "intent_id": "performance_stability",
        "name": "Performance, stability, and unexpected behavior",
        "patterns": [r"\bslow\b", r"\bfreez(?:e|ing|es|en)\b", r"\bcrash(?:es|ed|ing)?\b", r"\blag(?:gy)?\b", r"\bglitch\b", r"\bstuck\b", r"\bnot working\b", r"\bdoesn'?t work\b"],
    },
    {
        "intent_id": "keyboard_text_rendering",
        "name": "Keyboard, characters, and text rendering",
        "patterns": [r"\bquestions? marks?\b", r"\bsquares?\b", r"\bkeyboard\b", r"\bletters?\b", r"\bcharacters?\b", r"\bemojis?\b", r"\btext rendering\b"],
    },
    {
        "intent_id": "support_contact_experience",
        "name": "Support contact and service experience",
        "patterns": [r"\bcustomer service\b", r"\bon hold\b", r"\bdisconnected\b", r"\bprivate messages?\b", r"\bcheck dm\b", r"\bwaiting\b", r"\bsupport (?:is|was|has)\b"],
    },
    {
        "intent_id": "store_orders_repairs",
        "name": "Store, order, delivery, and repair service",
        "patterns": [r"\bapple store\b", r"\brepair\b", r"\bgenius bar\b", r"\border\b", r"\bdeliver(?:y|ed)?\b", r"\bship(?:ping|ped)?\b", r"\bappointment\b"],
    },
]

INTENT_INDEX = {intent["intent_id"]: intent for intent in INTENTS}
for intent in INTENTS:
    intent["compiled_patterns"] = [re.compile(pattern, re.I) for pattern in intent["patterns"]]

WORD_RE = re.compile(r"[a-z][a-z0-9']*")
MENTION_RE = re.compile(r"@\w+|https?://\S+", re.I)
NON_SUPPORT_RE = re.compile(r"^(?:thanks?|thank you|love (?:it|you)|great|awesome|good morning|hello|hi|hey)[! .😊❤️👍]*$", re.I)
QUALITY_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)
MOJIBAKE_MARKERS = set("ï¿¸âÃÂãðÐþÞýÝ")
QUALITY_STOP_WORDS = {
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

def normalize(text: str) -> str:
    return " ".join(MENTION_RE.sub(" ", text).lower().split())


def content_word_count(text: str) -> int:
    return len(WORD_RE.findall(normalize(text)))


def quality_tokens(text: str) -> list[str]:
    return QUALITY_TOKEN_RE.findall(normalize(text))


def quality_canonical(text: str) -> str:
    canonical = normalize(text)
    canonical = re.sub(r"https?://\S+|www\.\S+", " ", canonical, flags=re.I)
    canonical = re.sub(r"@\w+|#\w+", " ", canonical)
    canonical = re.sub(r"[^a-z0-9\s]", " ", canonical)
    return " ".join(canonical.split())


def quality_content_tokens(text: str) -> set[str]:
    return {
        token for token in quality_canonical(text).split()
        if len(token) > 2 and token not in QUALITY_STOP_WORDS
    }


def has_probable_mojibake(text: str) -> bool:
    """Flag clear mojibake clusters without rejecting ordinary multilingual text."""
    if len(re.findall(r"I[\ufe0e\ufe0f]", text or "")) >= 4:
        return True
    for token in re.findall(r"\S+", text or ""):
        if len(token) > 24 or not any(char in MOJIBAKE_MARKERS for char in token):
            continue
        if re.search(r"(?:ï¿|ï¸|Ã¢|Ã©|Ã±|Ã¼|Â\s|â€™|ðŸ)", token, re.I):
            return True
        if re.search(r"[a-z0-9][ï¿¸âÃÂãðÐþÞýÝ]{2,}|[ï¿¸âÃÂãðÐþÞýÝ]{2,}[a-z0-9]", token, re.I):
            return True
    return False


def quality_rejection_reason(item, accepted_content_tokens, accepted_canonicals):
    text = item["text"] or ""
    tokens = quality_tokens(text)
    if not text.strip() or not tokens:
        return "empty_or_non_informative"
    unique_ratio = len(set(tokens)) / len(tokens)
    if len(tokens) >= 8 and unique_ratio < 0.2:
        return "low_token_diversity"
    token_counts = Counter(tokens)
    if len(tokens) >= 8 and token_counts.most_common(1)[0][1] / len(tokens) >= 0.5:
        return "repeated_token_noise"
    if has_probable_mojibake(text):
        return "mojibake_or_unicode_artifact"
    canonical = quality_canonical(text)
    if canonical in accepted_canonicals:
        return "exact_duplicate"
    content = quality_content_tokens(text)
    if len(content) >= 6:
        for accepted in accepted_content_tokens:
            overlap = len(content & accepted)
            if overlap >= 4 and overlap / min(len(content), len(accepted)) >= 0.7 and len(content | accepted) >= 6:
                return "clearly_redundant_near_duplicate"
    return None


def quality_filter_select(items, limit):
    selected = []
    accepted_content_tokens = []
    accepted_canonicals = set()
    rejection_counts = Counter()
    replacement_examples = []
    replacement_counts_by_bucket = Counter()
    pending_rejections = []
    for item in items:
        if len(selected) >= limit:
            break
        reason = quality_rejection_reason(item, accepted_content_tokens, accepted_canonicals)
        if reason:
            rejection_counts[reason] += 1
            replacement_counts_by_bucket[items[0]["bucket"]] += 1
            pending_rejections.append((reason, item))
            continue
        selected.append(item)
        accepted_content_tokens.append(quality_content_tokens(item["text"]))
        accepted_canonicals.add(quality_canonical(item["text"]))
        if pending_rejections and len(replacement_examples) < 10:
            reason, rejected = pending_rejections.pop(0)
            replacement_examples.append({
                "bucket": item["bucket"],
                "reason": reason,
                "rejected_tweet_id": rejected["tweet_id"],
                "rejected_text": rejected["text"],
                "replacement_tweet_id": item["tweet_id"],
                "replacement_text": item["text"],
            })
    if len(selected) != limit:
        raise ValueError(
            f"Quality-filtered bucket has insufficient candidates: selected={len(selected)} target={limit}"
        )
    return selected, rejection_counts, replacement_examples, replacement_counts_by_bucket


def classify(text: str):
    normalized = normalize(text)
    matches = []
    for intent in INTENTS:
        evidence = [pattern.pattern for pattern in intent["compiled_patterns"] if pattern.search(normalized)]
        if evidence:
            matches.append({"intent_id": intent["intent_id"], "evidence_patterns": evidence})
    if not matches:
        return matches, None
    primary = max(enumerate(matches), key=lambda item: (len(item[1]["evidence_patterns"]), -item[0]))[1]["intent_id"]
    return matches, primary


def parse_timestamp(value: str | None):
    try:
        if not value:
            return None
        return datetime.strptime(value.strip(), "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc)
    except ValueError:
        return None


def select_by_bucket(items, limit):
    if not items:
        return []
    ranked = sorted(
        items,
        key=lambda item: (
            -item["evidence_strength"],
            -item["content_word_count"],
            -item["conversation_length"],
            item["created_at"],
            item["tweet_id"],
        ),
    )
    return ranked[:limit]


def assign_bucket(matches, primary, word_count, is_non_support):
    if not matches:
        return "unclassified"
    if len(matches) > 1:
        return "multi_intent"
    if word_count <= 3 or is_non_support:
        return "ambiguous"
    return "primary_intent"


def allocate_quota(intent_counts, total_target):
    total = sum(intent_counts.values())
    if total == 0:
        return {}
    raw = {}
    for intent_id, count in intent_counts.items():
        raw[intent_id] = (count / total) * total_target
    quotas = {intent_id: max(0, int(raw[intent_id])) for intent_id in intent_counts}
    remaining = total_target - sum(quotas.values())
    order = sorted(intent_counts, key=lambda intent_id: (raw[intent_id] - quotas[intent_id], -intent_counts[intent_id], intent_id), reverse=True)
    for intent_id in order[:remaining]:
        quotas[intent_id] += 1
    return quotas


def validate_selection(selected, target_total):
    counts = Counter(item["bucket"] for item in selected)
    assert counts.get("primary_intent", 0) + counts.get("unclassified", 0) + counts.get("multi_intent", 0) + counts.get("ambiguous", 0) == target_total, (
        "Selection total mismatch: "
        f"primary={counts.get('primary_intent',0)} unclassified={counts.get('unclassified',0)} multi={counts.get('multi_intent',0)} ambiguous={counts.get('ambiguous',0)} total={sum(counts.values())} target={target_total}"
    )
    assert counts.get("unclassified", 0) == 60, f"Unclassified count mismatch {counts.get('unclassified',0)}"
    assert counts.get("multi_intent", 0) == 80, f"Multi-intent count mismatch {counts.get('multi_intent',0)}"
    assert counts.get("ambiguous", 0) == 40, f"Ambiguous count mismatch {counts.get('ambiguous',0)}"
    assert counts.get("primary_intent", 0) == target_total - 180, f"Primary intent count mismatch {counts.get('primary_intent',0)}"
    return counts


def build_candidate_pool(source_jsonl: Path, output_jsonl: Path, report_path: Path, target_total: int = 700):
    records = []
    by_primary_intent = Counter()
    primary_intent = []
    multi_intent = []
    unclassified = []
    ambiguous = []
    total_customer_messages = 0

    with source_jsonl.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            conversation = json.loads(line)
            messages = conversation.get("messages", [])
            conversation_length = len(messages)
            for message in messages:
                if message.get("role") != "customer_message":
                    continue
                total_customer_messages += 1
                tweet_id = str(message.get("tweet_id") or "").strip()
                created_at = parse_timestamp(message.get("created_at"))
                text = str(message.get("text") or "")
                normalized = normalize(text)
                word_count = content_word_count(text)
                matches, primary = classify(text)
                is_short = word_count <= 3
                is_non_support = bool(NON_SUPPORT_RE.fullmatch(normalized))
                bucket = assign_bucket(matches, primary, word_count, is_non_support)

                record = {
                    "tweet_id": tweet_id,
                    "conversation_id": conversation.get("conversation_id"),
                    "author_id": message.get("author_id"),
                    "created_at": message.get("created_at"),
                    "created_at_utc": created_at.isoformat() if created_at else None,
                    "text": text,
                    "normalized_text": normalized,
                    "content_word_count": word_count,
                    "primary_intent": primary,
                    "matched_intent_ids": [match["intent_id"] for match in matches] if matches else [],
                    "evidence_by_intent": {match["intent_id"]: match["evidence_patterns"] for match in matches} if matches else {},
                    "evidence_strength": sum(len(match["evidence_patterns"]) for match in matches) if matches else 0,
                    "conversation_length": conversation_length,
                    "is_unclassified": bucket == "unclassified",
                    "is_multi_intent": bucket == "multi_intent",
                    "is_short": is_short,
                    "is_non_support_like": is_non_support,
                    "is_ambiguous": bucket == "ambiguous",
                    "bucket": bucket,
                }

                if bucket == "primary_intent":
                    by_primary_intent[primary] += 1
                    primary_intent.append(record)
                elif bucket == "multi_intent":
                    multi_intent.append(record)
                elif bucket == "ambiguous":
                    ambiguous.append(record)
                else:
                    unclassified.append(record)
                records.append(record)

    primary_intent_sorted = select_by_bucket(primary_intent, len(primary_intent))
    multi_intent_sorted = select_by_bucket(multi_intent, len(multi_intent))
    unclassified_sorted = select_by_bucket(unclassified, len(unclassified))
    ambiguous_sorted = select_by_bucket(ambiguous, len(ambiguous))

    target_special = {"unclassified": 60, "multi_intent": 80, "ambiguous": 40}
    target_primary_total = target_total - sum(target_special.values())
    quotas = allocate_quota(by_primary_intent, target_primary_total)

    selected = []
    quality_rejection_counts = Counter()
    replacement_examples = []
    replacement_counts_by_bucket = Counter()
    for bucket_name, bucket_data, bucket_target in [
        ("unclassified", unclassified_sorted, target_special["unclassified"]),
        ("multi_intent", multi_intent_sorted, target_special["multi_intent"]),
        ("ambiguous", ambiguous_sorted, target_special["ambiguous"]),
    ]:
        bucket_selected, rejection_counts, examples, bucket_replacements = quality_filter_select(bucket_data, bucket_target)
        selected.extend(bucket_selected)
        quality_rejection_counts.update(rejection_counts)
        replacement_examples.extend(examples)
        replacement_counts_by_bucket.update(bucket_replacements)

    for intent_id, quota in sorted(quotas.items()):
        bucket = [item for item in primary_intent_sorted if item["primary_intent"] == intent_id]
        intent_selected, rejection_counts, examples, intent_replacements = quality_filter_select(bucket, quota)
        selected.extend(intent_selected)
        quality_rejection_counts.update(rejection_counts)
        replacement_examples.extend(examples)
        replacement_counts_by_bucket.update(intent_replacements)

    if len(selected) != target_total:
        raise ValueError(f"Selection size mismatch after deterministic quota assignment: {len(selected)} != {target_total}")

    counts = validate_selection(selected, target_total)
    selected_intents = {item["primary_intent"] for item in selected if item["bucket"] == "primary_intent"}
    assert selected_intents == set(INTENT_INDEX), f"Primary intent coverage mismatch: {sorted(set(INTENT_INDEX) - selected_intents)}"

    candidate_dir = output_jsonl.parent
    candidate_dir.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("w", encoding="utf-8") as stream:
        for item in selected:
            stream.write(json.dumps({
                "candidate_id": f"cand_{item['tweet_id']}",
                "tweet_id": item["tweet_id"],
                "conversation_id": item["conversation_id"],
                "author_id": item["author_id"],
                "created_at_utc": item["created_at_utc"],
                "bucket": item["bucket"],
                "primary_intent": item["primary_intent"],
                "matched_intent_ids": item["matched_intent_ids"],
                "evidence_by_intent": item["evidence_by_intent"],
                "evidence_strength": item["evidence_strength"],
                "content_word_count": item["content_word_count"],
                "conversation_length": item["conversation_length"],
                "is_unclassified": item["is_unclassified"],
                "is_multi_intent": item["is_multi_intent"],
                "is_ambiguous": item["is_ambiguous"],
                "is_short": item["is_short"],
                "is_non_support_like": item["is_non_support_like"],
                "text": item["text"],
            }, ensure_ascii=False) + "\n")

    summary = {
        "phase": "3B",
        "target_candidate_count": target_total,
        "actual_candidate_count": len(selected),
        "source_conversations": str(source_jsonl),
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "selection_strategy": {
            "intent_allocation_method": "proportional allocation across the 15 discovered primary intents using Phase 3A counts as weights",
            "special_bucket_target": {"unclassified": 60, "multi_intent": 80, "ambiguous": 40},
            "quality_ranking": ["strongest evidence", "more content words", "longer conversations", "earlier timestamps"],
            "reproducibility": "Deterministic sort order and fixed quotas; no random sampling",
            "quality_filtering": [
                "Reject empty or non-informative records",
                "Reject low token-diversity and repeated-token noise",
                "Reject clear mojibake or Unicode-artifact patterns",
                "Reject exact duplicates and clearly redundant near-duplicates within each bucket",
                "Backfill rejected records from the same bucket or primary-intent quota",
            ],
        },
        "category_counts": {
            "primary_intent_examples": counts.get("primary_intent", 0),
            "unclassified_examples": counts.get("unclassified", 0),
            "multi_intent_examples": counts.get("multi_intent", 0),
            "ambiguous_examples": counts.get("ambiguous", 0),
        },
        "intent_counts": dict(sorted(Counter(item["primary_intent"] for item in selected if item["primary_intent"]).items())),
        "source_message_totals": {
            "total_customer_messages_analyzed": total_customer_messages,
            "total_primary_intent_messages": sum(by_primary_intent.values()),
            "total_unclassified_messages": len(unclassified),
            "total_multi_intent_messages": len(multi_intent),
            "total_ambiguous_messages": len(ambiguous),
        },
        "quality_filtering": {
            "rejection_counts": dict(sorted(quality_rejection_counts.items())),
            "replacement_count": sum(quality_rejection_counts.values()),
            "replacements_by_bucket": dict(sorted(replacement_counts_by_bucket.items())),
            "replacement_examples": replacement_examples[:10],
        },
        "output_files": {
            "candidate_pool": str(output_jsonl),
            "report": str(report_path),
        },
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join([
            "# Phase 3B: Candidate Pool for Human Labeling",
            "",
            "## Objective",
            "",
            "This candidate pool is built from real AppleSupport customer messages already prepared in Phase 2 and classified with the Phase 3A taxonomy.",
            "",
            "## Sampling strategy",
            "",
            "- Read the prepared AppleSupport conversation JSONL without reprocessing the full TWCS CSV.",
            "- Reuse the same phrase-based intent logic from Phase 3A to determine each message's matched intents and primary label.",
            "- Allocate the pool into fixed buckets: 520 primary-intent examples, 60 unclassified, 80 multi-intent, and 40 ambiguous.",
            "- Enforce the buckets as mutually exclusive labels to ensure the final sample matches the intended design.",
            "- Sort within each bucket by strongest evidence, content length, conversation length, and tweet id for reproducibility.",
            "- Apply deterministic quality filtering within each bucket: reject empty records, low-diversity/repeated-token noise, clear mojibake artifacts, exact duplicates, and clearly redundant near-duplicates.",
            "- Backfill every rejected candidate from the same bucket; primary-intent records are backfilled within their own intent quota to preserve all 15 intents.",
            "",
            "## Candidate counts",
            "",
            f"- Target candidate count: {target_total}",
            f"- Final candidate count: {len(selected)}",
            f"- Primary-intent examples: {summary['category_counts']['primary_intent_examples']}",
            f"- Unclassified examples: {summary['category_counts']['unclassified_examples']}",
            f"- Multi-intent examples: {summary['category_counts']['multi_intent_examples']}",
            f"- Ambiguous examples: {summary['category_counts']['ambiguous_examples']}",
            "",
            "## Quality filtering",
            "",
            f"- Rejected candidates considered for replacement: {summary['quality_filtering']['replacement_count']}",
            f"- Replacements applied: {summary['quality_filtering']['replacement_count']}",
            *[f"- Replacements in {bucket}: {count}" for bucket, count in summary["quality_filtering"]["replacements_by_bucket"].items()],
            *[f"- {reason}: {count}" for reason, count in summary["quality_filtering"]["rejection_counts"].items()],
            "",
            "## Intent coverage summary",
            "",
            *[f"- {INTENT_INDEX[intent_id]['name']}: {count}" for intent_id, count in sorted(summary["intent_counts"].items())],
            "",
            "## Files",
            "",
            f"- Candidate pool: {output_jsonl}",
            f"- Source conversations: {source_jsonl}",
            "",
            "## Notes",
            "",
            "- The pool is explicitly designed to support future human labeling and a smaller 150-250 example golden evaluation set.",
            "- The sampled messages remain grounded in real customer-to-brand interactions from the working AppleSupport dataset.",
            "- This Phase 3B output is reproducible from the script and should be re-generated if the source data or taxonomy changes.",
        ]),
        encoding="utf-8",
    )

    with (output_jsonl.parent / "candidate_pool_summary.json").open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2, ensure_ascii=False)
        stream.write("\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("conversations_jsonl", type=Path, help="Path to AppleSupport Phase 2 conversations JSONL")
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--target-total", type=int, default=700)
    args = parser.parse_args()

    source_path = args.conversations_jsonl.resolve()
    output_jsonl = (args.output_jsonl or source_path.parent.parent / "phase3" / "candidate_pool" / "candidate_pool.jsonl").resolve()
    report_path = (args.report or source_path.parent.parent / "phase3" / "reports" / "PHASE3B_CANDIDATE_POOL_REPORT.md").resolve()
    summary = build_candidate_pool(source_path, output_jsonl, report_path, target_total=args.target_total)
    print(json.dumps({
        "phase": "3B",
        "target_candidate_count": summary["target_candidate_count"],
        "actual_candidate_count": summary["actual_candidate_count"],
        "candidate_pool_path": str(output_jsonl),
        "report_path": str(report_path),
    }, indent=2))


if __name__ == "__main__":
    main()
