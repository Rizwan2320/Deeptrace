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

## Why temperature=0.0 for the judge but 0.1 for the generator?

The generator's job is synthesis — slight variation in wording is acceptable and even desirable for natural-sounding answers. The judge's job is consistent grading — the same claim against the same source should always produce the same verdict. We push determinism as far as it goes for the judge (0.0), accepting that it's not a hard guarantee due to floating point and batching, because consistency matters more than creativity here.

## Why three verdicts instead of two for the hallucination judge?

Collapsing "insufficient evidence" into either supported or unsupported corrupts the hallucination rate in opposite directions:

Forcing it into "supported" deflates hallucination rate — the system looks healthier than it is, hiding retrieval failures as generation wins.
Forcing it into "unsupported" inflates hallucination rate — you start fixing a generation problem that doesn't exist, when the real problem is that Tavily's snippets are too short to judge against. The third verdict separates two different failure modes: "unsupported" means the generation step overreached; "insufficient_evidence" means the retrieval step under-delivered. They point at different modules to fix.
Why does the hallucination judge explicitly say "do not use your own
knowledge of whether the claim is true in the real world"?

Without this instruction, the judge grades on real-world truth rather than source grounding. A claim can be true in reality and still be unsupported if this specific source doesn't say it — and that's exactly the failure mode we're measuring. Without the instruction, the judge would mark well-known true facts as "supported" even when the source says nothing about them, making the faithfulness scorer useless.

## Why recency is not a category — it's a property

"Recency" describes a temporal property of any question's answer, not a structural property of the question itself. A simple factual question can be volatile (Bitcoin price), a multi-hop question can be volatile (current CEO of Instagram's parent company), and an adversarial question can be volatile. Putting recency as a fifth category forced all volatile questions into one bucket, losing the structural information about how they should be retrieved, decomposed, and scored. Volatility belongs on its own axis.

## The four volatility levels and what they imply operationally

immutable: the answer cannot change by any real-world event (boiling point of water, chemical formula). Gold answers never need re-verification. slow_changing: changes on yearly timescales (population figures, broad trade-off analyses). Re-verify gold answers annually. fast_changing: changes on monthly timescales (software versions, model releases). Re-verify gold answers monthly. volatile: changes on daily/hourly timescales (prices, weather, current officeholders). No fixed gold answer — grade on behavior only.

## Why the two Source Quality numbers are never averaged

Citation validity (structural) and faithfulness rate (semantic) measure different failure modes in different layers. Citation validity failing means the generation layer produced a malformed output — wrong source index format. Faithfulness failing means the generation layer overreached its sources — it said something the sources don't back. Averaging them into one number hides which layer broke. A system with perfect citation formatting and 40% faithfulness looks like 70% on an averaged score — and you'd have no idea whether to fix your prompt or your source ranking. Keep them separate. Always report them separately.

## Best-of scoring for multi-source claims

When a claim cites multiple sources ([1, 3, 4, 5]), a claim is SUPPORTED if ANY one of those sources supports it. This is the generous interpretation — appropriate when measuring whether the model grounded itself in something real, not whether every attached citation was individually necessary. The short-circuit return on the first SUPPORTED verdict also saves Groq API calls on the remaining sources.

## Verdict priority when no source supports a claim

When best-of scoring finds no SUPPORTED verdict across all cited sources, the priority order is: JUDGE_ERROR > UNSUPPORTED > INSUFFICIENT_EVIDENCE. JUDGE_ERROR takes top priority because a parse failure is a measurement uncertainty, not a content verdict — it should be visible, not buried under a content label. UNSUPPORTED beats INSUFFICIENT_EVIDENCE because a direct contradiction is a stronger, more actionable signal than "all sources were vague." Knowing a claim was directly contradicted points at the generation prompt. Knowing all sources were vague points at retrieval quality. Different modules, different fixes.

JUDGE_ERROR counts against faithfulness_rate in the denominator

A parse failure is treated as a conservative failure — it pulls faithfulness_rate down rather than being excluded from the calculation. The judge_error_rate is reported separately so you know how much measurement uncertainty is baked into a given faithfulness_rate. If judge_error_rate > 15%, treat that run's faithfulness_rate as unreliable.

## Option A failure mode 2 — bullet-list answers

The regex claim extractor splits on sentence-ending punctuation. Bullet list answers have no sentence-ending punctuation between items, so the entire list becomes one compound claim. This produced a false 0.0 faithfulness rate on the Bitcoin query — the model's answer was actually correct and well-sourced, but the extractor collapsed five individually- sourced prices into one claim that no single source could support alone. A false negative on a good answer is dangerous: it would tell you to fix generation when generation is fine, and retrieval when retrieval is fine. Running count of Option A failure modes: 2 (compound sentence, bullet list). Switch to LLM extractor when false negative rate exceeds 15% on a full eval run.

## results[idx - 1] is a fragile coupling point

The scorer assumes source indices in citations map directly to list position (1-indexed). This is true as long as results are passed through in the same order they were retrieved. If anything ever reorders or filters results between generation and scoring without renumbering citations, this silently judges the wrong source. Not a bug today — a fragile assumption worth remembering as the pipeline grows.

## Why generation and verification must be separate passes, not simultaneous

Asking the same LLM to generate a claim and check that claim in the same context/forward-pass is asking it to grade its own homework while still writing it. The model has already committed, in that context, to the belief that a source supports its claim — asking it to reassess in the same breath produces overwhelming self-confirmation, not real checking. This is called self-consistency bias.

The mitigation is architectural, not prompt-based: run verification as a genuinely separate call that never sees the generator's own reasoning or justification — only the claim and the raw source text. That's why judge_claim(claim, source_text) doesn't receive the full original answer or the generator's confidence — seeing those would let the judge anchor on the generator's own justification instead of checking independently.

This is the same core insight behind Chain-of-Verification (CoVe, Week 7): verification questions must be answered without the model seeing its own baseline answer, or the "check" becomes an echo of the original claim rather than an independent judgment.

Trade-off: this costs one extra LLM call per claim (N+1 calls instead of 1). Worth paying for an independent check, but it's a real latency/cost tax that should be named explicitly, not hidden.

Known limitation: the judge is currently the same underlying model (Llama-3.3-70b) as the generator, just called separately. This is better than same-context self-check but not as strong as a genuinely different model as judge — a systematic blind spot in the model could appear in both generation and verification. Not fixed today; held as a known gap

## Zero claims is not the same as zero faithfulness

An answer with no extractable claims (typically a correct hedge) and an answer where every claim was checked and failed are completely different situations, but forcing both onto a 0.0-1.0 scale makes them look identical. This is the exact same failure class as the v2.0 curriculum's documented correctness=None bug - discovering it independently, in code you wrote yourself, makes the lesson land differently than reading about it. The fix is the same principle every time: don't force a "cannot measure this" case into the same numeric range as "measured, and it failed." Give it its own explicit signal (None, a separate flag, a separate count) instead.

## Judges can fail on synonyms, not just facts

The hallucination judge marked a claim UNSUPPORTED because the answer said "HFCV" and the source said "FCEV" - the same concept, different acronym. This is a real limitation: an LLM judge doing literal text comparison can miss that two different surface forms refer to the same thing. This is exactly why judge calibration against human-labeled examples matters before trusting a judge's numbers at scale - a human would immediately recognize the synonym; the judge didn't. A single run already surfaced a concrete disagreement case worth calibrating against, not a hypothetical one.

## Never let a single latency number hide two different costs

Wrapping "time the user waits" (search + generation) and "time the eval harness spends judging after the fact" (multiple sequential LLM calls per claim) into one number risks a wrong conclusion. A 12+ second average looked like a production latency crisis. Separating the two numbers is necessary before deciding whether there's actually a problem, and if so, which part of the system has it.

## One real eval run surfaces more real bugs than ten spot-checks

Two hand-picked test queries (boiling point, Bitcoin) looked clean and confirmed the scorer worked. Running the same scorer across 20 diverse questions in one pass surfaced three new things in a single run: a scoring bug (zero-claims defaulting to 0.0), a third extractor failure mode (comma-joined compound facts), and a genuine judge miscalibration (synonym blindness). Diversity of test cases matters more than volume of manual spot-checks - the bugs that matter hide in the categories you haven't tried yet, not in re-running the same query you already trust.

## Why test a prompt fix in isolation instead of rerunning the full pipeline

Rerunning Q005/Q006 through the full pipeline (search + generate + judge)
to verify the absence-claim fix would have changed two variables at once:
the judge prompt (what we actually changed) and the retrieved sources
(which aren't pinned - Tavily can return different results run to run,
per F-012). A pass or fail in that setup would be ambiguous - impossible
to tell whether the result came from the fix working or from different
input data this time.

Calling judge_claim() directly with fixed, hand-written claim/source pairs
removed every variable except the one being tested. This also cost 3 Groq
calls instead of a full 20-question pipeline run - cheaper AND more
conclusive at the same time. When verifying a fix, isolate the smallest
unit that actually changed, don't re-run the whole system around it.

The overcorrection check (Case 2: a FALSE absence claim, source DOES
contain the info) mattered more than the direct case (Case 1: a TRUE
absence claim now correctly SUPPORTED). Case 1 only proves the fix does
something. Case 2 proves the fix didn't break the judge's ability to
still catch a real contradiction - it's the harder direction to get right,
and the one most likely to silently break if the prompt instruction was
worded too broadly.

## "Confirmed" is not the same as "verified" — a file-state bug, not a code bug

A prompt-fix I made to hallucination_scorer.py was applied against a stale copy of the file — one that never actually received an enum change (JUDGE_ERROR) I had only described in chat text, never applied with the file-editing tools. The result: source_quality_scorer.py depended on ClaimVerdict.JUDGE_ERROR existing, and it silently didn't, because a described change and an applied change are not the same thing, and nobody re-verified the file's actual state before trusting it. The fix wasn't just restoring the missing code - it was recognizing the mistake as a process failure: "I said it's done" (from either party) is a claim, not a fact, until the actual file is re-read and confirmed. This is the exact same discipline as re-viewing a file before editing it with str_replace - stale assumptions about state cause bugs that have nothing to do with logic errors.

## Defensive validation should happen per-item, not per-batch, when one bad item shouldn't sink the rest

results = [SearchResult(**r) for r in raw_results] looks clean but has a real production flaw: if any ONE of five results is malformed (Tavily occasionally returns broken redirect URLs instead of real ones), the entire list comprehension throws, and the whole search() call fails - losing four good results because of one bad one. Wrapping each individual construction in its own try/except, logging and dropping the bad one, means a single malformed record degrades gracefully (4 results instead of 5) instead of catastrophically (0 results, the whole request fails). This is the same "map the actual API contract" principle from Day 1, applied to fault tolerance instead of schema design: assume the API will occasionally send something malformed, and don't let one bad record take down everything else in the same response.
