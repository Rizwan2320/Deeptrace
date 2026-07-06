"""
run_eval.py

Runs the full pipeline (search -> generate -> score_source_quality) across
every question in evals/gold_dataset.json. Writes one result file with
per-question detail plus an aggregate summary.

This is the first REAL baseline run — not a spot-check on 1-2 queries.
Expected to surface failure modes in categories the scorer hasn't seen yet:
multi-hop, adversarial (refusals), analytical (no fixed answer, often no
numbered citations at all).

Survives individual question failures — a rate limit or API error on
question 14 should not lose the results already computed for questions
1-13. Each question is wrapped independently; failures are recorded, not
fatal.

Run from project root:
    uv run python -m evals.run_eval
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from src.search.client import search
from src.generation.generator import generate, PROMPT_VERSION
from evals.source_quality_scorer import score_source_quality
from evals.models import GoldQuestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GOLD_DATASET_PATH = Path("evals/gold_dataset.json")
RESULTS_DIR = Path("evals/results")
RUN_NAME = "week1b_baseline"


def load_gold_dataset() -> list[GoldQuestion]:
    with GOLD_DATASET_PATH.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [GoldQuestion(**entry) for entry in raw]


def run_single_question(question: GoldQuestion) -> dict:
    try:
        pipeline_start = time.perf_counter()
        results = search(question.query, max_results=5)
        answer = generate(question.query, results)
        pipeline_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)

        scoring_start = time.perf_counter()
        score = score_source_quality(question.query, answer, results)
        scoring_ms = round((time.perf_counter() - scoring_start) * 1000, 2)

        return {
            "id": question.id,
            "query": question.query,
            "category": question.category.value,
            "volatility": question.volatility.value,
            "status": "success",
            "answer": answer,
            "source_count": len(results),
            "citation_validity": score.citation_validity.is_valid,
            "faithfulness_rate": score.faithfulness_rate,
            "zero_claims": score.zero_claims,
            "judge_error_rate": score.judge_error_rate,
            "total_claims": score.total_claims,
            "claim_results": [c.model_dump() for c in score.claim_results],
            "pipeline_latency_ms": pipeline_ms,
            "scoring_latency_ms": scoring_ms,
        }
    except Exception as e:
        logger.error({
            "event": "question_failed",
            "id": question.id,
            "query": question.query,
            "error": str(e),
        })
        return {
            "id": question.id,
            "query": question.query,
            "category": question.category.value,
            "volatility": question.volatility.value,
            "status": "error",
            "error": str(e),
        }


def summarize(question_results: list[dict]) -> dict:
    successful = [r for r in question_results if r["status"] == "success"]
    failed = [r for r in question_results if r["status"] == "error"]

    scored = [r for r in successful if r["faithfulness_rate"] is not None]
    zero_claim_count = sum(1 for r in successful if r["faithfulness_rate"] is None)

    if scored:
        avg_faithfulness = round(
            sum(r["faithfulness_rate"] for r in scored) / len(scored), 4
        )
    else:
        avg_faithfulness = None

    if successful:
        avg_judge_error = round(
            sum(r["judge_error_rate"] for r in successful) / len(successful), 4
        )
        citation_valid_count = sum(1 for r in successful if r["citation_validity"])
        avg_pipeline_latency = round(
            sum(r["pipeline_latency_ms"] for r in successful) / len(successful), 2
        )
        avg_scoring_latency = round(
            sum(r["scoring_latency_ms"] for r in successful) / len(successful), 2
        )
    else:
        avg_judge_error = avg_pipeline_latency = avg_scoring_latency = 0.0
        citation_valid_count = 0

    by_category: dict[str, list[float]] = {}
    for r in scored:
        by_category.setdefault(r["category"], []).append(r["faithfulness_rate"])

    faithfulness_by_category = {
        cat: round(sum(rates) / len(rates), 4) for cat, rates in by_category.items()
    }

    return {
        "total_questions": len(question_results),
        "successful": len(successful),
        "failed": len(failed),
        "failed_ids": [r["id"] for r in failed],
        "avg_faithfulness_rate": avg_faithfulness,
        "scored_answer_count": len(scored),
        "zero_claim_count": zero_claim_count,
        "avg_judge_error_rate": avg_judge_error,
        "citation_validity_pass_count": citation_valid_count,
        "avg_pipeline_latency_ms": avg_pipeline_latency,  # what a real user waits for
        "avg_scoring_latency_ms": avg_scoring_latency,    # offline eval-only cost, never in prod request path
        "faithfulness_by_category": faithfulness_by_category,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    questions = load_gold_dataset()

    print(f"Running eval across {len(questions)} questions...\n")

    question_results = []
    for i, question in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {question.id}: {question.query[:60]}...")
        result = run_single_question(question)
        question_results.append(result)
        status_symbol = "OK" if result["status"] == "success" else "FAILED"
        print(f"    -> {status_symbol}")

    summary = summarize(question_results)

    output = {
        "run_name": RUN_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "summary": summary,
        "results": question_results,
    }

    output_path = RESULTS_DIR / f"{RUN_NAME}.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Results written to {output_path}")
    print(f"\nSummary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()



    