import json
import re
from collections import Counter, defaultdict
from pathlib import Path

POOL = Path("outputs/phase3/candidate_pool/candidate_pool.jsonl")
SUMMARY = Path("outputs/phase3/candidate_pool/candidate_pool_summary.json")
rows = [json.loads(line) for line in POOL.read_text(encoding="utf-8").splitlines() if line.strip()]
summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
markers = set("ï¿¸âÃÂãðÐþÞýÝ")
stop = {"the","a","an","and","or","but","if","then","when","while","for","with","without","this","that","these","those","from","into","onto","over","under","about","after","before","between","through","during","because","please","help","my","your","our","i","me","you","we","they","them","is","are","was","were","be","been","being","to","of","in","on","at","it","its","as","so","not","no","yes","can","could","would","should","have","has","had","do","does","did","im","apple","support","thanks","thank","hi","hello","issue","problem","fix","bug","app","apps","phone","iphone","ipad","watch","just","very","really","too","also","still","again","out","up","down","all","any","some","few","many","more","most","ever"}

def norm(text):
    text = (text or "").replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()

def tokens(text):
    return re.findall(r"[a-z0-9]+", norm(text).lower())

def canonical(text):
    text = norm(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+|#\w+", " ", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text)).strip()

def content(text):
    return {token for token in canonical(text).split() if len(token) > 2 and token not in stop}

def mojibake(text):
    text = norm(text)
    if len(re.findall(r"I[\ufe0e\ufe0f]", text)) >= 4:
        return True
    for token in re.findall(r"\S+", text):
        if len(token) > 24 or not any(char in markers for char in token):
            continue
        if re.search(r"(?:ï¿|ï¸|Ã¢|Ã©|Ã±|Ã¼|Â\s|â€™|ðŸ)", token, re.I):
            return True
        if re.search(r"[a-z0-9][ï¿¸âÃÂãðÐþÞýÝ]{2,}|[ï¿¸âÃÂãðÐþÞýÝ]{2,}[a-z0-9]", token, re.I):
            return True
    return False

low = set()
artifact = set()
empty = set()
meaningful = set()
for i, row in enumerate(rows):
    text = norm(row.get("text", ""))
    toks = tokens(text)
    if not text or not toks:
        empty.add(i)
    if toks and len(set(toks)) / len(toks) < 0.2:
        low.add(i)
    if mojibake(text):
        artifact.add(i)
    if len(toks) >= 4 and len(set(toks)) / len(toks) >= 0.3 and re.search(r"[A-Za-z]", text):
        meaningful.add(i)

by_canon = defaultdict(list)
for i, row in enumerate(rows):
    value = canonical(row.get("text", ""))
    if value:
        by_canon[value].append(i)
exact_groups = {key: value for key, value in by_canon.items() if len(value) > 1}
exact_indices = {i for group in exact_groups.values() for i in group}
near_pairs = []
for i in range(len(rows)):
    if i in exact_indices:
        continue
    left = content(rows[i].get("text", ""))
    if len(left) < 6:
        continue
    for j in range(i + 1, len(rows)):
        if j in exact_indices:
            continue
        right = content(rows[j].get("text", ""))
        if len(right) < 6:
            continue
        overlap = len(left & right)
        if overlap >= 4 and overlap / min(len(left), len(right)) >= 0.7 and len(left | right) >= 6:
            near_pairs.append((i, j))

print("total_rows", len(rows))
print("bucket_counts", dict(Counter(row["bucket"] for row in rows)))
print("intent_counts", dict(sorted(Counter(row["primary_intent"] for row in rows if row["primary_intent"]).items())))
print("low_diversity_count", len(low))
print("exact_duplicate_count", sum(len(group) for group in exact_groups.values()))
print("near_duplicate_count", len(near_pairs))
print("mojibake_count", len(artifact))
print("empty_non_informative_count", len(empty))
print("meaningful_count", len(meaningful))
print("replacements_by_bucket", summary["quality_filtering"].get("replacements_by_bucket", {}))
print("rejection_counts", summary["quality_filtering"]["rejection_counts"])
print("--- 10 rejected_to_replacement_examples ---")
for example in summary["quality_filtering"]["replacement_examples"][:10]:
    print(json.dumps(example, ensure_ascii=False))
