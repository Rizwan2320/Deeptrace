"""
analytical_depth_scorer.py

LLM-as-judge for Analytical Depth: reasoning, synthesis, and conflict
resolution beyond fact-aggregation (QUALITY.md's own definition, not an
invented rubric). Static-LLM version per Day 4 — the agentic version
(tool-using evaluator, independently verifies reasoning against external
sources) is the documented upgrade path curriculum says substantially
outperforms this one. Treat these numbers with extra skepticism relative
to presentation/task-compliance scores until that upgrade is earned.

Report-only input, same isolation as presentation_scorer.py. No blanket
"correct refusal = full score" rule (unlike task_compliance_scorer.py) —
a hedge only scores well here if it demonstrates actual reasoning, not
just for refusing to answer.
"""

import json
import logging
from enum import Enum
from typing import Optional

from groq import Groq
from pydantic import BaseModel, field_validator, model_validator

from src.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
client = Groq(api_key=settings.groq_api_key)

JUDGE_PROMPT_VERSION = "v1.0"


class JudgeStatus(str, Enum):
    SCORED = "scored"
    JUDGE_ERROR = "judge_error"


class AnalyticalDepthJudgment(BaseModel):
    status: JudgeStatus
    reasoning_score: Optional[int] = None
    reasoning_reasoning: Optional[str] = None
    synthesis_score: Optional[int] = None
    synthesis_reasoning: Optional[str] = None
    conflict_present: Optional[bool] = None
    conflict_resolution_score: Optional[int] = None
    conflict_resolution_reasoning: Optional[str] = None
    error_detail: Optional[str] = None

    @field_validator("reasoning_score", "synthesis_score", "conflict_resolution_score")
    @classmethod
    def clamp_score(cls, v):
        if v is None:
            return v
        if v < 1:
            logger.warning({"event": "score_clamped", "original": v, "clamped_to": 1})
            return 1
        if v > 5:
            logger.warning({"event": "score_clamped", "original": v, "clamped_to": 5})
            return 5
        return v

    @model_validator(mode="after")
    def scored_requires_consistent_fields(self):
        if self.status != JudgeStatus.SCORED:
            return self

        missing = [
            name for name, val in [
                ("reasoning_score", self.reasoning_score),
                ("synthesis_score", self.synthesis_score),
                ("conflict_present", self.conflict_present),
            ] if val is None
        ]
        if missing:
            raise ValueError(f"status=scored but missing: {missing}")

        if self.conflict_present and self.conflict_resolution_score is None:
            raise ValueError(
                "conflict_present=True but conflict_resolution_score is missing"
            )
        if not self.conflict_present and self.conflict_resolution_score is not None:
            raise ValueError(
                "conflict_present=False but conflict_resolution_score was set "
                "— should be null when there is nothing to resolve"
            )
        return self


JUDGE_PROMPT = """\
You are a strict analytical-depth judge. Your ONLY job is to evaluate
whether a REPORT reasons over its facts, rather than merely listing them.

Do NOT judge factual correctness, citation quality, coverage of the
query, or writing style — those are evaluated separately.

Score two dimensions from 1 (very poor) to 5 (excellent), always:
- reasoning: does the report explain WHY or HOW, draw out implications,
  or does it only state WHAT happened with no explanation?
- synthesis: does the report connect multiple facts into one coherent
  conclusion or insight, or does it read as an unconnected list of
  separate facts placed next to each other?

Conflict resolution is CONDITIONAL, not always scored:
First decide conflict_present — does the report itself contain or imply
conflicting information (different figures, disagreeing sources,
competing explanations for the same thing)?
- If conflict_present is false: do not score conflict_resolution at all.
  Set conflict_resolution_score to null. This is not a penalty — most
  reports have nothing to resolve, and that is not a flaw.
- If conflict_present is true: score conflict_resolution 1-5 — does the
  report surface and address the tension explicitly (e.g. explain why
  the figures differ), or does it silently pick one side, or present
  contradictory information with no comment at all?

Respond with ONLY valid JSON, no other text, no markdown formatting:
{{"reasoning_score": <1-5>, "reasoning_reasoning": "<one sentence>", "synthesis_score": <1-5>, "synthesis_reasoning": "<one sentence>", "conflict_present": true|false, "conflict_resolution_score": <1-5 or null>, "conflict_resolution_reasoning": "<one sentence or null>"}}

REPORT TEXT: {report_text}

JSON response:"""


def judge_analytical_depth(report_text: str) -> AnalyticalDepthJudgment:
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(report_text=report_text),
        }],
        temperature=0.0,
    )
    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        return AnalyticalDepthJudgment(status=JudgeStatus.SCORED, **data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error({
            "event": "judge_parse_failure",
            "raw_response": raw,
            "error": str(e),
        })
        return AnalyticalDepthJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail=f"Parse failed: {str(e)[:100]}",
        )