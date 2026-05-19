from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # HeyGen
    heygen_api_key: str = ""

    # Embedding
    embedding_model: str = "text-embedding-3-small"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Paths
    upload_dir: str = "./uploads"
    output_dir: str = "./output"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def upload_abs_path(self) -> Path:
        return Path(self.upload_dir).resolve()

    @property
    def output_abs_path(self) -> Path:
        return Path(self.output_dir).resolve()


settings = Settings()
