"""
presentation_scorer.py

LLM-as-judge for Presentation Quality: clarity, organisation, fluency.
Judges the REPORT TEXT alone — no query, no sources, no generator reasoning.
Correctness, coverage, and citation faithfulness are separate verticals;
leaking any of them in here would blur exactly the "fluent liar" signal
this vertical exists to isolate (see ENGINEERING_PRINCIPLES.md, #1).

Cheapest vertical to score: single LLM call, no external tools, no
claim extraction, no multi-source resolution.
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

JUDGE_PROMPT_VERSION = "v1.1"


class JudgeStatus(str, Enum):
    SCORED = "scored"
    JUDGE_ERROR = "judge_error"


class PresentationJudgment(BaseModel):
    status: JudgeStatus
    clarity_score: Optional[int] = None
    clarity_reasoning: Optional[str] = None
    organisation_score: Optional[int] = None
    organisation_reasoning: Optional[str] = None
    fluency_score: Optional[int] = None
    fluency_reasoning: Optional[str] = None
    error_detail: Optional[str] = None

    @field_validator("clarity_score", "organisation_score", "fluency_score")
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
    def scored_requires_all_dimensions(self):
        if self.status == JudgeStatus.SCORED:
            missing = [
                name for name, val in [
                    ("clarity_score", self.clarity_score),
                    ("organisation_score", self.organisation_score),
                    ("fluency_score", self.fluency_score),
                ] if val is None
            ]
            if missing:
                raise ValueError(f"status=scored but missing: {missing}")
        return self


JUDGE_PROMPT = """\
You are a strict writing-quality judge. Your ONLY job is to evaluate a
REPORT TEXT along three independent dimensions of presentation quality.

Do NOT judge whether the report is factually correct, complete, or
well-cited — those are evaluated separately. Judge only the surface
quality of the writing itself.

Score each dimension from 1 (very poor) to 5 (excellent). Each dimension
must be judged independently — do not let one dimension's flaws lower
another dimension's score:

- clarity: is it unambiguous and readable by a non-expert, with jargon
  explained or avoided where unnecessary? Ignore sentence ordering and
  ignore repetition — judge only whether individual statements are
  understandable in isolation.
- organisation: are the facts grouped and sequenced in a logical order
  (e.g. one topic fully covered before moving to the next)? Ignore
  whether sentences are repetitive or padded — a report can restate
  itself and still be in the correct order; that is a fluency problem,
  not an organisation problem.
- fluency: is the prose natural and well-formed, without padding,
  repetition, or the same claim restated for length? Ignore whether
  topics are sequenced logically — judge only the sentence-level
  writing quality, not the ordering of ideas.

Respond with ONLY valid JSON, no other text, no markdown formatting:
{{"clarity_score": <1-5>, "clarity_reasoning": "<one sentence>", "organisation_score": <1-5>, "organisation_reasoning": "<one sentence>", "fluency_score": <1-5>, "fluency_reasoning": "<one sentence>"}}

REPORT TEXT: {report_text}

JSON response:"""


def judge_presentation(report_text: str) -> PresentationJudgment:
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
        return PresentationJudgment(status=JudgeStatus.SCORED, **data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error({
            "event": "judge_parse_failure",
            "raw_response": raw,
            "error": str(e),
        })
        return PresentationJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail=f"Parse failed: {str(e)[:100]}",
        )