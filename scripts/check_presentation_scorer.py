"""
Manual calibration check for presentation_scorer.py.

Not a pass/fail test — there's no ground truth to assert against yet
(that's what Day 5 judge calibration is for, against ~30 hand-scored
items). This is the cheaper, earlier step: does the judge's scoring
even move in the right direction on obviously-different inputs?

Run: python scripts/check_presentation_scorer.py
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.presentation_scorer import judge_presentation, JudgeStatus

# Same underlying facts, three deliberately different writing qualities.
GOOD_REPORT = """\
Solar panel efficiency has improved significantly over the past decade.
Standard commercial panels now convert roughly 22% of sunlight into
electricity, up from about 15% ten years ago. This gain comes mainly
from better cell materials and reduced manufacturing defects.

Cost has fallen alongside efficiency. The price per watt of installed
solar capacity has dropped by more than half since 2015, driven by
economies of scale in manufacturing and cheaper silicon processing.

Together, these two trends explain why solar is now cost-competitive
with fossil fuels in most sunny regions without subsidies."""

BAD_FLUENCY_REPORT = """\
Solar panel efficiency has improved. Solar panels are more efficient
now than before. The efficiency of solar panels has gone up. This is
because solar panel efficiency has increased over time. Efficiency
gains in solar panels are due to better efficiency in the cells used.
Cost has also gone down. The cost of solar has decreased. Solar costs
less than it used to cost, which is a decrease in cost."""

BAD_ORGANISATION_REPORT = """\
Cost-competitive with fossil fuels now in sunny regions. Silicon
processing cheaper. 22% efficiency for commercial panels currently.
Manufacturing economies of scale drove the price drop. No subsidies
needed in many cases. Ten years ago it was about 15% efficiency.
Price per watt down more than half since 2015. Better cell materials
are part of why efficiency went up. Fewer manufacturing defects too."""


def run_check(label: str, text: str):
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    result = judge_presentation(text)

    if result.status == JudgeStatus.JUDGE_ERROR:
        print(f"JUDGE_ERROR: {result.error_detail}")
        return

    print(f"clarity:      {result.clarity_score}  — {result.clarity_reasoning}")
    print(f"organisation: {result.organisation_score}  — {result.organisation_reasoning}")
    print(f"fluency:      {result.fluency_score}  — {result.fluency_reasoning}")


if __name__ == "__main__":
    run_check("GOOD REPORT (expect high scores across the board)", GOOD_REPORT)
    run_check("BAD FLUENCY (expect low fluency, clarity/organisation should stay reasonable)", BAD_FLUENCY_REPORT)
    run_check("BAD ORGANISATION (expect low organisation, fluency/clarity should stay reasonable)", BAD_ORGANISATION_REPORT)