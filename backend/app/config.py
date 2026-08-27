from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "RepoInsight"
    app_env: str = "development"
    app_port: int = 8000
    debug: bool = True

    database_url: str
    redis_url: str

    github_token: str

    gemini_api_key_project_a: str
    gemini_api_key_project_b: str
    groq_api_key: str

    secret_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()