from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    llm_provider: str = "groq"
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    model_name: str = "openai/gpt-oss-120b"
    ollama_base_url: str = "http://ollama:11434"
    database_url: str = "mysql+pymysql://atlas:change_me_local_only@localhost:3306/project_atlas"
    readonly_database_url: str = ""
    vector_db_url: str = "http://localhost:6333"
    api_key: str = ""
    log_level: str = "INFO"
    confidence_threshold: float = 0.70
    request_timeout_seconds: int = 25
    max_input_chars: int = 4000
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size_chars: int = 1200
    chunk_overlap_chars: int = 160
    llm_input_cost_per_1k: float | None = None
    llm_output_cost_per_1k: float | None = None

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        provider = value.strip().lower()
        if provider not in {"openai", "groq", "gemini", "ollama"}:
            raise ValueError("LLM_PROVIDER must be one of: openai, groq, gemini, ollama")
        return provider

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        model = value.strip()
        if not model:
            raise ValueError("MODEL_NAME must not be empty")
        return model


settings = Settings()
