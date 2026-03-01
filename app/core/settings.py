from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    redis_url: str = Field(alias="REDIS_URL")
    admin_chat_id: int = Field(alias="ADMIN_CHAT_ID")
    admin_user_id: int = Field(alias="ADMIN_USER_ID")
    google_spreadsheet_id: str = Field(alias="GOOGLE_SPREADSHEET_ID")
    google_service_account_json_path: str = Field(alias="GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
    google_worksheet_title: str = Field(default="Sheet1", alias="GOOGLE_WORKSHEET_TITLE")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_model_uri: str = Field(alias="LLM_MODEL_URI")
    llm_api_url: str = Field(
        default="https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        alias="LLM_API_URL",
    )
    log_level: str = "INFO"
    redis_draft_ttl_seconds: int = 7 * 24 * 60 * 60
    llm_request_timeout_seconds: float = 30.0
    sheets_request_timeout_seconds: float = 30.0
    llm_retry_attempts: int = 3
    sheets_retry_attempts: int = 3
    hot_candidate_threshold: int = Field(default=70, alias="HOT_CANDIDATE_THRESHOLD")
    screening_questions: tuple[str, ...] = (
        (
            "Расскажи про последний проект или задачу, где ты реально использовал AI "
            "в разработке: что делал, какой получился результат."
        ),
        "Как выглядит твой рабочий процесс с AI по шагам: от задачи до готового результата?",
        "Как ты проверяешь качество результата, который помог сделать AI?",
        (
            "Что ты делаешь, когда AI сгенерировал решение, которое почти работает: "
            "как дебажишь и как взаимодействуешь с ИИ?"
        ),
        (
            "Как ты формулируешь запросы к AI, чтобы он выдавал нормальный результат: "
            "что обязательно пишешь? Приведи один пример своего промпта."
        ),
        (
            "Примерно какая доля работы у тебя делается с AI в процентах и "
            "за счет чего это видно на практике?"
        ),
        (
            "За счет чего ты обычно добиваешься требуемого результата для бизнеса, "
            "когда делаешь AI-first решение?"
        ),
    )

    @field_validator("google_service_account_json_path")
    @classmethod
    def resolve_google_service_account_json_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute():
            return str(path)
        return str((PROJECT_ROOT / path).resolve())

    def is_admin_user(self, telegram_user_id: int | None) -> bool:
        return telegram_user_id == self.admin_user_id


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
