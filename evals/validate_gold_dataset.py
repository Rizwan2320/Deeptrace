"""
validate_gold_dataset.py

Loads evals/gold_dataset.json, validates every entry against the GoldQuestion
schema, and checks the dataset matches its own design intent (8 simple factual,
4 multi-hop, 4 adversarial, 4 analytical). Run this any time the gold dataset
changes — before trusting a single eval number that comes out of it.

Run from the project root as a module, not as a script:
    uv run python -m evals.validate_gold_dataset

(Running it directly as `python evals/validate_gold_dataset.py` puts evals/
on sys.path instead of the project root, and the `from evals.models import`
line below will fail with ModuleNotFoundError. The -m flag runs it as part
of the evals package, with the project root on sys.path instead.)
"""

import json
import sys
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from evals.models import GoldQuestion, QueryCategory, Volatility

GOLD_DATASET_PATH = Path("evals/gold_dataset.json")

EXPECTED_DISTRIBUTION = {
    QueryCategory.SIMPLE_FACTUAL: 8,
    QueryCategory.MULTI_HOP: 4,
    QueryCategory.ADVERSARIAL: 4,
    QueryCategory.ANALYTICAL: 4,
}


def load_raw_dataset(path: Path) -> list[dict]:
    if not path.exists():
        print(f"ERROR: {path} does not exist.")
        sys.exit(1)

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_entries(raw_entries: list[dict]) -> list[GoldQuestion]:
    validated: list[GoldQuestion] = []
    errors: list[str] = []

    for i, entry in enumerate(raw_entries):
        entry_id = entry.get("id", f"<missing id at index {i}>")
        try:
            validated.append(GoldQuestion(**entry))
        except ValidationError as e:
            errors.append(f"  [{entry_id}] {e}")

    if errors:
        plural = "y" if len(errors) == 1 else "ies"
        print(f"FAILED: {len(errors)} entr{plural} failed schema validation:\n")
        print("\n".join(errors))
        sys.exit(1)

    return validated


def check_dataset_integrity(questions: list[GoldQuestion]) -> None:
    ids = [q.id for q in questions]

    duplicate_ids = [
        id_
        for id_, count in Counter(ids).items()
        if count > 1
    ]

    if duplicate_ids:
        print(f"FAILED: duplicate IDs found: {duplicate_ids}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Category distribution
    # ------------------------------------------------------------------

    category_counts = Counter(q.category for q in questions)

    print("Category distribution:")

    mismatched: list[QueryCategory] = []

    for category in QueryCategory:
        count = category_counts.get(category, 0)
        expected = EXPECTED_DISTRIBUTION.get(category, 0)

        if count != expected:
            mismatched.append(category)

        flag = "" if count == expected else f"  <-- expected {expected}"
        print(f"  {category.value:<16} {count}{flag}")

    # ------------------------------------------------------------------
    # Volatility distribution
    # ------------------------------------------------------------------

    volatility_counts = Counter(q.volatility for q in questions)

    print("\nVolatility distribution:")

    for volatility in Volatility:
        count = volatility_counts.get(volatility, 0)
        print(f"  {volatility.value:<16} {count}")

    # ------------------------------------------------------------------
    # Gold answer statistics
    # ------------------------------------------------------------------

    no_fixed_answer = sum(
        1 for q in questions
        if q.gold_answer is None
    )

    volatile_reason = sum(
        1
        for q in questions
        if q.gold_answer is None
        and q.volatility in {Volatility.VOLATILE, Volatility.FAST_CHANGING}
    )

    analytical_reason = sum(
        1
        for q in questions
        if q.gold_answer is None
        and q.category == QueryCategory.ANALYTICAL
    )

    print(f"\nQuestions without a fixed gold_answer: {no_fixed_answer}")
    print(f"  - because volatile/fast-changing: {volatile_reason}")
    print(f"  - because analytical (no single answer exists): {analytical_reason}")

    if mismatched:
        names = [c.value for c in mismatched]
        print(f"\nWARNING: category counts don't match expected distribution: {names}")
        print("This isn't a schema failure — it's a deviation from your stratification plan.")


def main() -> None:
    raw_entries = load_raw_dataset(GOLD_DATASET_PATH)
    questions = validate_entries(raw_entries)

    print(f"PASSED: all {len(questions)} entries are schema-valid.\n")

    check_dataset_integrity(questions)


if __name__ == "__main__":
    main()