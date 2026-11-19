"""Copy/plagiarism detection: TF-IDF over char n-grams of normalized added code."""
from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_THRESHOLD = 0.85

_COMMENT_RE = re.compile(r"(#.*$|//.*$)", re.M)
_STRING_RE = re.compile(r"""(".*?"|'.*?')""")
_IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_KEYWORDS = set(
    "def class return if else elif for while in import from as try except finally with lambda None True False "
    "and or not is pass break continue raise yield async await function const let var new this null undefined "
    "export default require module throw catch switch case self".split()
)


def normalize_code(code: str) -> str:
    """Strip comments, collapse strings and rename identifiers so renaming a variable doesn't evade detection."""
    code = _COMMENT_RE.sub("", code)
    code = _STRING_RE.sub('"S"', code)
    code = _IDENT_RE.sub(lambda m: m.group(0) if m.group(0) in _KEYWORDS else "ID", code)
    return re.sub(r"\s+", " ", code).strip()


@dataclass
class SimilarityMatch:
    other_id: str
    score: float


def find_similar(code: str, store: dict[str, str], threshold: float = DEFAULT_THRESHOLD,
                 min_chars: int = 80) -> list[SimilarityMatch]:
    """store: {submission_id: added_code}. Returns matches >= threshold, best first."""
    norm = normalize_code(code)
    if len(norm) < min_chars or not store:
        return []
    ids = list(store)
    docs = [normalize_code(store[i]) for i in ids]
    keep = [(i, d) for i, d in zip(ids, docs) if len(d) >= min_chars]
    if not keep:
        return []
    vec = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), sublinear_tf=True)
    try:
        mat = vec.fit_transform([d for _, d in keep] + [norm])
    except ValueError:
        return []
    sims = cosine_similarity(mat[-1], mat[:-1])[0]
    res = [SimilarityMatch(i, float(s)) for (i, _), s in zip(keep, sims) if s >= threshold]
    return sorted(res, key=lambda m: -m.score)
