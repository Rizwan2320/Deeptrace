"""
source_quality_scorer.py

Orchestrates the Source Quality vertical: combines structural citation
validity (citation_scorer) with semantic faithfulness (claim_extractor +
hallucination_scorer) into one SourceQualityScore per answer.

These two numbers are NEVER averaged into one score. They measure different
failure modes — structural asks "does this citation index exist", semantic
asks "does the cited source actually support the claim". Collapsing them
would hide which layer (generation formatting vs. generation grounding)
needs fixing when a score drops.

Multi-source claims (e.g. "[1, 3, 4, 5]") use best-of scoring: a claim is
SUPPORTED if at least one cited source supports it. This is a documented,
generous interpretation — see LEARNINGS.md for the reasoning.
"""

import logging
from pydantic import BaseModel

from evals.citation_scorer import check_citation_validity, CitationCheckResult
from evals.claim_extractor import extract_claims, ClaimSourcePair
from evals.hallucination_scorer import judge_claim, ClaimVerdict, ClaimJudgment
from src.search.models import SearchResult

logger = logging.getLogger(__name__)


class ClaimResult(BaseModel):
    claim: str
    source_indices: list[int]
    verdict: ClaimVerdict
    reasoning: str


class SourceQualityScore(BaseModel):
    query: str
    citation_validity: CitationCheckResult
    claim_results: list[ClaimResult]
    faithfulness_rate: float
    judge_error_rate: float
    total_claims: int


def _resolve_claim_verdict(claim: str, source_indices: list[int], results: list[SearchResult]) -> ClaimJudgment:
    """Best-of scoring across all cited sources for one claim."""
    judgments: list[ClaimJudgment] = []

    for idx in source_indices:
        source_text = results[idx - 1].content  # 1-indexed citations
        judgment = judge_claim(claim, source_text)
        judgments.append(judgment)

        if judgment.verdict == ClaimVerdict.SUPPORTED:
            return judgment  # best-of short-circuit — one support is enough

    # No source supported it — prefer a JUDGE_ERROR signal over silently
    # picking UNSUPPORTED if any judge call failed to parse
    if any(j.verdict == ClaimVerdict.JUDGE_ERROR for j in judgments):
        return next(j for j in judgments if j.verdict == ClaimVerdict.JUDGE_ERROR)

    # All judged, none supported — prefer UNSUPPORTED over INSUFFICIENT_EVIDENCE
    # if any single source directly contradicted the claim
    if any(j.verdict == ClaimVerdict.UNSUPPORTED for j in judgments):
        return next(j for j in judgments if j.verdict == ClaimVerdict.UNSUPPORTED)

    return judgments[0]  # all insufficient_evidence


def score_source_quality(query: str, answer: str, results: list[SearchResult]) -> SourceQualityScore:
    citation_validity = check_citation_validity(answer, source_count=len(results))

    claim_pairs: list[ClaimSourcePair] = extract_claims(answer, source_count=len(results))
    claim_results: list[ClaimResult] = []

    for pair in claim_pairs:
        # Skip source indices the citation scorer already flagged invalid —
        # no point asking the judge about a source that doesn't exist
        valid_indices = [i for i in pair.source_indices if 1 <= i <= len(results)]
        if not valid_indices:
            continue

        judgment = _resolve_claim_verdict(pair.claim, valid_indices, results)
        claim_results.append(ClaimResult(
            claim=pair.claim,
            source_indices=valid_indices,
            verdict=judgment.verdict,
            reasoning=judgment.reasoning,
        ))

    total = len(claim_results)
    supported = sum(1 for c in claim_results if c.verdict == ClaimVerdict.SUPPORTED)
    judge_errors = sum(1 for c in claim_results if c.verdict == ClaimVerdict.JUDGE_ERROR)

    faithfulness_rate = round(supported / total, 4) if total > 0 else 0.0
    judge_error_rate = round(judge_errors / total, 4) if total > 0 else 0.0

    if judge_error_rate > 0.15:
        logger.warning({
            "event": "high_judge_error_rate",
            "query": query,
            "judge_error_rate": judge_error_rate,
            "message": "Judge error rate exceeds 15% - treat faithfulness_rate for this answer with caution",
        })

    return SourceQualityScore(
        query=query,
        citation_validity=citation_validity,
        claim_results=claim_results,
        faithfulness_rate=faithfulness_rate,
        judge_error_rate=judge_error_rate,
        total_claims=total,
    )