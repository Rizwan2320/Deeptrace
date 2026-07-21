"""
task_compliance_scorer.py

LLM-as-judge for Task Compliance: does the report actually cover what
the query asked for. This is the STATIC-LLM version specified for Day 4 —
the judge infers essential points from the query itself, in the same
call that checks coverage against the report. The stronger AGENTIC
version (independently research the query, build a grounded yes/no
checklist BEFORE seeing the report) is the documented upgrade path, not
built here — see PHASE_1_EXIT_CRITERIA.md.

Unlike presentation_scorer.py, this judge DOES see the query — coverage
can't be judged against nothing. It still never sees the generator's own
reasoning, only the final report text, same isolation principle as every
other judge in this project.
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


class TaskComplianceJudgment(BaseModel):
    status: JudgeStatus
    coverage_score: Optional[int] = None
    covered_points: list[str] = []
    missing_points: list[str] = []
    reasoning: Optional[str] = None
    error_detail: Optional[str] = None

    @field_validator("coverage_score")
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
    def scored_requires_score(self):
        if self.status == JudgeStatus.SCORED and self.coverage_score is None:
            raise ValueError("status=scored but coverage_score is missing")
        return self


JUDGE_PROMPT = """\
You are a strict task-compliance judge. Your ONLY job is to determine
whether a REPORT actually covers what the QUERY asked for.

Do NOT judge writing quality, factual correctness, or citation quality —
those are evaluated separately. Judge coverage only: given what a complete
answer to this query would need to address, how much of that does the
report actually address?

Steps:
1. Identify the essential points a complete, correct answer to the QUERY
   would need to cover. Keep this to the 2-5 points that actually matter —
   do not pad with trivial sub-points.
2. Check the REPORT against each point: covered or missing.
3. Score coverage from 1 (misses nearly everything essential) to 5
   (covers everything essential).

For missing_points specifically: name the actual missing content, at the
same level of specificity as covered_points. Do NOT use a generic
positional placeholder like "the second reason" or "the third factor" —
if you can identify what the missing point actually is (and you should
be able to, since you identified the full list of essential points in
step 1), state it directly, e.g. "improvement in cell efficiency" or
"battery chemistry and degradation rate", not "the remaining factor".

A report that correctly states it cannot answer the query, when the query
is genuinely unanswerable or the available sources are explicitly
described as insufficient, should score 5 — a correct refusal is full
compliance, not a coverage failure.

Respond with ONLY valid JSON, no other text, no markdown formatting:
{{"coverage_score": <1-5>, "covered_points": ["<point>", ...], "missing_points": ["<specific missing point>", ...], "reasoning": "<one or two sentences>"}}

QUERY: {query}

REPORT: {report_text}

JSON response:"""


def judge_task_compliance(query: str, report_text: str) -> TaskComplianceJudgment:
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{
            "role": "user",
            "content": JUDGE_PROMPT.format(query=query, report_text=report_text),
        }],
        temperature=0.0,
    )
    raw = response.choices[0].message.content

    try:
        data = json.loads(raw)
        return TaskComplianceJudgment(status=JudgeStatus.SCORED, **data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error({
            "event": "judge_parse_failure",
            "raw_response": raw,
            "error": str(e),
        })
        return TaskComplianceJudgment(
            status=JudgeStatus.JUDGE_ERROR,
            error_detail=f"Parse failed: {str(e)[:100]}",
        )