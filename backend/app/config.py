"""Central app configuration, loaded from environment / .env."""

from pathlib import Path
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "production"] = "development"

    google_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"

    # --- Chat model used by the agents ---
    llm_provider: Literal["groq", "gemini"] = "groq"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_reasoning_effort: Literal["low", "medium", "high"] = "low"
    llm_timeout_seconds: int = 40

    github_token: str = ""
    tavily_api_key: str = ""

    chroma_persist_dir: str = str(BASE_DIR / "data" / "chroma")
    knowledge_base_dir: str = str(BASE_DIR / "data" / "knowledge_base")
    seed_on_startup: bool = False

    # --- LLM output handling ---
    llm_output_mode: Literal["structured", "legacy"] = "structured"
    llm_max_attempts: int = 2

    # --- Auth ---
    otp_expire_minutes: int = 10
    resend_api_key: str = ""
    mail_from: str = "Wayfind <onboarding@resend.dev>"
    mail_from_name: str = "Wayfind"
    jwt_secret_key: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    max_upload_mb: int = 5
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_model_name(self) -> str:
        return self.groq_model if self.llm_provider == "groq" else self.gemini_model

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Neon/Render hand out postgres:// or postgresql://; SQLAlchemy needs the driver.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    @model_validator(mode="after")
    def _require_production_settings(self) -> Self:
        if self.environment != "production":
            return self
        problems: list[str] = []
        if not self.google_api_key:
            problems.append("GOOGLE_API_KEY is required")
        if self.llm_provider == "groq" and not self.groq_api_key:
            problems.append("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        if not self.resend_api_key:
            problems.append("RESEND_API_KEY is required (OTP emails)")
        if self.jwt_secret_key == "change-me-in-.env" or len(self.jwt_secret_key) < 32:
            problems.append("JWT_SECRET_KEY must be a random string of 32+ characters")
        if self.database_url.startswith("sqlite"):
            problems.append("DATABASE_URL must point to PostgreSQL in production")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production")
        if any("localhost" in o for o in self.cors_origin_list):
            problems.append("CORS_ORIGINS must not contain localhost in production")
        if problems:
            raise ValueError(
                "Invalid production configuration:\n- " + "\n- ".join(problems)
            )
        return self


settings = Settings()

for d in (settings.chroma_persist_dir, settings.knowledge_base_dir):
    Path(d).mkdir(parents=True, exist_ok=True)
