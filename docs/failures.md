## F-001: Search latency exceeds budget on simple factual queries

Observed: 9,385ms for single Tavily search (simple factual, max_results=3)
Target: <3,000ms (p95), hard max 8,000ms
Hypothesis: geographic latency (Mingora → Tavily servers) + free tier throttling
Status: Known, not yet addressed. Async parallel search (Week 3) won't fix this —
it parallelises multiple queries, not a single slow one.
Next step: measure 10 queries and check if this is consistent or an outlier.

## F-002: Sources return conflicting numbers for the same query

Observed: Tokyo population query returns 36.9M, 10.3M, and 14M from three sources
Cause: different geographic definitions (metro vs city proper), different years
Impact: generation model has no way to resolve this without explicit source context
Status: Known. Addressed in Week 4 verification loop.

## F-003: Multi-hop queries fail by omission, not hallucination

Observed: "Who founded the company that makes the iPhone 15 chip?" → correctly
hedged, but never attempted decomposition (chip maker → Apple → founder)
Cause: naive pipeline has no query decomposition step
Status: Expected at this phase. Addressed in Week 2 (decomposer).

## F-004: Recency conflicts surfaced but not resolved

Observed: Bitcoin price query returned 5 different values from 5 sources,
correctly flagged as inconsistent, but no use of published_date to determine
which source is freshest
Cause: ranking/filtering doesn't yet use temporal metadata
Status: Known. Addressed in Week 3 (recency-aware ranking).

## F-005: [pending] Encoding bug — degree symbol corrupted (Â°C, Â°F)

Observed: boiling point answer rendered "100Â°C" instead of "100°C"
Hypothesis: [your guess here]
Status: Investigating

## F-006: Zero-claim answers were scored as 0.0 faithfulness (RESOLVED)

Observed: Q008 (multi-hop, "what year was the iPhone chip manufacturer founded") correctly hedged with zero citations - the model made no grounded claims because it correctly identified insufficient evidence. The scorer defaulted total_claims=0 to faithfulness_rate=0.0, the worst possible score, on an answer that did nothing wrong. Root cause: faithfulness_rate = supported/total if total > 0 else 0.0 treated "no claims to check" the same as "every claim checked and failed." This is the same bug class as the v2.0 curriculum's documented correctness=None pitfall, but inverted - v2.0 silently excluded hedges (inflating scores), we silently zeroed them (deflating scores). Both directions corrupt the metric. Fix: faithfulness_rate is now Optional[float] = None when total_claims==0. A new zero_claims boolean flag tracks this explicitly. run_eval.py's aggregator excludes None from averages rather than treating it as 0.0, and reports zero_claim_count separately so hedge behavior is visible, not hidden inside a corrupted average. Status: Resolved. Whether the hedge itself was CORRECT (vs. an unnecessary refusal) is a separate question for the hedge scorer, not yet built - this fix only stops faithfulness_rate from being wrongly computed on non-claims.

## F-007: Extractor failure mode #3 - comma/conjunction-joined compound facts

Observed: Q009 (Bitcoin price) produced "reports a price of $62,865.79, while states the price is $62,896.36" as ONE claim citing [2,3] - two distinct price facts joined by a comma and "while" instead of a full stop. The regex extractor only splits on sentence-ending punctuation, so this compound clause was never split. Each individual price was correctly sourced by its respective citation, but the merged claim asks a single source to support two different numbers, producing a false UNSUPPORTED verdict on facts that were each individually correct. Running count of Option A extractor failures across ~20 real answers: 3 (compound sentence with "or", bullet list, comma+conjunction join). Status: Known, documented. Switch trigger unchanged: >15% false negative rate on a full eval run. Current evidence suggests we're approaching a real decision point - worth counting precisely on the next full run.

## F-008: Judge synonym blindness - HFCV vs FCEV (judge calibration signal)

Observed: Q019 (EV vs hydrogen fuel cell comparison) - the model's answer used "HFCV" (Hydrogen Fuel Cell Vehicle), the source used "FCEV" (Fuel Cell Electric Vehicle) - same concept, different acronym. The judge marked the claim UNSUPPORTED with reasoning "the source text refers to FCEVs, not HFCVs" - a literal string mismatch, not a real grounding failure. This is a genuine judge miscalibration, not a generation failure or an extractor failure. Status: Known. This is exactly the kind of disagreement a human labeler would catch and Cohen's kappa would quantify. Concrete evidence for why judge calibration (Phase 1 exit criteria) matters before fully trusting faithfulness numbers at scale.

## F-003 update: multi-hop reasoning is inconsistent, not uniformly broken

Originally documented (Day 5): naive pipeline "fails multi-hop by omission, never attempts decomposition." Q005 in the full baseline run contradicts this - the model correctly distinguished "Apple designs the chip" from "TSMC manufactures it" and correctly identified Morris Chang as TSMC's founder, entirely from raw snippets, with no decomposition step. Q008 (a very similar question) failed to find the same information. Revised understanding: the naive pipeline's multi-hop performance is inconsistent and highly dependent on whether the needed facts happen to appear together in the retrieved snippets - not a clean pass/fail. This is a more accurate characterization than the original "fails by omission" framing, and it's still a real argument for Week 2's decomposer, just for a more precise reason: consistency, not capability.

## F-009: Pipeline latency and eval scoring latency were conflated

Observed: run_eval.py's original per-question latency wrapped search + generate + score_source_quality as one number, producing an average of 12,589ms with several questions over 22,000ms - appearing to blow through the <3s/8s budget in QUALITY.md by a wide margin. Root cause: the scoring step (multiple sequential judge calls per claim) is an offline, eval-time-only cost that never runs in a live user request - it has nothing to do with what a real user experiences. Conflating it with pipeline latency risks concluding "the system is too slow" when the actual pipeline (search+generate) might be fine, and only the measurement process itself is slow. Fix: run_eval.py now records pipeline_latency_ms (search+generate, what QUALITY.md's budget actually applies to) and scoring_latency_ms (judge overhead, offline-only) as two separate numbers. Status: Resolved in measurement. Actual pipeline latency against the <3s budget still needs to be checked once the next run reports the split number - don't assume it's fine just because the conflated number was misleading.

## F-010:

judge absence-claim blind spot — RESOLVED (JUDGE_PROMPT v1.1, explicit absence-claim handling added)

## F-011:

pipeline latency exceeds QUALITY.md budget (avg 9,279ms vs 3,000ms target / 8,000ms hard max) — PARKED. Trigger to revisit: start of Week 3 (async search work), or sooner if latency blocks a decision we need to make before then. Not a measurement-trust issue — the eval harness's faithfulness numbers remain meaningful even though the pipeline itself is slow.

## F-012:

run-to-run non-determinism (unpinned search results + generation temperature) — NOT A BUG, but a standing reminder: single-run, per-question numbers are not stable ground truth. This is exactly why the Statistical Rigor section of this checklist (bootstrap 95% CIs) exists — don't fully trust a number until that's built.

## F-013: Judge verdict doesn't always match its own reasoning (compound claims)

Observed: two cases in one run, opposite directions. Q008: reasoning states "the text is cut off and we cannot confirm... " - textbook insufficient_evidence language - but verdict field says "unsupported." Q009: reasoning states one of two cited prices "does not mention $64,808.11" (unconfirmed) - but verdict field says "supported" for the whole compound claim anyway. Root cause: both claims are compound (multiple facts merged by the known extractor limitation, TD-004). Forcing multiple sub-facts with different truth values into one verdict slot makes the judge's structured output inconsistent with its own stated reasoning - sometimes rounding down to a harsher verdict than the reasoning supports, sometimes rounding up to a more lenient one. Impact: this is a distinct, more concerning reliability gap than F-010 - it's not about one claim shape (absence claims), it's about the verdict field not being reliably grounded in the reasoning field at all, once claims are compound. Any faithfulness number computed from compound claims should be treated with real skepticism until this is addressed. Status: Known, not yet fixed. Likely resolved together with TD-004 (fixing the extractor to stop producing compound claims in the first place would remove most of the conditions that trigger this).

## F-014: Presentation scorer dimension bleed — repetition penalized organisation score (RESOLVED)

Observed: JUDGE_PROMPT v1.0 scored a topically well-ordered but repetitive
report at organisation=1, and a genuinely scrambled but cleanly-worded
report at organisation=3 — the more disorganized report scored higher.
Judge's own reasoning on the first case cited "repetitive and disordered"
as justification for the organisation score, conflating a fluency
property with an organisation property.

Root cause: JUDGE_PROMPT v1.0 defined each dimension (clarity,
organisation, fluency) but never told the judge to exclude the other
two dimensions' signals when scoring one of them.

Fix: JUDGE_PROMPT v1.1 adds explicit exclusion clauses per dimension
("ignore repetition when judging organisation," etc.). Reran the same
two planted reports post-fix: organisation now orders correctly
(bad-organisation=3 < bad-fluency=4).

Status: Resolved. Open watch, not yet confirmed: v1.1's fluency score
on the bad-organisation report dropped to 2, reasoning citing "lacking
cohesive linking between ideas" — possibly a legitimate fluency
observation, possibly the same bleed running in the other direction.
One run only. Needs repeated runs against the same fixed input before
deciding real vs. noise (F-012 precedent: single-run numbers aren't
stable ground truth). Do not patch the prompt again until confirmed.
