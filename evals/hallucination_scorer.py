"""
hallucination_scorer.py

LLM-as-judge for semantic citation alignment. Judges whether a single CLAIM
is supported by a single SOURCE TEXT — strictly against the source, not
against real-world truth. This is the atomic unit. Running it across every
claim/citation pair in a full answer is the next layer, built separately.

Three verdicts, not two — see TRADEOFFS.md / LEARNINGS.md for why collapsing
"insufficient evidence" into either supported or unsupported corrupts the
hallucination rate in opposite directions.
"""

import json
import logging
from enum import Enum

from groq import Groq
from pydantic import BaseModel

from src.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
client = Groq(api_key=settings.groq_api_key)

JUDGE_PROMPT_VERSION = "v1.1"


class ClaimVerdict(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    JUDGE_ERROR = "judge_error"


class ClaimJudgment(BaseModel):
    verdict: ClaimVerdict
    reasoning: str


JUDGE_PROMPT = """\
You are a strict fact-checking judge. Your ONLY job is to determine whether
a CLAIM is supported by a specific SOURCE TEXT.

Critical rule: judge ONLY against the source text provided. Do NOT use your
own knowledge of whether the claim is true in the real world. A claim can be
true in reality and still be unsupported if this specific source doesn't say it.

Special case — ABSENCE claims: some claims assert that the source does NOT
contain certain information (e.g. "the source does not mention the founder").
For these claims, check whether the source text genuinely lacks that
information. If it does genuinely lack it, the absence claim is SUPPORTED —
the claim is correctly describing what is and isn't in the source. Do not
mark an absence claim UNSUPPORTED just because the source contains other,
unrelated information. Only mark it UNSUPPORTED if the source actually DOES
contain the information the claim says is missing.

Classify the claim into exactly one of three categories:
- "supported": the source text directly confirms this claim
- "unsupported": the source text contradicts this claim, or says nothing related to it
- "insufficient_evidence": the source text is topically related but too vague, partial, or ambiguous to confirm or deny the claim

Respond with ONLY valid JSON, no other text, no markdown formatting:
{{"verdict": "supported" | "unsupported" | "insufficient_evidence", "reasoning": "<one sentence>"}}

CLAIM: {claim}

SOURCE TEXT: {source_text}

JSON response:"""


def judge_claim(claim: str, source_text: str) -> ClaimJudgment:
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(claim=claim, source_text=source_text),
        }],
        temperature=0.0,
    )
    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        return ClaimJudgment(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error({
            "event": "judge_parse_failure",
            "claim": claim,
            "raw_response": raw,
            "error": str(e),
        })
        return ClaimJudgment(
            verdict=ClaimVerdict.JUDGE_ERROR,
            reasoning=f"Parse failed: {str(e)[:100]}",
        )