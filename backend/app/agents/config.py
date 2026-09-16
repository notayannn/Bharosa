from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-120b"


settings = AgentSettings()