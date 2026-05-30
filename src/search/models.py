from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional

class SearchResult(BaseModel):
    url: HttpUrl
    title: str
    content: str
    score: float
    raw_content: Optional[str] = None
    published_date: Optional[str] = None

    @field_validator("score")
    @classmethod
    def score_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"score {v} is outside expected range [0.0, 1.0]")
        return v

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v