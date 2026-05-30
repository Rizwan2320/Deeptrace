# test_search.py (delete after confirming)
import logging
logging.basicConfig(level=logging.INFO)

from src.search.client import search

results = search("What is the current population of Tokyo?", max_results=3)
for r in results:
    print(r.title, "|", r.score, "|", r.content[:80])