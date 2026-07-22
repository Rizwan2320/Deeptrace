"""
Manual calibration check for analytical_depth_scorer.py.
Not pass/fail — no ground truth yet. Read the output.

Run: python scripts/check_analytical_depth_scorer.py
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evals.analytical_depth_scorer import judge_analytical_depth, JudgeStatus

GOOD_ANALYTICAL_REPORT = """\
Tokyo's population is often cited inconsistently, with figures ranging
from about 9 million to over 37 million depending on the source. This
variation is not a contradiction — different sources use different
geographic definitions. Tokyo's 23 special wards have roughly 9-10
million residents; the broader Tokyo Metropolis reports about 14
million; the full Greater Tokyo Area, including surrounding prefectures
like Kanagawa and Saitama, is often reported near 37 million. For most
comparisons with other world cities, the Greater Tokyo Area figure is
the standard reference, since it captures the full metropolitan economic
and commuting zone rather than just the administrative core."""

FLAT_AGGREGATION_REPORT = """\
Tokyo's population is 14 million. Tokyo's population is also reported
as 37 million. Tokyo's population is sometimes given as 9 million. The
Tokyo Metropolis area is large. Tokyo is a major city in Japan. Tokyo
has many wards. Tokyo is densely populated."""

NO_CONFLICT_REPORT = """\
Photosynthesis converts light energy into chemical energy stored in
glucose. This process is foundational because it forms the base of
nearly every food chain on Earth — most organisms depend, directly or
indirectly, on the energy captured by photosynthetic organisms. Its
byproduct, oxygen, is what makes aerobic respiration possible for
complex life, which is why the evolution of photosynthesis is considered
one of the most consequential events in the planet's biological
history."""


r = judge_analytical_depth(FLAT_AGGREGATION_REPORT)
print(f"conflict_present: {r.conflict_present}")
print(f"conflict_resolution_score: {r.conflict_resolution_score}")
print(f"conflict_resolution_reasoning: {r.conflict_resolution_reasoning}")

