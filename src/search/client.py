import httpx
import logging
import time

from src.search.models import SearchResult
from src.config.settings import get_settings

# Module-level initialization.
settings = get_settings()
logger = logging.getLogger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"
TAVILY_API_KEY = settings.tavily_api_key


def search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search using Tavily API and return typed SearchResult objects."""
    start = time.perf_counter()

    response = httpx.post(
        TAVILY_API_URL,
        json={"query": query, "max_results": max_results},
        headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
        timeout=settings.search_timeout_seconds,
    )
    response.raise_for_status()

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Extract raw results
    raw_results = response.json().get("results", [])

    # Defensive check: enforce max_results contract
    if len(raw_results) > max_results:
        logger.warning({
            "event": "search_contract_violation",
            "query": query,
            "requested_max_results": max_results,
            "actual_result_count": len(raw_results),
        })
        raw_results = raw_results[:max_results]

    # Convert to typed models
    results = [SearchResult(**r) for r in raw_results]

    logger.info({
        "event": "search_complete",
        "query": query,
        "result_count": len(results),
        "latency_ms": round(elapsed_ms, 2),
    })

    return results