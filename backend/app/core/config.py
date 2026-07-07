from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Engineering Command Center"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default=["http://localhost:3000"])

    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None

    # Embedding
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 50
    embedding_task_type_doc: str = "retrieval_document"
    embedding_task_type_query: str = "retrieval_query"

    # Knowledge base
    knowledge_collection: str = "engineering_knowledge"
    chunk_max_chars: int = 4000
    chunk_overlap_chars: int = 200
    chunk_max_lines: int = 80
    chunk_overlap_lines: int = 15

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    secret_key: str = "change-me-in-production"
    allowed_email_domain: str = "yourdomain.com"
    frontend_url: str = "http://localhost:3000"
    jwt_expire_hours: int = 8

    # GitHub
    github_token: str
    github_org: str
    # Optional prefix filter — if set, only repos whose names start with this prefix are scanned.
    # Useful when a GitHub org mixes unrelated product repos (e.g. "cinema-*" scans only cinema repos).
    github_repo_prefix: str | None = None

    # Repository scanner
    repos_base_path: str = "/data/repos"
    repo_include_patterns: list[str] = Field(default=["*"])
    repo_exclude_patterns: list[str] = Field(default=["experimental-*", "poc-*"])
    # Max parallel clone/sync workers
    repo_sync_concurrency: int = 4

    # Scheduler — automatic sync + incremental index
    scheduler_enabled: bool = True
    # How often to run the sync+index cycle (in hours). Default: every 2 hours.
    scheduler_interval_hours: int = 2
    # Index state file path — tracks last indexed commit SHA per repo
    index_state_path: str = "index_state.json"

    # Admin credentials (configurable via env vars)
    admin_email: str = "admin@yourdomain.com"
    admin_password: str = "admin@1234"

    # Usage tracking DB path
    usage_db_path: str = "usage.db"

    # AWS
    aws_region: str = "ap-south-1"

    @field_validator("repo_include_patterns", "repo_exclude_patterns", "allowed_origins", mode="before")
    @classmethod
    def parse_str_list(cls, v: str | list[str]) -> list[str]:
        # pydantic-settings v2 passes list fields as already-parsed lists when the env
        # value is a valid JSON array (e.g. ["a","b"]). The str branch handles the legacy
        # comma-separated format for backwards compatibility.
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
