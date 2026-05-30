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
