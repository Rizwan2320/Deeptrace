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
