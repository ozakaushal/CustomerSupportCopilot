from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Atharva ITS Support Copilot"
    environment: str = "development"

    # api keys
    groq_api_key: str = ""
    hf_token: str = ""
    tavily_api_key: str = ""
    pinecone_api_key: str = ""

    # models and pinecone
    chat_model: str = "qwen/qwen3.8-27b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_index: str = "it-support"
    vector_namespace: str = "company_private_kb"

    retrieval_k: int = 4
    max_rewrites: int = 1
    ingest_token: str = ""

    # paths
    chat_log_db: str = str(BASE_DIR / "data" / "chat_log.db")
    upload_dir: str = str(BASE_DIR / "uploads")
    knowledge_dir: str = str(BASE_DIR / "data" / "knowledge")

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")


settings = None


# returns the settings object, reads .env only the first time
def get_settings():
    global settings
    if settings is None:
        settings = Settings()
    return settings
