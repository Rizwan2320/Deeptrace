import logging
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.search.client import search
from src.generation.generator import generate
from src.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
app = FastAPI(title="Deep Research Agent", version="0.1.0")


class ResearchRequest(BaseModel):
    query: str
    max_results: int = 5


class ResearchResponse(BaseModel):
    query: str
    answer: str
    source_count: int
    latency_ms: float
    prompt_version: str


@app.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest) -> ResearchResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    start = time.perf_counter()

    results = search(request.query, max_results=request.max_results)

    if not results:
        raise HTTPException(status_code=502, detail="Search returned no results")

    answer = generate(request.query, results)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info({
        "event": "research_complete",
        "query": request.query,
        "source_count": len(results),
        "latency_ms": elapsed_ms,
    })

    return ResearchResponse(
        query=request.query,
        answer=answer,
        source_count=len(results),
        latency_ms=elapsed_ms,
        prompt_version="v1.0",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}