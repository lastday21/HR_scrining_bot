from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandidateDraft(BaseModel):
    submission_id: str = Field(default_factory=lambda: str(uuid4()))
    telegram_user_id: str
    telegram_username: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    contacts: str | None = None
    answers: list[str] = Field(default_factory=list)
    project_link: str | None = None
    q_index: int = 0
    sheets_written: bool = False
    llm_error: bool = False
    llm_error_message: str | None = None

    def to_submission(self) -> CandidateSubmission:
        if len(self.answers) != 7:
            msg = "Candidate draft must have exactly 7 answers before submission."
            raise ValueError(msg)
        return CandidateSubmission(
            submission_id=self.submission_id,
            telegram_user_id=self.telegram_user_id,
            telegram_username=self.telegram_username,
            started_at=self.started_at,
            last_name=self.last_name or "",
            first_name=self.first_name or "",
            middle_name=self.middle_name or "",
            contacts=self.contacts,
            answers=self.answers,
            project_link=self.project_link,
            sheets_written=self.sheets_written,
            llm_error=self.llm_error,
            llm_error_message=self.llm_error_message,
        )


class CandidateSubmission(BaseModel):
    submission_id: str
    telegram_user_id: str
    telegram_username: str | None = None
    started_at: datetime
    last_name: str
    first_name: str
    middle_name: str
    contacts: str | None = None
    answers: list[str]
    project_link: str | None = None
    sheets_written: bool = False
    llm_error: bool = False
    llm_error_message: str | None = None


class LlmScore(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    criterion_1: int = 0
    criterion_2: int = 0
    criterion_3: int = 0
    result: int = 0
    model_explanation: str = ""

    @model_validator(mode="after")
    def validate_result(self) -> "LlmScore":
        expected_result = self.criterion_1 + self.criterion_2 + self.criterion_3
        if self.result != expected_result:
            msg = "LLM result must equal the sum of all criteria."
            raise ValueError(msg)
        return self

    @property
    def total_score(self) -> int:
        return self.result
