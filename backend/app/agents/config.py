from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """
    Agents get their own settings loader, separate from backend/app/core/config.py.
    This keeps `agents/` genuinely standalone — importable by the FastAPI
    backend now, or by a separate worker process later (Phase 2), without
    ever reaching into backend/-specific code.
    """
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "llama-3.3-70b-versatile"


settings = AgentSettings()