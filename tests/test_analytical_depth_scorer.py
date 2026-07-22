"""
Unit tests for analytical_depth_scorer.py's validation logic only.
No API calls. Judge quality itself is checked in
scripts/check_analytical_depth_scorer.py, formal κ calibration in Day 5.
"""
"""
Unit tests for analytical_depth_scorer.py's validation logic only.
No API calls. Judge quality itself is checked in
scripts/check_analytical_depth_scorer.py, formal κ calibration in Day 5.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from pydantic import ValidationError

from evals.analytical_depth_scorer import AnalyticalDepthJudgment, JudgeStatus


def make_scored(reasoning=3, synthesis=3, conflict_present=False, conflict_score=None):
    return AnalyticalDepthJudgment(
        status=JudgeStatus.SCORED,
        reasoning_score=reasoning,
        reasoning_reasoning="test",
        synthesis_score=synthesis,
        synthesis_reasoning="test",
        conflict_present=conflict_present,
        conflict_resolution_score=conflict_score,
        conflict_resolution_reasoning="test" if conflict_score is not None else None,
    )


class TestScoreClamping:
    def test_reasoning_above_range_clamps(self):
        assert make_scored(reasoning=8).reasoning_score == 5

    def test_synthesis_below_range_clamps(self):
        assert make_scored(synthesis=-1).synthesis_score == 1

    def test_conflict_score_clamps_when_present(self):
        result = make_scored(conflict_present=True, conflict_score=99)
        assert result.conflict_resolution_score == 5


class TestStatusInvariant:
    def test_scored_missing_reasoning_raises(self):
        with pytest.raises(ValidationError, match="reasoning_score"):
            AnalyticalDepthJudgment(
                status=JudgeStatus.SCORED,
                synthesis_score=3,
                synthesis_reasoning="test",
                conflict_present=False,
            )

    def test_judge_error_without_any_fields_succeeds(self):
        result = AnalyticalDepthJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail="Parse failed: test",
        )
        assert result.reasoning_score is None


class TestConflictNullableInvariant:
    def test_no_conflict_with_null_score_succeeds(self):
        result = make_scored(conflict_present=False, conflict_score=None)
        assert result.conflict_present is False
        assert result.conflict_resolution_score is None

    def test_conflict_present_with_score_succeeds(self):
        result = make_scored(conflict_present=True, conflict_score=2)
        assert result.conflict_resolution_score == 2

    def test_conflict_present_missing_score_raises(self):
        with pytest.raises(ValidationError, match="conflict_present=True"):
            AnalyticalDepthJudgment(
                status=JudgeStatus.SCORED,
                reasoning_score=3,
                reasoning_reasoning="test",
                synthesis_score=3,
                synthesis_reasoning="test",
                conflict_present=True,
                conflict_resolution_score=None,
            )

    def test_no_conflict_but_score_set_raises(self):
        """The important negative case: a score should never leak in
        when there's nothing to resolve — same discipline as
        faithfulness_rate staying None instead of defaulting to 0.0."""
        with pytest.raises(ValidationError, match="conflict_present=False"):
            AnalyticalDepthJudgment(
                status=JudgeStatus.SCORED,
                reasoning_score=3,
                reasoning_reasoning="test",
                synthesis_score=3,
                synthesis_reasoning="test",
                conflict_present=False,
                conflict_resolution_score=4,
            )


def make_scored(reasoning=3, synthesis=3, conflict_present=False, conflict_score=None):
    return AnalyticalDepthJudgment(
        status=JudgeStatus.SCORED,
        reasoning_score=reasoning,
        reasoning_reasoning="test",
        synthesis_score=synthesis,
        synthesis_reasoning="test",
        conflict_present=conflict_present,
        conflict_resolution_score=conflict_score,
        conflict_resolution_reasoning="test" if conflict_score is not None else None,
    )


class TestScoreClamping:
    def test_reasoning_above_range_clamps(self):
        assert make_scored(reasoning=8).reasoning_score == 5

    def test_synthesis_below_range_clamps(self):
        assert make_scored(synthesis=-1).synthesis_score == 1

    def test_conflict_score_clamps_when_present(self):
        result = make_scored(conflict_present=True, conflict_score=99)
        assert result.conflict_resolution_score == 5


class TestStatusInvariant:
    def test_scored_missing_reasoning_raises(self):
        with pytest.raises(ValidationError, match="reasoning_score"):
            AnalyticalDepthJudgment(
                status=JudgeStatus.SCORED,
                synthesis_score=3,
                synthesis_reasoning="test",
                conflict_present=False,
            )

    def test_judge_error_without_any_fields_succeeds(self):
        result = AnalyticalDepthJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail="Parse failed: test",
        )
        assert result.reasoning_score is None


class TestConflictNullableInvariant:
    def test_no_conflict_with_null_score_succeeds(self):
        result = make_scored(conflict_present=False, conflict_score=None)
        assert result.conflict_present is False
        assert result.conflict_resolution_score is None

    def test_conflict_present_with_score_succeeds(self):
        result = make_scored(conflict_present=True, conflict_score=2)
        assert result.conflict_resolution_score == 2

    def test_conflict_present_missing_score_raises(self):
        with pytest.raises(ValidationError, match="conflict_present=True"):
            AnalyticalDepthJudgment(
                status=JudgeStatus.SCORED,
                reasoning_score=3,
                reasoning_reasoning="test",
                synthesis_score=3,
                synthesis_reasoning="test",
                conflict_present=True,
                conflict_resolution_score=None,
            )

    def test_no_conflict_but_score_set_raises(self):
        """The important negative case: a score should never leak in
        when there's nothing to resolve — same discipline as
        faithfulness_rate staying None instead of defaulting to 0.0."""
        with pytest.raises(ValidationError, match="conflict_present=False"):
            AnalyticalDepthJudgment(
                status=JudgeStatus.SCORED,
                reasoning_score=3,
                reasoning_reasoning="test",
                synthesis_score=3,
                synthesis_reasoning="test",
                conflict_present=False,
                conflict_resolution_score=4,
            )