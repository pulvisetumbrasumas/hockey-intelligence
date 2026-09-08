from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./hockey_intelligence.db"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    ollama_temperature: float = 0.3
    ollama_num_ctx: int = 4096
    ollama_timeout: int = 120

    # NHL Data Sources
    nhl_stats_api_base: str = "https://api.nhle.com/stats/rest/en"
    nhl_web_api_base: str = "https://api-web.nhle.com/v1"

    # Data Seeding
    data_seed_seasons: str = "20232024,20242025"

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def seed_seasons(self) -> list[int]:
        return [int(s.strip()) for s in self.data_seed_seasons.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
