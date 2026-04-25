"""Algorithmic A vs B matching for claim-like records.

Pure-stdlib (no embeddings) Jaccard token overlap with greedy bipartite assignment.
Determinism: the matcher is a pure function of its inputs and never calls an LLM,
so unit tests can lock in behaviour without API access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal, Protocol

_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_STOP = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "were",
        "with",
        "this",
        "these",
        "those",
        "we",
        "our",
        "their",
        "they",
        "than",
        "then",
        "but",
        "not",
        "no",
        "more",
        "less",
        "most",
        "very",
        "such",
        "all",
        "any",
        "can",
        "may",
        "also",
        "well",
        "into",
        "while",
        "where",
        "when",
        "which",
        "who",
        "whose",
        "whom",
        "what",
    }
)


def tokenize(text: str) -> set[str]:
    """Lowercase alphanumeric tokens minus a small English stopword list."""

    return {tok.lower() for tok in _WORD_RE.findall(text or "") if tok.lower() not in _STOP}


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    """Standard Jaccard similarity for two token sets (0.0 on empty either side)."""

    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def char_ngrams(text: str, n: int = 4) -> set[str]:
    """Lower-cased character n-grams over a-z0-9 + single space (for paraphrase matching)."""

    norm = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    if len(norm) < n:
        return {norm} if norm else set()
    return {norm[i : i + n] for i in range(len(norm) - n + 1)}


def char_jaccard(a: str, b: str, *, n: int = 4) -> float:
    """Jaccard over character n-grams; tolerant to morphology and minor reordering."""

    return jaccard(char_ngrams(a, n=n), char_ngrams(b, n=n))


def char_overlap_coefficient(a: str, b: str, *, n: int = 4) -> float:
    """Szymkiewicz–Simpson overlap on char n-grams: |A∩B| / min(|A|,|B|).

    Robust to length asymmetry — a short B that "fits inside" a long A scores high.
    Useful when the LLM produces a terser paraphrase of a verbose gold claim.
    """

    sa, sb = char_ngrams(a, n=n), char_ngrams(b, n=n)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def combined_score(text_a: str, text_b: str) -> float:
    """Best of token-Jaccard and char-4gram overlap coefficient.

    Token Jaccard is precise but brittle on heavy paraphrases; char-4gram overlap
    coefficient catches morphological variants ("normalization" vs "norm") and is
    robust to one side being much shorter. The pair max is a cheap proxy for semantic
    similarity without dragging in embedding dependencies.
    """

    return max(
        jaccard(tokenize(text_a), tokenize(text_b)),
        char_overlap_coefficient(text_a, text_b, n=4),
    )


@dataclass(frozen=True)
class Record:
    """One side of a comparison — A is gold, B is the LLM-generated draft."""

    record_id: str
    text: str
    fields: dict[str, str]


@dataclass(frozen=True)
class Pair:
    """A successful match between one A record and one B record."""

    a_id: str
    b_id: str
    score: float
    field_disagreements: list[dict[str, str]]
    score_source: str = "lexical"  # "lexical" | "embedding"


class EmbeddingScorerProtocol(Protocol):
    """Pluggable embedding-based scorer for cascade matching.

    Implementations should return cosine similarity in [0.0, 1.0] and ideally
    cache embeddings between calls so the matcher can ask in any order without
    paying the network cost twice.
    """

    def score(self, text_a: str, text_b: str) -> float: ...


@dataclass(frozen=True)
class MatchResult:
    """Greedy-bipartite match output."""

    pairs: list[Pair]
    unmatched_a: list[str]
    unmatched_b: list[str]


ScoringStrategy = Literal["token", "combined"]


def _score_pair(text_a: str, text_b: str, scoring: ScoringStrategy) -> float:
    if scoring == "token":
        return jaccard(tokenize(text_a), tokenize(text_b))
    return combined_score(text_a, text_b)


def match_records(
    a: list[Record],
    b: list[Record],
    *,
    min_score: float = 0.35,
    compared_fields: tuple[str, ...] = ("polarity", "claim_type"),
    scoring: ScoringStrategy = "combined",
    embedding_scorer: EmbeddingScorerProtocol | None = None,
    embedding_min_score: float = 0.75,
    lexical_accept_threshold: float = 0.50,
) -> MatchResult:
    """Greedy bipartite matching; ties broken by lower index.

    Three-stage cascade:

    1. **Lexical** — token Jaccard + (with ``scoring="combined"``) char-4gram overlap.
       If the lexical score is ``>= lexical_accept_threshold`` we accept immediately
       — no embedding call needed.
    2. **Embedding (optional)** — if ``embedding_scorer`` is provided, recompute the
       score for low-lexical pairs as ``max(lexical, embedding_cosine)``. Pairs accepted
       only via embedding are flagged ``score_source="embedding"`` in the report.
    3. **Greedy bipartite assignment** by descending score; lower index breaks ties.

    Defaults: ``min_score=0.35`` (lexical floor), ``embedding_min_score=0.75``
    (cosine floor), ``lexical_accept_threshold=0.50``. Tuned on the Phase 6.B PoC:
    boosts recall ~50%→~85% on heavily paraphrased pairs without measurable false
    positives in spot-check.
    """

    scored: list[tuple[float, str, int, int]] = []
    for ai, ar in enumerate(a):
        for bi, br in enumerate(b):
            lex = _score_pair(ar.text, br.text, scoring)
            source = "lexical"
            sc = lex
            # Cascade: only consult embeddings when lexical can't decide on its own.
            # Embeddings *promote* a pair only if they clear their own threshold —
            # otherwise we fall back to the lexical score so that a barely-lexical
            # match (e.g. 0.40) is not destroyed by a slightly-higher-but-still-noisy
            # embedding score (e.g. 0.65).
            if embedding_scorer is not None and lex < lexical_accept_threshold:
                emb = embedding_scorer.score(ar.text, br.text)
                if emb >= embedding_min_score and emb > lex:
                    sc = emb
                    source = "embedding"
            if sc >= min_score:
                scored.append((sc, source, ai, bi))

    scored.sort(key=lambda t: (-t[0], t[2], t[3]))
    used_a: set[int] = set()
    used_b: set[int] = set()
    pairs: list[Pair] = []
    for sc, source, ai, bi in scored:
        if ai in used_a or bi in used_b:
            continue
        used_a.add(ai)
        used_b.add(bi)
        ar = a[ai]
        br = b[bi]
        disagreements = [
            {"field": f, "a": ar.fields.get(f, ""), "b": br.fields.get(f, "")}
            for f in compared_fields
            if (ar.fields.get(f, "") or "") != (br.fields.get(f, "") or "")
        ]
        pairs.append(
            Pair(
                a_id=ar.record_id,
                b_id=br.record_id,
                score=round(sc, 3),
                field_disagreements=disagreements,
                score_source=source,
            )
        )
    pairs.sort(key=lambda p: p.a_id)
    unmatched_a = sorted(a[i].record_id for i in range(len(a)) if i not in used_a)
    unmatched_b = sorted(b[i].record_id for i in range(len(b)) if i not in used_b)
    return MatchResult(pairs=pairs, unmatched_a=unmatched_a, unmatched_b=unmatched_b)


def classify_spot_check_priority(result: MatchResult, *, a_total: int) -> tuple[str, str]:
    """Rank human spot-check urgency from the diff plus its rationale string."""

    polarity_flips = sum(
        1 for p in result.pairs for d in p.field_disagreements if d["field"] == "polarity"
    )
    type_flips = sum(
        1 for p in result.pairs for d in p.field_disagreements if d["field"] == "claim_type"
    )
    unmatched_a_ratio = len(result.unmatched_a) / a_total if a_total else 0.0

    if polarity_flips >= 1 or unmatched_a_ratio >= 0.30:
        priority = "high"
        why = (
            f"polarity_flips={polarity_flips}, unmatched_a_ratio={unmatched_a_ratio:.2f}"
            f" (gate: polarity_flips ≥ 1 OR unmatched_a_ratio ≥ 0.30)"
        )
    elif type_flips >= 1 or len(result.unmatched_a) >= 1:
        priority = "medium"
        why = (
            f"type_flips={type_flips}, unmatched_a={len(result.unmatched_a)}"
            f" (gate: type_flips ≥ 1 OR unmatched_a ≥ 1)"
        )
    else:
        priority = "low"
        why = "no polarity_flips, no type_flips, no unmatched_a"
    return priority, why
