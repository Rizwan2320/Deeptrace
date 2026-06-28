"""
citation_scorer.py

Mechanical citation-validity scorer. Checks whether every citation marker
the model produced (e.g. [1] or [1, 3, 4, 5]) refers to a source that
actually exists in the provided source list.

This is a STRUCTURAL check only. It does NOT verify that the cited source
actually supports the claim next to it — that's semantic citation alignment,
a harder problem for a later week. This catches fabricated citation indices,
not fabricated claims with a real-looking citation attached.
"""

import re
from pydantic import BaseModel

# Matches [1] and also [1, 3, 4, 5] — the model groups multiple citations
# in a single bracket with comma separation. Confirmed from real output:
# "100°C [1, 3, 4, 5]" from the boiling point query.
CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


class CitationCheckResult(BaseModel):
    cited_indices: list[int]
    invalid_citations: list[int]
    out_of_range_count: int
    is_valid: bool


def extract_citation_indices(answer: str) -> list[int]:
    indices: set[int] = set()
    for match in CITATION_PATTERN.finditer(answer):
        for part in match.group(1).split(","):
            indices.add(int(part.strip()))
    return sorted(indices)


def check_citation_validity(answer: str, source_count: int) -> CitationCheckResult:
    cited = extract_citation_indices(answer)
    invalid = [n for n in cited if n < 1 or n > source_count]
    return CitationCheckResult(
        cited_indices=cited,
        invalid_citations=invalid,
        out_of_range_count=len(invalid),
        is_valid=len(invalid) == 0,
    )