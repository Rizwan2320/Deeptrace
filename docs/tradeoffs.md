## TD-001: Correlation IDs deferred to pipeline wiring

Decision: Not adding request_id to individual module logs yet.
Reason: Adding it before the FastAPI layer exists means passing it as a
parameter through every function — premature coupling.
Tradeoff: Logs are currently untraceable across modules.
Resolution: Add request_id at the FastAPI layer (main.py) and thread it
through search() and generate() when the endpoint is built.
Status: Resolved in Week 1A pipeline wiring.

## TD-002: Agreement/determinacy inferred from category, not its own field

Decision: gold_answer is nulled out when volatility == VOLATILE OR
category == ANALYTICAL. There is no explicit "agreement" or "determinacy"
field — low agreement is currently inferred only from category being
analytical.
Reason: with 5 categories and 20 questions, a dedicated field would be
premature structure for a distinction that only one category needs right
now.
Tradeoff: if a future category needs to express low agreement independently
of being "analytical" (e.g. a volatile question that is ALSO low-agreement,
like predicting next week's interest rate decision), the current schema
can't express that combination cleanly.
Resolution: deferred. Revisit if/when a new question category needs both
volatility and low-agreement set independently. Don't add the field
preemptively — this is exactly the kind of complexity that should be
earned by a real example, not designed for in advance.
Status: Open, monitoring.

## TD-003: Claim extraction deferred — hallucination scorer is atomic only

Decision: hallucination_scorer.py judges one claim against one source.
No orchestration layer yet to extract claims from a full answer and pair
them with their cited sources.
Reason: building the atomic unit correctly before the orchestration layer
prevents the orchestration from hardcoding assumptions about what the
atomic unit returns. If the judge's output schema changes, the orchestration
layer changes in one place.
Tradeoff: the hallucination scorer is not yet usable on a real eval run —
it requires a claim-extraction layer to sit above it.
Resolution: next file to build.
Status: Open.

# TD-004: Claim extractor approach — Option A vs Option B

Decision: pending — see next session.
Option A (regex sentence splitter): free, deterministic, fast. Breaks on
multi-sentence claims and uncited sentences.
Option B (LLM claim extractor): handles complex structures. Costs tokens,
introduces non-determinism, adds latency to every eval run.
Tradeoff: Option A is cheap but brittle; Option B is robust but expensive
for a tool that runs on every eval. The right answer depends on how often
real model answers actually produce multi-sentence claims with shared
citations — empirical question, not a theoretical one.
Status: Pending decision.

## TD-004: Claim extractor — Option A (regex) now, Option B (LLM) when earned

Decision: build regex extractor first, behind a shared extract_claims()
interface. LLM extractor implements the same interface when Option A
demonstrably fails on real answers.
Trigger for switching: a specific answer where regex mis-pairs claims and
sources, measurably reducing faithfulness score vs. manual grading.
Cost of switching: one import line. Zero changes to eval orchestration.
Status: Resolved. Build Option A now.

## TD-004 update 1: concrete failure case observed

Observed in first real test: compound sentence "boiling point is 373 K [1],
equivalent to 100°C [1, 3, 4, 5] or 212°F [1, 3]" collapsed into one
ClaimSourcePair with union of citations [1, 3, 4, 5]. The judge now evaluates
the entire compound claim against each source individually — source [3] which
only covers 100°C gets asked to support a claim that also includes 373 K and
212°F, which it doesn't. This produces false "insufficient_evidence" verdicts
on claims that are individually well-supported.
Switch trigger: if this false insufficient_evidence rate exceeds 15% on real
eval runs, switch to LLM extractor.

## TD-004 update 2: bullet-list answers not handled by regex splitter

Observed: Bitcoin price query produced a bullet-list answer. The regex
splitter (splits on sentence-ending punctuation) treated the entire
bullet block as one compound claim, collapsing five individually-sourced
prices into one claim judged against one source. Result: faithfulness
rate 0.0 on an answer that was actually correct and well-sourced.
This is a false negative — the scorer is penalizing good behavior.
Running tally of Option A failures: 2 (compound sentence, bullet list).
Switch trigger remains: if false negative rate exceeds 15% on a full
eval run, switch to LLM extractor.
