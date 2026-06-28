# INTERVIEW_PREP.md — Deep Research Agent

## Data Modeling & Validation

Question:
"Why would you use Pydantic validators over a plain dataclass when modeling data from an external API?"

Why they're asking:
Big tech systems ingest data from dozens of external APIs. Interviewers want to know if you think about failure at the boundary, not after bad data has already corrupted three downstream services.

Weak answer:
"Pydantic has built-in validation and dataclasses don't, so Pydantic is safer."

Strong answer:
"Pydantic and dataclasses look similar on the surface — both give you typed fields — but they solve different problems. A dataclass declares shape. It does not enforce truth. If an external API returns a relevance score of 1.5, or an empty string where content is required, a dataclass stores it without complaint. That bad value now carries the same trust as good data, and it propagates into ranking logic, prompts, or eval scoring before anyone notices.

I modeled Tavily's search results as a Pydantic model specifically because field_validators let me encode the actual constraints of the API, not just its shape. The score field has a validator that raises ValueError outside [0.0, 1.0] — Tavily's documented range — and the content field rejects empty strings, because an empty snippet flowing into a generation prompt produces a confidently-empty citation later. Validating at the boundary means every downstream module — ranking, generation, eval — can assume the data it receives is already correct. That assumption is what lets the rest of the codebase stay simple.

[YOUR: add the actual number of malformed responses you've seen from Tavily/Groq so far, if any — concrete data makes this answer land harder in an interview]"

---

Question:
"You're ingesting data from a third-party API. The API sometimes omits fields it claims are always present. How do you model this defensively, and where does validation belong in the pipeline?"

Why they're asking:
Every production system at scale eventually hits an API that lies about its schema. They want to see if you validate at the boundary (correct) or deep inside business logic (expensive mistake).

Weak answer:
"I'd wrap the API call in a try/except and skip records that error out."

Strong answer:
"Catching exceptions around the API call handles crashes, but it doesn't handle the more common case — fields silently missing rather than the whole call failing. The right fix is at the schema level, not the try/except level.

In this project, Tavily's docs claim every result has a title, url, content, and score, but published_date is documented as optional and frequently absent — Wikipedia results, scraped pages, and doc sites routinely omit it. I modeled it as Optional[str] = None, which maps what the API actually does rather than what its documentation promises. That single line means the model instantiates cleanly when the field is missing, instead of raising a ValidationError that crashes the whole batch over one optional field.

Where this gets defensive is the required fields. If content comes back empty, that's not a documented optional case — it's a sign something upstream is broken. The validator on content raises ValueError immediately rather than letting an empty string flow into a generation prompt, where it would silently produce a citation with nothing behind it. Validation belongs exactly at the ingestion boundary — the moment external data becomes an object in your system — because every layer after that should be able to trust the shape and quality of what it's handed.

[YOUR: note any field where you discovered the real API behavior didn't match the documented behavior — interviewers respond well to a specific example]"

---

Question:
"What is the difference between `Optional[str]` and `Optional[str] = None` in Pydantic v2, and when does it matter?"

Why they're asking:
This is a common footgun. They want to know if you've actually hit this bug or if you just read the docs.

Weak answer:
"Optional[str] just means the field is optional."

Strong answer:
"That's the trap, actually — Optional[str] alone does not make a field optional in Pydantic v2. It only tells the type system the field can hold None as a value; you'd still have to pass something — even explicitly None — when constructing the model. The field becomes truly non-required only with Optional[str] = None, where the default value is what lets you omit the field entirely.

I caught this distinction directly while modeling published_date on a SearchResult class. The first instinct is to write Optional[str] and assume that's enough — it reads like 'this is optional' in plain English. It isn't, until the default is attached. Getting this wrong in a real ingestion pipeline means a field documented as 'sometimes absent' raises a ValidationError on every record that omits it, which is the opposite of defensive modeling — you've built a validator that crashes on the exact case it was supposed to handle gracefully.

[YOUR: if you've hit this specific bug while building — a required-looking Optional field crashing unexpectedly — describe what broke and how you found it]"

---

Question:
"A third-party API adds a new field you haven't modeled. How does Pydantic handle it, and what's the right production strategy?"

Why they're asking:
Upstream API drift is inevitable at scale. They want to know if you've thought about schema evolution beyond "it works today."

Weak answer:
"Pydantic ignores extra fields by default, so it just works."

Strong answer:
"Pydantic v2's default behavior — extra='ignore' — does mean the model instantiates cleanly when an API adds a field you haven't seen before. That's convenient, but 'it just works' is the wrong takeaway, because it also means you have zero visibility into the fact that the API changed underneath you.

The strategy I'd use — and the one I documented as a trade-off in this project — is environment-dependent strictness. In staging, set extra='forbid' so any new field the API starts sending raises immediately, during testing, where you have time to evaluate whether it matters. In production, stay with extra='ignore' so an unexpected field doesn't take the whole service down, but log model_extra whenever it's non-empty so you have an observability signal that schema drift occurred, even though nothing crashed.

The failure mode this prevents: an API silently adds a field that actually matters — say, an 'is_paywalled' flag — and your system keeps working, technically, while quietly degrading because you're ignoring information you should be using. Silent schema drift doesn't look like a bug. It looks like nothing happened, which is exactly why it's dangerous.

[YOUR: if Tavily or Groq's response schema has changed since you started this project, describe what changed and whether your extra-field strategy caught it]"

## API Design & Protocol Literacy

Question:
"Your API's JSON response renders correctly in most clients but is corrupted in one. The bytes you sent are correct. What's wrong, and whose responsibility is it to fix?"

Why they're asking:
Distinguishes engineers who understand the wire protocol from those who only understand the happy path.

Weak answer:
"I'd tell the user to change their console or client settings."

Strong answer:
"The instinct to blame the client is understandable but backwards. I hit this exact bug — a FastAPI endpoint returning text with a degree symbol, and a Windows PowerShell client rendering it as 'Â°' instead of '°'. The bytes leaving the server were correct UTF-8 the entire time. The corruption happened because the Content-Type header didn't declare a charset, and PowerShell's HTTP client fell back to decoding the body as Latin-1 in that case — each multi-byte UTF-8 sequence got split into two separate Latin-1 characters.

Telling every client to configure itself correctly doesn't scale — you don't control every client that will ever call your API. The fix belongs on the server: declare the charset explicitly in the Content-Type header instead of relying on a default that not every HTTP client agrees on. An unspecified encoding is an implicit contract, and implicit contracts are exactly the kind of thing that breaks on the client you didn't test against. I fixed it with a custom JSONResponse subclass that sets charset=utf-8 explicitly as the app's default response class — one line, and it stops being a client-dependent guessing game.

[YOUR: confirm whether the fix resolved it cleanly when you retested with the original PowerShell client]"

## Testing & Measurement Philosophy

Question:
"Should test/eval data have the same validation rigor as production data?"

Why they're asking:
Junior engineers often treat test data as inherently safe since "it's just for testing." Senior engineers know a bug in your eval set is a bug in your understanding of your own system — and it's worse than a production bug because it silently corrupts every decision you make based on its numbers.

Weak answer:
"Test data doesn't need the same rigor since it's not user-facing."

Strong answer:
"It's tempting to think test data is lower stakes because no real user ever sees it directly. That's backwards — a bug in your eval set doesn't just fail quietly, it corrupts every decision you make using its numbers, and you have no way to notice because the numbers still look like numbers.

I saw a documented version of exactly this failure in the curriculum I'm working from: an earlier version of the eval harness set correctness=None for hedge-style answers — cases where the system correctly refused to answer an unanswerable question — and the scoring logic silently skipped any record with correctness=None instead of treating it as a result. That meant roughly 30% of the gold dataset was invisible to every metric, every week, without a single error or warning. The eval harness looked healthy. It wasn't measuring a third of what it claimed to.

The fix I applied in my own gold dataset was the same principle I used for the production SearchResult model: schema validation at the boundary. A field_validator now rejects a fixed gold_answer on any question tagged volatile or analytical, because pinning an exact answer to a fact that changes, or to a question with no single correct answer, is exactly the kind of bug that looks fine until you check it against reality months later. Test data is a measurement instrument. An unvalidated measurement instrument is worse than no instrument, because it gives you false confidence instead of an honest 'I don't know.'

[YOUR: note how many of your 20 gold questions are tagged volatile or analytical, and what percentage that represents — concrete numbers make this answer land harder]"

## Pyhton Internals

Question:
"What's the difference between running a script directly versus running it with python -m, and why does it matter for imports?"

Why they're asking:
This is a real, recurring Python internals question at mid-to-senior backend interviews. It separates engineers who've actually hit an import error and diagnosed it from those who've only memorized "use -m sometimes."

Weak answer:
"You use -m when imports aren't working."

Strong answer:
"It comes down to what gets added to sys.path. When you run a script directly with python some_script.py, Python adds the script's own containing folder to sys.path — not the project root, unless the script happens to live there.

I hit this directly: a validation script living inside an evals/ package needed to import a sibling module, evals.models. Running it directly put evals/ itself on sys.path, so Python looked for an 'evals' folder inside evals/ and failed with ModuleNotFoundError. Running it with python -m evals.validate_gold_dataset instead starts sys.path from the project root and executes the script as part of the evals package — so the sibling import resolves correctly. The fix isn't in the import statement at all. It's in how the interpreter is invoked. A script at the project root never hits this, because its own folder already is the root.

[YOUR: note any other place in your codebase where this distinction will matter again as the project grows — e.g. if you add a CLI entrypoint or test runner inside a package folder]"

## Evaluation & LLM-System Design

Question:
"How do you validate that an LLM's citations in a RAG-style answer are trustworthy? What's the difference between checking that a citation exists versus checking that it's correct?"

Why they're asking:
This tests whether you understand the gap between structural validation (cheap, deterministic) and semantic validation (expensive, requires judgment) in LLM evaluation — and whether you default to the easy check while believing you've solved the hard problem.

Weak answer:
"I'd check that the citation numbers match real sources in the context."

Strong answer:
"That's necessary but it's a much narrower check than it sounds like. A citation pointing to a real source only proves the model didn't invent a source number out of thin air — it says nothing about whether that source actually supports the specific claim sitting next to it. A model under token pressure will frequently grab the nearest plausible-looking source index and attach it to a claim that source doesn't actually back. That passes a structural check and fails a real one.

I built the structural layer first deliberately — a regex-based scorer that flags any citation index outside the valid source range. It's free, deterministic, and catches a real failure mode: fabricated citation numbers. But I scoped it explicitly as NOT verifying semantic alignment, because that's a fundamentally different and harder problem — it requires either an LLM-as-judge comparing the claim text against the actual source content, or human annotation, and it comes with its own calibration problem: judges need to agree with each other and with ground truth, which is where things like inter-rater agreement metrics come in. Building the cheap structural check first, and being honest about what it does and doesn't catch, prevented me from shipping a scorer that looked rigorous but only ever caught the easiest 20% of citation failures.

[YOUR: once you build the semantic alignment scorer, add the percentage of citations that passed the structural check but failed semantic alignment — that gap is the most interesting number in this whole system]"

## Schema Design Judgment

Question:
"You discover your data actually has a second, independent dimension that your current schema doesn't capture — it's currently just implied by another field. Do you add a new field now, or leave it inferred?"

Why they're asking:
This tests schema evolution judgment, not schema design knowledge. Both
"always add the field for correctness" and "never add fields speculatively"
are wrong defaults — the skill is knowing which side of that line you're on
for a specific case, with specific evidence.

Weak answer:
"I'd add the field now so the schema is correct and complete."

Strong answer:
"It depends on whether I have a concrete case that needs the dimension
expressed independently, not just a theoretical one. In a gold dataset I
built, I noticed 'volatility' (does the answer change over time) and
'agreement' (does everyone converge on one answer right now) are actually
two separate axes — but my schema only captures agreement implicitly,
through one category (analytical) that happens to always have low
agreement. Adding an explicit 'agreement' field would be more 'correct' on
paper. But with only 5 categories and 20 questions, every category that
currently needs low agreement is the same category that needs it — there's
no real case yet where I need to vary agreement independently of category.

Adding the field now would be exactly the kind of complexity the project's
own engineering principle warns against: complexity must be earned by a
measured need, not added because it's theoretically more complete. I
documented the gap in TRADEOFFS.md with the specific future case that would
force the change — a category that's both volatile and low-agreement, like
predicting next week's interest rate decision — so the decision is
reversible and the trigger condition is explicit, not just deferred and
forgotten.

[YOUR: if you ever do hit a question that needs both axes independently,
note what it was and whether the TRADEOFFS.md entry correctly predicted it]"
