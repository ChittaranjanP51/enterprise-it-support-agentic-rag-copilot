from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    pinecone_api_key: str = ""
    pinecone_index: str = "it-support-kb"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    tavily_api_key: str = ""

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    top_k: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
