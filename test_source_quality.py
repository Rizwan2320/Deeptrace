# test_source_quality.py (throwaway)
from evals.source_quality_scorer import score_source_quality
from src.search.client import search
from src.generation.generator import generate

query = "What is the current price of Bitcoin?"
results = search(query, max_results=5)
answer = generate(query, results)

score = score_source_quality(query, answer, results)
print(f"Faithfulness rate: {score.faithfulness_rate}")
print(f"Judge error rate: {score.judge_error_rate}")
print(f"Citation validity: {score.citation_validity.is_valid}")
print(f"\nPer-claim breakdown:")
for c in score.claim_results:
    print(f"  [{c.verdict.value}] {c.claim}")
    print(f"    sources: {c.source_indices} | reasoning: {c.reasoning}")