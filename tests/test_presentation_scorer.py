"""
Unit tests for presentation_scorer.py's validation logic only.
No API calls — these test the Pydantic model directly, not judge_presentation().
Judge quality itself is checked separately (scripts/check_presentation_scorer.py
now, formal κ calibration in Day 5).
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from pydantic import ValidationError

from evals.presentation_scorer import PresentationJudgment, JudgeStatus


def make_scored(clarity=3, organisation=3, fluency=3):
    return PresentationJudgment(
        status=JudgeStatus.SCORED,
        clarity_score=clarity,
        clarity_reasoning="test",
        organisation_score=organisation,
        organisation_reasoning="test",
        fluency_score=fluency,
        fluency_reasoning="test",
    )


class TestScoreClamping:
    def test_above_range_clamps_to_5(self):
        result = make_scored(clarity=7)
        assert result.clarity_score == 5

    def test_below_range_clamps_to_1(self):
        result = make_scored(organisation=0)
        assert result.organisation_score == 1

    def test_negative_clamps_to_1(self):
        result = make_scored(fluency=-3)
        assert result.fluency_score == 1

    def test_in_range_value_unchanged(self):
        result = make_scored(clarity=3)
        assert result.clarity_score == 3

    def test_boundary_low_unchanged(self):
        result = make_scored(clarity=1)
        assert result.clarity_score == 1

    def test_boundary_high_unchanged(self):
        result = make_scored(clarity=5)
        assert result.clarity_score == 5


class TestStatusInvariant:
    def test_scored_with_all_dimensions_succeeds(self):
        result = make_scored()
        assert result.status == JudgeStatus.SCORED

    def test_scored_missing_one_dimension_raises(self):
        with pytest.raises(ValidationError, match="organisation_score"):
            PresentationJudgment(
                status=JudgeStatus.SCORED,
                clarity_score=3,
                clarity_reasoning="test",
                fluency_score=3,
                fluency_reasoning="test",
            )

    def test_scored_missing_all_dimensions_raises(self):
        with pytest.raises(ValidationError):
            PresentationJudgment(status=JudgeStatus.SCORED)

    def test_judge_error_without_scores_succeeds(self):
        result = PresentationJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail="Parse failed: test",
        )
        assert result.status == JudgeStatus.JUDGE_ERROR
        assert result.clarity_score is None