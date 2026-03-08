from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI YouTube Remix Generator API"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    database_url: str = "postgresql://user:password@localhost:5432/remixdb"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    quick_output_root: str = "/app/outputs"
    youtube_client_secrets_path: str | None = None
    youtube_token_path: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        if value.lstrip().startswith("["):
            return [item.strip() for item in json.loads(value) if str(item).strip()]
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
