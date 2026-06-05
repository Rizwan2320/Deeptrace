## TD-001: Correlation IDs deferred to pipeline wiring

Decision: Not adding request_id to individual module logs yet.
Reason: Adding it before the FastAPI layer exists means passing it as a
parameter through every function — premature coupling.
Tradeoff: Logs are currently untraceable across modules.
Resolution: Add request_id at the FastAPI layer (main.py) and thread it
through search() and generate() when the endpoint is built.
Status: Resolved in Week 1A pipeline wiring.
