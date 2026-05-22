from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # LLM (DeepSeek, OpenAI-compatible)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-v4-flash"

    # Volcengine TTS (火山引擎语音合成)
    volc_app_id: str = ""
    volc_access_token: str = ""
    volc_tts_api_key: str = ""
    volc_tts_voice_type: str = "zh_female_vv_uranus_bigtts"

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
