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
