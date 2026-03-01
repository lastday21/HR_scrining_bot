from __future__ import annotations

import logging

from aiogram import Bot

from app.core.errors import LlmRequestError, SheetsWriteError, ValidationError
from app.core.settings import Settings
from app.domain.models import CandidateDraft, CandidateSubmission, LlmScore
from app.domain.validators import (
    DECLINE_TO_ANSWER_TEXT,
    normalize_phone_number,
    validate_answer,
    validate_optional_middle_name,
    validate_person_name,
    validate_project_link,
)
from app.integrations.llm_client import YandexLlmClient
from app.integrations.notifier import TelegramNotifier
from app.integrations.sheets_client import GoogleSheetsClient, ScreeningStats, TopCandidate
from app.storage.redis_storage import RedisDraftStorage

logger = logging.getLogger(__name__)


class ScreeningService:
    def __init__(
        self,
        *,
        settings: Settings,
        storage: RedisDraftStorage,
        llm_client: YandexLlmClient,
        sheets_client: GoogleSheetsClient,
        notifier: TelegramNotifier,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.llm_client = llm_client
        self.sheets_client = sheets_client
        self.notifier = notifier

    async def get_draft(self, telegram_user_id: int) -> CandidateDraft | None:
        return await self.storage.get_draft(telegram_user_id)

    async def restart_draft(
        self,
        telegram_user_id: int,
        telegram_username: str | None = None,
    ) -> CandidateDraft:
        draft = CandidateDraft(
            telegram_user_id=str(telegram_user_id),
            telegram_username=self._normalize_username(telegram_username),
        )
        await self.storage.save_draft(draft)
        logger.info(
            "Draft restarted",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "restart",
                "success": True,
            },
        )
        return draft

    async def save_last_name(
        self,
        telegram_user_id: int,
        value: str,
        telegram_username: str | None = None,
    ) -> CandidateDraft:
        draft = await self._require_draft(telegram_user_id)
        draft.telegram_username = self._normalize_username(telegram_username)
        draft.last_name = validate_person_name(value)
        await self.storage.save_draft(draft)
        logger.info(
            "Last name saved",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "last_name",
                "success": True,
            },
        )
        return draft

    async def save_first_name(
        self,
        telegram_user_id: int,
        value: str,
        telegram_username: str | None = None,
    ) -> CandidateDraft:
        draft = await self._require_draft(telegram_user_id)
        draft.telegram_username = self._normalize_username(telegram_username)
        draft.first_name = validate_person_name(value)
        await self.storage.save_draft(draft)
        logger.info(
            "First name saved",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "first_name",
                "success": True,
            },
        )
        return draft

    async def save_middle_name(
        self,
        telegram_user_id: int,
        value: str,
        telegram_username: str | None = None,
    ) -> CandidateDraft:
        draft = await self._require_draft(telegram_user_id)
        draft.telegram_username = self._normalize_username(telegram_username)
        draft.middle_name = validate_optional_middle_name(value)
        await self.storage.save_draft(draft)
        logger.info(
            "Middle name saved",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "middle_name",
                "success": True,
            },
        )
        return draft

    async def save_contacts_text(
        self,
        telegram_user_id: int,
        value: str,
        telegram_username: str | None = None,
    ) -> CandidateDraft:
        draft = await self._require_draft(telegram_user_id)
        draft.telegram_username = self._normalize_username(telegram_username)
        normalized_text = value.strip()
        if normalized_text.lower() == DECLINE_TO_ANSWER_TEXT.lower():
            draft.contacts = ""
        else:
            draft.contacts = normalize_phone_number(normalized_text)
        await self.storage.save_draft(draft)
        logger.info(
            "Contacts saved",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "contacts",
                "success": True,
            },
        )
        return draft

    async def save_contacts_shared(
        self,
        telegram_user_id: int,
        phone_number: str,
        contact_user_id: int | None,
        telegram_username: str | None = None,
    ) -> CandidateDraft:
        if contact_user_id is not None and contact_user_id != telegram_user_id:
            raise ValidationError("Contact user id does not match sender.")

        draft = await self._require_draft(telegram_user_id)
        draft.telegram_username = self._normalize_username(telegram_username)
        draft.contacts = normalize_phone_number(phone_number)
        await self.storage.save_draft(draft)
        logger.info(
            "Contacts shared",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "contacts_shared",
                "success": True,
            },
        )
        return draft

    async def save_answer(self, telegram_user_id: int, value: str) -> CandidateDraft:
        draft = await self._require_draft(telegram_user_id)
        answer = validate_answer(value)
        if draft.q_index != len(draft.answers):
            draft.q_index = len(draft.answers)
        draft.answers.append(answer)
        draft.q_index = len(draft.answers)
        await self.storage.save_draft(draft)
        logger.info(
            "Screening answer saved",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "draft",
                "step": "question_answer",
                "attempt": draft.q_index,
                "success": True,
            },
        )
        return draft

    async def complete_screening(
        self,
        *,
        telegram_user_id: int,
        project_link_text: str,
        telegram_username: str | None = None,
    ) -> CandidateSubmission:
        draft = await self._require_draft(telegram_user_id)
        draft.telegram_username = self._normalize_username(telegram_username)
        normalized_project_link = project_link_text.strip()
        if normalized_project_link.lower() == DECLINE_TO_ANSWER_TEXT.lower():
            draft.project_link = None
        else:
            draft.project_link = validate_project_link(normalized_project_link)
        await self.storage.save_draft(draft)
        logger.info(
            "Screening completed",
            extra={
                "telegram_user_id": draft.telegram_user_id,
                "submission_id": draft.submission_id,
                "state": "completed",
                "step": "project_link",
                "success": True,
            },
        )
        return draft.to_submission()

    async def process_submission(self, bot: Bot, submission: CandidateSubmission) -> None:
        logger.info(
            "Submission processing started",
            extra={
                "telegram_user_id": submission.telegram_user_id,
                "submission_id": submission.submission_id,
                "state": "completed",
                "step": "process_submission",
                "success": True,
            },
        )
        score = LlmScore(
            criterion_1=0,
            criterion_2=0,
            criterion_3=0,
            result=0,
            model_explanation="LLM scoring was not completed.",
        )
        try:
            score = await self.llm_client.score_submission(
                submission,
                self.settings.screening_questions,
            )
        except LlmRequestError as error:
            submission.llm_error = True
            submission.llm_error_message = str(error)
            score = LlmScore(
                criterion_1=0,
                criterion_2=0,
                criterion_3=0,
                result=0,
                model_explanation="LLM scoring failed; candidate requires manual review.",
            )
            await self._persist_llm_error(submission)
            logger.exception(
                "LLM scoring failed",
                extra={
                    "telegram_user_id": submission.telegram_user_id,
                    "submission_id": submission.submission_id,
                    "state": "completed",
                    "step": "llm_score",
                    "success": False,
                },
            )
            await self.notifier.send_processing_error(bot, submission, f"LLM error: {error}")

        try:
            await self.sheets_client.upsert_submission(submission, score)
        except SheetsWriteError as error:
            logger.exception(
                "Google Sheets write failed",
                extra={
                    "telegram_user_id": submission.telegram_user_id,
                    "submission_id": submission.submission_id,
                    "state": "completed",
                    "step": "sheets_upsert",
                    "success": False,
                },
            )
            await self.notifier.send_sheets_fallback(bot, submission, score, str(error))
            return

        await self.storage.mark_sheets_written(submission.telegram_user_id)
        logger.info(
            "Submission written to Google Sheets",
            extra={
                "telegram_user_id": submission.telegram_user_id,
                "submission_id": submission.submission_id,
                "state": "completed",
                "step": "sheets_written",
                "success": True,
            },
        )
        if self.notifier.is_hot_candidate(score):
            await self.notifier.send_hot_candidate(bot, submission, score)
            logger.info(
                "Hot candidate notification sent",
                extra={
                    "telegram_user_id": submission.telegram_user_id,
                    "submission_id": submission.submission_id,
                    "state": "completed",
                    "step": "hot_candidate_notification",
                    "success": True,
                },
            )

    async def get_screening_stats(self) -> ScreeningStats:
        return await self.sheets_client.get_screening_stats()

    async def get_top_candidates(self) -> list[TopCandidate]:
        return await self.sheets_client.get_top_candidates(limit=3)

    async def _persist_llm_error(self, submission: CandidateSubmission) -> None:
        draft = await self.storage.get_draft(submission.telegram_user_id)
        if draft is None:
            return
        draft.llm_error = submission.llm_error
        draft.llm_error_message = submission.llm_error_message
        await self.storage.save_draft(draft)

    async def _require_draft(self, telegram_user_id: int) -> CandidateDraft:
        draft = await self.storage.get_draft(telegram_user_id)
        if draft is None:
            return await self.restart_draft(telegram_user_id)
        return draft

    def _normalize_username(self, telegram_username: str | None) -> str | None:
        if not telegram_username:
            return None
        return telegram_username if telegram_username.startswith("@") else f"@{telegram_username}"
