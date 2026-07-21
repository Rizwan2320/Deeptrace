"""
Manual calibration check for task_compliance_scorer.py.
Not pass/fail — no ground truth yet. Read the output.

Run: python scripts/check_task_compliance_scorer.py
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.task_compliance_scorer import judge_task_compliance, JudgeStatus

QUERY_FULL = "What are the two main reasons solar panel costs have fallen?"
REPORT_FULL = """\
Solar panel costs have fallen for two main reasons. First, manufacturing
has scaled up significantly, driving down the per-unit cost of silicon
processing and panel assembly through economies of scale. Second, cell
efficiency has improved from roughly 15% a decade ago to about 22% today,
so each panel produces more power for the same materials cost."""

QUERY_PARTIAL = "What are the two main reasons solar panel costs have fallen?"
REPORT_PARTIAL = """\
Solar panel costs have fallen mainly due to improvements in manufacturing
scale, which has driven down the per-unit cost of production significantly
over the past decade."""


QUERY_HEDGE = "What will the price of Bitcoin be on December 31, 2026?"
REPORT_HEDGE = """\
The available sources do not contain reliable information to predict a
future Bitcoin price on a specific date. Bitcoin's price is highly
volatile and no source can be treated as a gold answer for a future date.
I cannot provide a specific figure for this query."""



def run_check(label: str, query: str, report: str):
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    result = judge_task_compliance(query, report)

    if result.status == JudgeStatus.JUDGE_ERROR:
        print(f"JUDGE_ERROR: {result.error_detail}")
        return

    print(f"coverage_score: {result.coverage_score}")
    print(f"covered:        {result.covered_points}")
    print(f"missing:        {result.missing_points}")
    print(f"reasoning:      {result.reasoning}")


if __name__ == "__main__":
    run_check("FULL COVERAGE (expect score ~5)", QUERY_FULL, REPORT_FULL)
    run_check("PARTIAL COVERAGE (expect score ~2-3, missing_points non-empty)", QUERY_PARTIAL, REPORT_PARTIAL)
    run_check("CORRECT HEDGE (expect score 5 — refusal is compliance, not failure)", QUERY_HEDGE, REPORT_HEDGE)