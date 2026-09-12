import json
import re
from collections import defaultdict
from pathlib import Path

DATA_PATH = Path(r"C:\Users\DELL\Documents\Codex\2026-09-12\excellent-the-new-dataset-is-much\outputs\phase3\candidate_pool\candidate_pool.jsonl")
rows = [json.loads(line) for line in DATA_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

MOJIBAKE_CHARS = set("ï¿¸âÃÂãðÐþÞýÝ")
STOP_WORDS = {
    'the','a','an','and','or','but','if','then','when','while','for','with','without','this','that','these','those',
    'from','into','onto','over','under','about','after','before','between','through','during','because','please','help',
    'my','your','our','i','me','you','we','they','them','is','are','was','were','be','been','being','to','of','in','on','at',
    'it','its','itself','as','so','not','no','yes','can','could','would','should','have','has','had','do','does','did','im',
    'apple','support','thanks','thank','hi','hello','issue','problem','fix','bug','app','apps','phone','iphone','ipad','watch',
    'just','very','really','too','also','still','again','out','up','down','all','any','some','few','many','more','most','ever'
}

def norm(s):
    s = (s or "").replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def tokenize_ascii(s):
    return re.findall(r"[A-Za-z0-9]+", (s or "").lower())

def unique_ratio(s):
    toks = tokenize_ascii(s)
    return len(set(toks)) / len(toks) if toks else 0.0

def is_probable_mojibake_token(tok):
    tok = tok.strip()
    if not tok or len(tok) > 24:
        return False
    # Very conservative: flag only short tokens that mix mojibake markers with ASCII letters/digits.
    if not any(ch in MOJIBAKE_CHARS for ch in tok):
        return False
    if any(ch in tok for ch in "¿¸"):
        if re.search(r"[A-Za-z0-9].*[ï¿¸âÃÂãðÐþÞýÝ]|[ï¿¸âÃÂãðÐþÞýÝ].*[A-Za-z0-9]", tok):
            return True
    if re.search(r"(?:ï¿|ï¸|Ã¢|Ã©|Ã±|Ã¼|Â\s|â€™|ðŸ)", tok, flags=re.I):
        return True
    # Mixed marker + ASCII near the start/end of a short token is suspicious.
    if re.search(r"[A-Za-z0-9][ï¿¸âÃÂãðÐþÞýÝ]{2,}[A-Za-z0-9]|[ï¿¸âÃÂãðÐþÞýÝ]{2,}[A-Za-z0-9]|[A-Za-z0-9][ï¿¸âÃÂãðÐþÞýÝ][A-Za-z0-9]", tok):
        return True
    return False

def detect_mojibake(text):
    text = norm(text)
    if not text:
        return False
    # Legitimate multilingual text is not rejected just because it contains non-ASCII letters.
    # We look specifically for mojibake-style marker runs mixed with ASCII and punctuation.
    for tok in re.findall(r"\S+", text):
        if is_probable_mojibake_token(tok):
            return True
    return False

def canonical_for_duplicate(text):
    text = norm(text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"@\w+|#\w+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def content_tokens(text):
    canon = canonical_for_duplicate(text)
    toks = [t for t in canon.split() if len(t) > 2 and t not in STOP_WORDS]
    return toks

def exact_duplicate_groups(rows):
    by_canon = defaultdict(list)
    for idx, row in enumerate(rows):
        canon = canonical_for_duplicate(row["text"])
        if canon:
            by_canon[canon].append(idx)
    return {k: v for k, v in by_canon.items() if len(v) > 1}

def near_duplicate_pairs(rows, exact_groups):
    exact_idx = {idx for v in exact_groups.values() for idx in v}
    pairs = []
    for i in range(len(rows)):
        if i in exact_idx:
            continue
        ai = content_tokens(rows[i]["text"])
        if len(ai) < 6:
            continue
        set_i = set(ai)
        for j in range(i + 1, len(rows)):
            if j in exact_idx:
                continue
            bj = content_tokens(rows[j]["text"])
            if len(bj) < 6:
                continue
            set_j = set(bj)
            overlap = len(set_i & set_j)
            if overlap < 4:
                continue
            # Conservative: reject only repeated-question duplicates with substantial shared content.
            if overlap / min(len(set_i), len(set_j)) >= 0.7 and len(set_i | set_j) >= 6:
                pairs.append((i, j, overlap))
    return pairs

mojibake = set()
low_diversity = set()
empty = set()
meaningful = set()
for i, row in enumerate(rows):
    text = norm(row["text"])
    toks = tokenize_ascii(text)
    if not text or not toks:
        empty.add(i)
    if detect_mojibake(text):
        mojibake.add(i)
    if toks and unique_ratio(text) < 0.2:
        low_diversity.add(i)
    if len(toks) >= 4 and unique_ratio(text) >= 0.3 and re.search(r"[A-Za-z]", text):
        meaningful.add(i)

exact_groups = exact_duplicate_groups(rows)
near_pairs = near_duplicate_pairs(rows, exact_groups)
print("total_rows", len(rows))
print("mojibake_artifacts", len(mojibake))
print("low_unique_diversity", len(low_diversity))
print("empty_noninformative", len(empty))
print("exact_duplicate_records", sum(len(v) for v in exact_groups.values()))
print("exact_duplicate_groups", len(exact_groups))
print("near_duplicate_pairs", len(near_pairs))
print("meaningful_candidates", len(meaningful))
print("--- mojibake examples ---")
for idx in sorted(mojibake)[:20]:
    print(idx, rows[idx]["bucket"], "::", rows[idx]["text"])
print("--- low_diversity examples ---")
for idx in sorted(low_diversity)[:20]:
    print(idx, rows[idx]["bucket"], "::", rows[idx]["text"])
print("--- exact duplicate examples ---")
for canon, idxs in list(exact_groups.items())[:5]:
    if len(idxs) < 2:
        continue
    print("canon:", canon)
    for idx in idxs[:3]:
        print(" ", idx, rows[idx]["text"])
    print("---")
print("--- near duplicate examples ---")
for i, j, overlap in near_pairs[:5]:
    print("pair", i, j, "overlap", overlap)
    print("A:", rows[i]["text"])
    print("B:", rows[j]["text"])
    print("---")
