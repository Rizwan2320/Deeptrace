## 🔍 Tavily Search API: Response Schema Learnings

### ⚠️ Field Presence Is Conditional

- `raw_content`, `favicon`, `images` only appear if explicitly requested via `include_*` flags.
  → **Action**: Always validate presence with `.get()` or Pydantic optional fields. Never assume.
  ```python
  # Safe access pattern
  content = result.get("raw_content") or result.get("content")
  ```

### 🐍 Validation & Schema Design: `SearchResult` Model

**Q: What does `Optional[str] = None` mean for `published_date`? Why not just `str`?**
A: It tells the type checker and validator that the field can be a string or `None`, and `= None` makes it non-required with a safe default. We use this because Tavily's API doesn't guarantee publication metadata (Wikipedia, docs, and scraped pages often omit it). If we typed it as `str`, Pydantic would throw a `ValidationError` the moment the API omits the field, crashing the ingestion pipeline. `Optional[str] = None` maps the _actual_ API contract, not the ideal one.

**Q: What happens if you instantiate `SearchResult` without passing `raw_content`?**
A: It defaults to `None` and the model instantiates cleanly. No error. The trade-off is that downstream code must explicitly check for presence (`if result.raw_content:`) before processing. If you skip that guard, you'll hit runtime `TypeError`s when calling string methods on `None`. This is intentional: it keeps payloads lightweight by default and forces explicit handling of optional data, which is critical when scaling eval harnesses or batch processors.

**Q: Why does `score_must_be_valid` raise `ValueError` instead of returning `None`?**
A: Validation is meant to be fail-fast. Returning `None` would silently accept invalid or missing scores, pushing corrupted data downstream where it breaks ranking logic, evals, or LLM context windows. Raising `ValueError` immediately halts processing of that record, surfaces the exact bad input in logs, and preserves system integrity. In Pydantic, validators specifically use exceptions to signal "reject this input" — returning any value means "accept and possibly transform it."

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
