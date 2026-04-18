from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    base_url: str = "https://meowfacts.herokuapp.com"
    timeout_seconds: int = 10
    max_retries: int = 3
    backoff_factor: float = 0.5
    retry_on_statuses: list[int] = [429, 500, 502, 503, 504]
    facts_per_request: int = 9999
