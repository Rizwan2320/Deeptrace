from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # API keys
    tavily_api_key: str
    groq_api_key: str

    # Search config
    search_max_results: int = 5
    search_timeout_seconds: float = 10.0

    # Generation config
    groq_model: str = "llama-3.3-70b-versatile"
    generation_temperature: float = 0.1

    # Eval config
    eval_results_dir: str = "eval/results"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()