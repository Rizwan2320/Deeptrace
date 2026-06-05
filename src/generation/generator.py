import logging
import os
import time
from groq import Groq
from dotenv import load_dotenv
from src.config.settings import get_settings
from src.search.models import SearchResult


settings = get_settings()

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.groq_api_key)

PROMPT_VERSION = "v1.0"

RESEARCH_PROMPT = """\
You are a research assistant. Answer the question using ONLY the sources below.
Cite each claim with [1], [2], etc. matching the source number.
If the sources do not contain enough information to answer, say so explicitly.
Do not use your training knowledge — only what the sources contain.

Sources:
{sources}

Question: {query}

Answer:"""


def format_sources(results: list[SearchResult]) -> str:
    return "\n".join(
        f"[{i+1}] {r.title} ({r.url})\n{r.content}"
        for i, r in enumerate(results)
    )


def generate(query: str, results: list[SearchResult]) -> str:
    sources_text = format_sources(results)
    prompt = RESEARCH_PROMPT.format(sources=sources_text, query=query)

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.generation_temperature,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    answer = response.choices[0].message.content

    logger.info({
        "event": "generation_complete",
        "query": query,
        "prompt_version": PROMPT_VERSION,
        "latency_ms": round(elapsed_ms, 2),
        "input_tokens": response.usage.prompt_tokens,
        "output_tokens": response.usage.completion_tokens,
    })

    return answer