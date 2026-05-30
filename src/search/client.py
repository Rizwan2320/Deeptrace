import httpx
import logging
import os
import time
from dotenv import load_dotenv
from src.search.models import SearchResult

load_dotenv()

logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search(query: str, max_results: int = 5) -> list[SearchResult]:
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY not set in environment")

    start = time.perf_counter()

    response = httpx.post(
        TAVILY_API_URL,
        json={"query": query, "max_results": max_results},
        headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
        timeout=10.0,
    )
    response.raise_for_status()

    elapsed_ms = (time.perf_counter() - start) * 1000
    raw_results = response.json().get("results", [])

    results = [SearchResult(**r) for r in raw_results]

    logger.info({
        "event": "search_complete",
        "query": query,
        "result_count": len(results),
        "latency_ms": round(elapsed_ms, 2),
    })

    return results