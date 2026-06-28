## 🔍 Tavily Search API: Response Schema Learnings

-What fields does each result object contain? → Usually title, url, content, score, and raw_content (plus optional fields like favicon or images).
-What does the score field represent — what range is it in? → It’s Tavily’s relevance/confidence score from 0.0 to 1.0, where higher means a better match.
-Is published_date always present, or is it sometimes missing? → It’s sometimes missing and should be treated as optional.

### ⚠️ Field Presence Is Conditional

- `raw_content`, `favicon`, `images` only appear if explicitly requested via `include_*` flags.
  → **Action**: Always validate presence with `.get()` or Pydantic optional fields. Never assume.

🌐 HTTP & Pydantic Internals: Client Integration Learnings

1.  Why @lru_cache(maxsize=1) on get_settings()?
    Performance: Prevents repeated, unnecessary disk I/O and environment variable parsing on every function call.
    Singleton Pattern: Guarantees the entire app uses the exact same settings instance in memory, preventing configuration drift.
    Why not call Settings() directly? Calling it directly creates a new object every time, wasting resources and breaking the singleton guarantee.
    2: When does the crash happen if tavily_api_key is missing?
    Timing: It crashes at import time, not when the function is first called.
    Why: In client.py, the line settings = get_settings() is written at the module level (outside any function). Python executes module-level code the moment the file is imported. It immediately triggers get_settings(), which instantiates Settings(), reads the .env, and validates the missing key.
    Lesson: If you actually wanted lazy evaluation (delaying the crash until the API is called), you would need to move settings = get_settings() inside the search() function. However, failing at import time is often preferred in production because it "fails fast" and prevents the app from running with broken configuration.

### 🐍 Validation & Schema Design: `SearchResult` Model

**Q: What does `Optional[str] = None` mean for `published_date`? Why not just `str`?**
A:It means published_date can be a string or None because Tavily may omit that field in some results.Because not every webpage/result has a detectable publish date, so Tavily may not be able to extract one and leaves published_date out.

**Q: What happens if you instantiate `SearchResult` without passing `raw_content`?**
A: raw_content becomes None automatically because it has a default value.
**Q: Why does `score_must_be_valid` raise `ValueError` instead of returning `None`?**
A: It raises ValueError so invalid scores fail validation immediately instead of being accepted as None.Because returning None would make score become None, while raising ValueError clearly tells Pydantic the value is invalid and should reject that result.

> 💡 **Production takeaway**: Schema types should reflect API reality, not assumptions. Optional fields with `None` defaults keep pipelines running; strict validators with raised exceptions keep them honest.

### 🌐 HTTP & Pydantic Internals: Client Integration Learnings

**Q: What does `response.raise_for_status()` do, and what happens on a 429?**
A: It checks the HTTP status code. If `2xx`, it returns `None` silently. If `4xx` or `5xx`, it raises `requests.exceptions.HTTPError`. On a `429` (Tavily rate limit), it raises immediately with `HTTPError: 429 Client Error: Too Many Requests`. If unhandled, this crashes the call stack.
→ **Production fix**: `requests` doesn't auto-retry. Wrap the call in `tenacity` or `urllib3.util.Retry` with exponential backoff, or catch `HTTPError` and branch on `response.status_code` before propagating.

**Q: Why measure latency with `time.perf_counter()` instead of `time.time()`?**
A: `perf_counter()` is monotonic and uses the highest-resolution clock available. It _cannot_ jump backward/forward due to NTP syncs, manual clock adjustments, or DST changes. `time.time()` reads the wall clock, which can drift mid-measurement, making latency calculations inaccurate or even negative. Always use `perf_counter()` for intervals/benchmarking.

**Q: `SearchResult(**r)`— what if Tavily adds a new field we haven't modeled? Crash or ignore?**
A: Pydantic v2 defaults to`extra="ignore"`, so it silently drops unknown fields and instantiates cleanly. No crash. If you configure `extra="forbid"`, it raises `ValidationError`. If `extra="allow"`, it stores them in `result.model_extra`.
→ **Production takeaway**: Default ignore behavior shields you from upstream API drift, but hides schema evolution. In staging, set `extra="forbid"`to catch breaking changes early. In prod, log`model_extra` when present to maintain observability into API changes you haven't explicitly handled.

Q1:Why is temperature=0.1 and not 0.0 or 0.7? What does temperature control, and what's the trade-off?
ANS:temperature=0.0, most APIs including Groq don't guarantee full determinism anyway due to floating point arithmetic and request batching. So 0.0 gives you the illusion of determinism without the guarantee. 0.1 is the honest version of the same intent.
Q2:Why does the prompt explicitly say "Do not use your training knowledge"? Does the model actually obey this instruction?
ANS:the model frequently disobeys it when sources are thin. When Tavily returns weak snippets and the model "knows" the answer from training, it will use that knowledge and dress it up as if it came from the sources. Your hallucination rate scorer in Week 1B exists precisely because this prompt instruction is not a reliable defence — it's a signal, not a wall. Rewrite that answer to be blunt about this. It matters for how you interpret your eval results.
Q3:PROMPT_VERSION = "v1.0" is logged on every call. Why does that matter for your eval results?
ANS:Logging the prompt version lets you trace evaluation results back to the exact prompt used, making it possible to compare prompt changes and identify whether quality improvements or regressions came from the prompt itself.

## Why 502 and not 404 or 500 when search returns no results?

502 means "bad gateway" — the server received a bad response from an upstream
dependency (Tavily). 404 means "resource not found" — wrong here because the
/research endpoint exists. 500 means "our code crashed" — wrong because no
crash occurred, the upstream simply failed us. HTTP status codes communicate
failure origin. 502 tells the client: retry later, this isn't your fault and
it isn't a bug in our code.

## What does response_model=ResearchResponse do in FastAPI?

FastAPI uses it to: (1) validate that the endpoint actually returns what it
claims — if a field is missing, FastAPI raises an error before the response
leaves the server; (2) auto-generate OpenAPI documentation with the exact
response schema; (3) filter out any extra fields not in the model, preventing
accidental data leaks. In production: it's a contract enforced at runtime,
not just a type hint the interpreter ignores.

## tility a separate field from category, not folded into it?

They're independent axes. A multi-hop question can be stable (TSMC's
founding year) or volatile (the current Instagram CEO). Merging them into
one field would force duplicate categories (multi_hop_stable,
multi_hop_volatile...) or lose the distinction entirely. Orthogonal
concerns get orthogonal fields.

Why does running a script with -m matter for imports?

When you run python some_script.py directly, Python adds that script's
own containing folder to sys.path — not necessarily the project root. If
the script needs to import a sibling package, Python looks for it relative
to wherever the script physically lives.

validate_gold_dataset.py lives INSIDE evals/. Running it directly
(python evals/validate_gold_dataset.py) puts evals/ itself on sys.path —
so from evals.models import ... fails, because Python is looking for an
"evals" folder inside evals/, not for evals/ as a package one level up.
Running it with -m (python -m evals.validate_gold_dataset) instead
starts sys.path from the project root and treats it as a module inside
the evals package — that's why the import resolves.

## Why didn't test_citation_scorer.py need the -m flag?

Because it lives directly in the project root, not inside a package
subfolder. Running it directly adds its own containing folder to
sys.path — and that folder IS the project root, so "evals" resolves
correctly as a subfolder right there. The -m flag only matters when the
script you're executing is itself inside the package it needs to import
from. Root-level scripts never have this problem, because the root
already contains every top-level package you've built.

## A technically-correct number can still hide a real distinction

The gold dataset validator originally printed "9 questions without a fixed
gold_answer" as one number. That number was accurate — but it silently
merged two different root causes: 5 questions had no fixed answer because
they're volatile (the true answer changes over time), and 4 had no fixed
answer because they're analytical (no single answer exists even at one
point in time). The fix wasn't a different number — it was splitting one
number into the two causes underneath it. Whenever a metric combines
distinct failure reasons into one count, the count can be true and still
hide the thing you actually need to see.

## Volatility (time) is not the same axis as agreement (consensus)

"Stable" describes whether the ground truth drifts as time passes —
TSMC's founding year is stable, Bitcoin's price is volatile. "Agreement"
describes something orthogonal: whether everyone looking at the same facts
right now converges on one answer. Analytical questions are stable (the
trade-offs between microservices and monoliths don't change month to
month) but have permanently low agreement (two competent engineers can
weigh the same trade-offs differently and both be right). Recency
questions are usually high-agreement but volatile (everyone agrees on
today's Bitcoin price; that agreed-on number is wrong tomorrow). These are
two separate dimensions that happened to get collapsed into one field
(category == analytical implies low agreement) because the dataset is
small enough that it didn't matter yet.
