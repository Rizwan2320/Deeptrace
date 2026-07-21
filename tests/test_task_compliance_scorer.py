"""
Unit tests for task_compliance_scorer.py's validation logic only.
No API calls. Judge quality itself is checked in
scripts/check_task_compliance_scorer.py, formal κ calibration in Day 5.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pytest
from pydantic import ValidationError

from evals.task_compliance_scorer import TaskComplianceJudgment, JudgeStatus


def make_scored(score=3):
    return TaskComplianceJudgment(
        status=JudgeStatus.SCORED,
        coverage_score=score,
        covered_points=["point a"],
        missing_points=[],
        reasoning="test",
    )


class TestScoreClamping:
    def test_above_range_clamps_to_5(self):
        assert make_scored(score=9).coverage_score == 5

    def test_below_range_clamps_to_1(self):
        assert make_scored(score=0).coverage_score == 1

    def test_in_range_value_unchanged(self):
        assert make_scored(score=3).coverage_score == 3


class TestStatusInvariant:
    def test_scored_with_score_succeeds(self):
        assert make_scored().status == JudgeStatus.SCORED

    def test_scored_missing_score_raises(self):
        with pytest.raises(ValidationError, match="coverage_score"):
            TaskComplianceJudgment(status=JudgeStatus.SCORED)

    def test_judge_error_without_score_succeeds(self):
        result = TaskComplianceJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail="Parse failed: test",
        )
        assert result.coverage_score is None

    def test_default_empty_lists(self):
        result = TaskComplianceJudgment(status=JudgeStatus.JUDGE_ERROR)
        assert result.covered_points == []
        assert result.missing_points == []