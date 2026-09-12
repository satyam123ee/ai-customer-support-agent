#!/usr/bin/env python3
"""Deterministic sparse TF-IDF lexical retrieval over the Phase 4 corpus."""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_CORPUS = Path("outputs/phase4/retrieval/retrieval_corpus.jsonl")
DEFAULT_GOLDEN = Path("outputs/phase3/golden_set/golden_evaluation_set_annotated.jsonl")
DEFAULT_OUTPUT = Path("outputs/phase4/retrieval/retrieval_results.jsonl")
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


def tokenize(text: str) -> list[str]:
    value = MENTION_URL_RE.sub(" ", text or "").lower()
    return [token for token in TOKEN_RE.findall(value) if len(token) > 2 and token not in STOP_WORDS]


class TfidfIndex:
    def __init__(self, records: list[dict]):
        self.records = records
        self.document_count = len(records)
        self.postings: dict[str, dict[int, int]] = defaultdict(dict)
        self.idf: dict[str, float] = {}
        self.document_norms: list[float] = [0.0] * self.document_count
        document_frequencies = Counter()
        document_term_counts = []
        for index, record in enumerate(records):
            counts = Counter(tokenize(record["customer_text"]))
            document_term_counts.append(counts)
            for token, count in counts.items():
                document_frequencies[token] += 1
                self.postings[token][index] = count
        for token, frequency in document_frequencies.items():
            self.idf[token] = math.log((self.document_count + 1) / (frequency + 1)) + 1.0
        for index, counts in enumerate(document_term_counts):
            self.document_norms[index] = math.sqrt(sum((count * self.idf[token]) ** 2 for token, count in counts.items()))

    def search(self, query: str, top_k: int, exclude_message_id: str | None = None, exclude_conversation_id: str | None = None) -> list[tuple[dict, float]]:
        query_counts = Counter(tokenize(query))
        query_weights = {
            token: count * self.idf[token]
            for token, count in query_counts.items()
            if token in self.idf
        }
        query_norm = math.sqrt(sum(weight ** 2 for weight in query_weights.values()))
        if query_norm == 0.0:
            return []
        dot_products = defaultdict(float)
        for token, query_weight in query_weights.items():
            for index, count in self.postings[token].items():
                record = self.records[index]
                if exclude_message_id and str(record["customer_message_id"]) == str(exclude_message_id):
                    continue
                if exclude_conversation_id and record.get("conversation_id") == exclude_conversation_id:
                    continue
                dot_products[index] += query_weight * count * self.idf[token]
        scored = []
        for index, dot_product in dot_products.items():
            denominator = query_norm * self.document_norms[index]
            if denominator == 0.0:
                continue
            scored.append((self.records[index], dot_product / denominator))
        scored.sort(key=lambda item: (-item[1], str(item[0]["customer_message_id"])))
        return scored[:top_k]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def retrieve(corpus_path: Path, golden_path: Path, output_path: Path, top_k: int = 5) -> dict:
    if top_k < 1:
        raise ValueError("top_k must be positive")
    corpus = load_jsonl(corpus_path)
    golden = load_jsonl(golden_path)
    index = TfidfIndex(corpus)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    failure_count = 0
    result_count = 0
    with output_path.open("w", encoding="utf-8") as output:
        for golden_record in golden:
            evaluation = golden_record.get("evaluation", {})
            eligible = evaluation.get("gold_intent") is not None
            results = index.search(
                golden_record.get("text", ""),
                top_k,
                exclude_message_id=golden_record.get("message_id"),
                exclude_conversation_id=golden_record.get("conversation_id"),
            )
            if not results:
                failure_count += 1
                output.write(json.dumps({
                    "golden_id": golden_record["golden_id"],
                    "query": golden_record.get("text"),
                    "gold_intent": evaluation.get("gold_intent"),
                    "evaluation_eligible": eligible,
                    "retrieval_failed": True,
                    "top_k_configured": top_k,
                    "retrieved_rank": None,
                    "retrieved_conversation_id": None,
                    "retrieved_message_id": None,
                    "retrieved_customer_text": None,
                    "retrieved_historical_response": None,
                    "retrieved_intent_ids": [],
                    "retrieved_primary_intent": None,
                    "similarity_score": None,
                }, ensure_ascii=False) + "\n")
                result_count += 1
                continue
            for rank, (record, score) in enumerate(results, start=1):
                output.write(json.dumps({
                    "golden_id": golden_record["golden_id"],
                    "query": golden_record.get("text"),
                    "gold_intent": evaluation.get("gold_intent"),
                    "evaluation_eligible": eligible,
                    "retrieval_failed": False,
                    "top_k_configured": top_k,
                    "retrieved_rank": rank,
                    "retrieved_conversation_id": record.get("conversation_id"),
                    "retrieved_message_id": record.get("customer_message_id"),
                    "retrieved_customer_text": record.get("customer_text"),
                    "retrieved_historical_response": record.get("historical_response"),
                    "retrieved_intent_ids": record.get("corpus_intent_ids", []),
                    "retrieved_primary_intent": record.get("corpus_primary_intent"),
                    "similarity_score": score,
                }, ensure_ascii=False) + "\n")
                result_count += 1
    return {
        "golden_queries": len(golden),
        "retrieval_result_rows": result_count,
        "retrieval_failures": failure_count,
        "top_k": top_k,
        "corpus_records": len(corpus),
        "same_message_and_conversation_excluded": True,
        "retrieval_method": "standard-library sparse TF-IDF cosine similarity",
        "output_file": str(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(retrieve(args.corpus, args.golden, args.output, args.top_k), indent=2))


if __name__ == "__main__":
    main()
