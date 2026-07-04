from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator


class QueryCategory(str, Enum):
    SIMPLE_FACTUAL = "simple_factual"
    MULTI_HOP = "multi_hop"
    ADVERSARIAL = "adversarial"
    ANALYTICAL = "analytical"


class Volatility(str, Enum):
    IMMUTABLE = "immutable"        # physically/logically cannot change
    SLOW_CHANGING = "slow_changing"  # changes on yearly timescales
    FAST_CHANGING = "fast_changing"  # changes on monthly timescales
    VOLATILE = "volatile"            # changes on daily/hourly timescales


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
        if v is not None and (
            volatility == Volatility.VOLATILE or
            volatility == Volatility.FAST_CHANGING or
            category == QueryCategory.ANALYTICAL
        ):
            raise ValueError(
                "Volatile, fast-changing, or analytical questions must not "
                "have a fixed gold_answer. Use expected_behavior instead."
            )
        return v