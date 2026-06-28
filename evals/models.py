from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator


class QueryCategory(str, Enum):
    SIMPLE_FACTUAL = "simple_factual"
    MULTI_HOP = "multi_hop"
    RECENCY = "recency"
    ADVERSARIAL = "adversarial"
    ANALYTICAL = "analytical"


class Volatility(str, Enum):
    STABLE = "stable"      # answer does not change over time
    VOLATILE = "volatile"  # answer can change day to day or month to month


class GoldQuestion(BaseModel):
    id: str
    query: str
    category: QueryCategory
    volatility: Volatility
    gold_answer: Optional[str] = None
    expected_behavior: str
    notes: Optional[str] = None

    @field_validator("gold_answer")
    @classmethod
    def no_fixed_answer_for_volatile_or_analytical(cls, v, info):
        category = info.data.get("category")
        volatility = info.data.get("volatility")
        if v is not None and (volatility == Volatility.VOLATILE or category == QueryCategory.ANALYTICAL):
            raise ValueError(
                "Volatile or analytical questions must not have a fixed gold_answer. "
                "Use expected_behavior instead — fixed answers go stale or have no single truth."
            )
        return v