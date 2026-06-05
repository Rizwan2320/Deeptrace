# INTERVIEW_PREP.md — Deep Research Agent

## Search & Data Modeling

**Q: Why would you use Pydantic validators over a plain dataclass for external API data?**
Tests: defensive engineering, understanding of data contracts
Why they ask: big tech systems ingest data from dozens of external APIs.
Interviewers want to know if you think about failure at the boundary,
not after the bad data has already corrupted three downstream services.
Your answer should mention: fail-fast validation, API contract vs ideal contract,
silent failures vs loud failures, and what happens at scale when 1 in 10,000
API responses has a malformed field.

---

## Data Modeling & Validation

**Q: You're ingesting data from a third-party API. The API sometimes omits fields
it claims are always present. How do you model this defensively, and where does
validation belong in the pipeline?**
Tests: Pydantic/schema design, defensive engineering, API contract thinking
Why they ask: every production system at scale eventually hits an API that lies
about its schema. They want to see if you validate at the boundary (correct) or
deep inside business logic (expensive mistake).
Your answer should mention: Optional fields with None defaults, field_validators
that raise ValueError not return None, validating at ingestion before data
enters any business logic, and the cost of silent failures at scale.

---

**Q: What is the difference between `Optional[str]` and `Optional[str] = None`
in Pydantic v2, and when does it matter?**
Tests: Pydantic v2 internals, precision under pressure
Why they ask: this is a common footgun. They want to know if you've actually
hit this bug or if you just read the docs. `Optional[str]` still requires the
field — it just allows None as a value. `Optional[str] = None` makes the field
truly non-required. Matters every time you model an API that omits fields.

**Q: A third-party API adds a new field you haven't modeled.
How does Pydantic handle it, and what's the right production strategy?**
Tests: Pydantic internals, API contract management, staging vs prod discipline
Why they ask: upstream API drift is inevitable at scale. They want to know
if you've thought about schema evolution beyond "it works today."
Your answer should mention: extra="ignore" default, extra="forbid" in staging
to catch breaking changes early, logging model_extra in prod for observability,
and why silent schema drift is a latency/correctness time bomb.
