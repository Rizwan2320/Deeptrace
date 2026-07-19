# test_absence_claim_fix.py (throwaway)
from evals.hallucination_scorer import judge_claim

# Case 1 — mirrors Q005: a TRUE absence claim. Source genuinely doesn't
# mention founders. Should now be SUPPORTED (was UNSUPPORTED before the fix).
print("Case 1 - true absence claim:")
print(judge_claim(
    claim="The source does not mention who founded the company.",
    source_text="Apple designs its own A17 Pro processor chip for the iPhone 15. The chip features a 6-core CPU and 6-core GPU.",
))

# Case 2 — the overcorrection check. A FALSE absence claim - the source
# DOES contain the info, but the claim says it doesn't. Must stay
# UNSUPPORTED. If this now incorrectly says SUPPORTED, the fix overcorrected
# into blindly trusting any absence claim.
print("\nCase 2 - false absence claim (overcorrection check):")
print(judge_claim(
    claim="The source does not mention who founded the company.",
    source_text="TSMC was founded by Morris Chang in 1987 and builds chips for Apple and NVIDIA.",
))

# Case 3 — mirrors Q006: compound claim mixing a positive fact with an
# absence fact in one sentence.
print("\nCase 3 - compound positive+absence claim:")
print(judge_claim(
    claim="WhatsApp is owned by Meta Platforms, but the source does not specify Meta's headquarters country.",
    source_text="WhatsApp was acquired by Meta Platforms in 2014 for $19 billion.",
))