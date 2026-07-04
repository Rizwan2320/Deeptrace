"""
claim_extractor.py

Splits a generated answer into (claim, cited_source_indices) pairs using
sentence splitting and regex citation extraction.

Option A — regex-based. Fast, free, deterministic. Known limitations:
- Misses claims that span multiple sentences
- Drops sentences with no citation (correct — uncited claims are handled
  separately by the coverage scorer, not here)
- Assumes citations appear inside or at the end of the sentence they
  support

When Option A demonstrably fails on real data, swap in llm_extractor.py
which implements the same extract_claims() signature.
"""

import re
from pydantic import BaseModel

CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class ClaimSourcePair(BaseModel):
    claim: str
    source_indices: list[int]


def _extract_indices(text: str) -> list[int]:
    indices: set[int] = set()
    for match in CITATION_PATTERN.finditer(text):
        for part in match.group(1).split(","):
            indices.add(int(part.strip()))
    return sorted(indices)


def _clean_claim(sentence: str) -> str:
    return CITATION_PATTERN.sub("", sentence).strip()


def extract_claims(answer: str, source_count: int) -> list[ClaimSourcePair]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if s.strip()]
    pairs: list[ClaimSourcePair] = []

    for sentence in sentences:
        indices = _extract_indices(sentence)
        valid_indices = [i for i in indices if 1 <= i <= source_count]

        if not valid_indices:
            continue  # uncited sentence — coverage scorer handles this

        claim = _clean_claim(sentence)
        if claim:
            pairs.append(ClaimSourcePair(claim=claim, source_indices=valid_indices))

    return pairs