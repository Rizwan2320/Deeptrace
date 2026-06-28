"""
validate_gold_dataset.py

Loads evals/gold_dataset.json, validates every entry against the GoldQuestion
schema, and checks the dataset matches its own design intent (4 questions per
category, unique IDs). Run this any time the gold dataset changes — before
trusting a single eval number that comes out of it.

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
EXPECTED_PER_CATEGORY = 4


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
    duplicate_ids = [id_ for id_, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        print(f"FAILED: duplicate IDs found: {duplicate_ids}")
        sys.exit(1)

    category_counts = Counter(q.category for q in questions)
    print("Category distribution:")
    mismatched = []
    for category in QueryCategory:
        count = category_counts.get(category, 0)
        if count != EXPECTED_PER_CATEGORY:
            mismatched.append(category)
        flag = "" if count == EXPECTED_PER_CATEGORY else f"  <-- expected {EXPECTED_PER_CATEGORY}"
        print(f"  {category.value:<16} {count}{flag}")

    volatility_counts = Counter(q.volatility for q in questions)
    print("\nVolatility distribution:")
    for volatility, count in volatility_counts.items():
        print(f"  {volatility.value:<16} {count}")

    no_fixed_answer = sum(1 for q in questions if q.gold_answer is None)
    volatile_reason = sum(
        1 for q in questions
        if q.gold_answer is None and q.volatility == Volatility.VOLATILE
    )
    analytical_reason = sum(
        1 for q in questions
        if q.gold_answer is None and q.category == QueryCategory.ANALYTICAL
    )
    print(f"\nQuestions without a fixed gold_answer: {no_fixed_answer}")
    print(f"  - because volatile (answer would go stale): {volatile_reason}")
    print(f"  - because analytical (no single answer exists): {analytical_reason}")

    if mismatched:
        names = [c.value for c in mismatched]
        print(f"\nWARNING: category counts don't match the {EXPECTED_PER_CATEGORY}-per-category design: {names}")
        print("This isn't a schema failure — it's a deviation from your own stratification plan.")


def main() -> None:
    raw_entries = load_raw_dataset(GOLD_DATASET_PATH)
    questions = validate_entries(raw_entries)
    print(f"PASSED: all {len(questions)} entries are schema-valid.\n")
    check_dataset_integrity(questions)


if __name__ == "__main__":
    main()