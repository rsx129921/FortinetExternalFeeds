from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    refresh_interval_hours: int = 24
    listen_host: str = "0.0.0.0"
    listen_port: int = 8080
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    api_token: str | None = None


settings = Settings()
