#!/usr/bin/env python3
"""Build a retrieval corpus from the locked Phase 2 AppleSupport conversations."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PHASE3_SCRIPT_DIR = SCRIPT_DIR.parent.parent / "phase3" / "scripts"
sys.path.insert(0, str(PHASE3_SCRIPT_DIR))
from build_candidate_pool import classify  # noqa: E402

DEFAULT_SOURCE = Path("outputs/phase2/data/applesupport_conversations.jsonl")
DEFAULT_OUTPUT = Path("outputs/phase4/retrieval/retrieval_corpus.jsonl")


def build(source_path: Path, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_count = 0
    response_count = 0
    with source_path.open("r", encoding="utf-8") as source, output_path.open("w", encoding="utf-8") as output:
        for line in source:
            if not line.strip():
                continue
            conversation = json.loads(line)
            messages = conversation.get("messages", [])
            for index, message in enumerate(messages):
                if message.get("role") != "customer_message":
                    continue
                customer_id = str(message.get("tweet_id") or "")
                customer_text = str(message.get("text") or "")
                matches, primary = classify(customer_text)
                response = None
                response_id = None
                response_created_at = None
                if index + 1 < len(messages) and messages[index + 1].get("role") == "brand_response":
                    response_message = messages[index + 1]
                    response = str(response_message.get("text") or "")
                    response_id = str(response_message.get("tweet_id") or "")
                    response_created_at = response_message.get("created_at")
                    response_count += 1
                record = {
                    "corpus_id": f"hist_{customer_id}",
                    "conversation_id": conversation.get("conversation_id"),
                    "customer_message_id": customer_id,
                    "customer_text": customer_text,
                    "customer_created_at": message.get("created_at"),
                    "customer_created_at_utc": message.get("created_at_utc"),
                    "author_id": message.get("author_id"),
                    "historical_response": response,
                    "historical_response_id": response_id,
                    "historical_response_created_at": response_created_at,
                    "conversation_length": len(messages),
                    "corpus_intent_ids": [match["intent_id"] for match in matches],
                    "corpus_primary_intent": primary,
                    "intent_metadata_source": "Phase3A_lexical_heuristic",
                    "source_file": str(source_path),
                }
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                corpus_count += 1
    return {
        "corpus_records": corpus_count,
        "records_with_immediate_historical_response": response_count,
        "source_file": str(source_path),
        "output_file": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), indent=2))


if __name__ == "__main__":
    main()
