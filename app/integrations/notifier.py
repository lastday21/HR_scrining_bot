from __future__ import annotations

from aiogram import Bot

from app.core.settings import Settings
from app.domain.models import CandidateSubmission, LlmScore


class TelegramNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_hot_candidate(self, score: LlmScore) -> bool:
        return score.total_score >= self.settings.hot_candidate_threshold

    async def send_hot_candidate(
        self,
        bot: Bot,
        submission: CandidateSubmission,
        score: LlmScore,
    ) -> None:
        await bot.send_message(
            self.settings.admin_chat_id,
            self._build_hot_candidate_message(submission, score),
        )

    async def send_sheets_fallback(
        self,
        bot: Bot,
        submission: CandidateSubmission,
        score: LlmScore,
        reason: str,
    ) -> None:
        await bot.send_message(
            self.settings.admin_chat_id,
            self._build_fallback_message(submission, score, reason),
        )

    async def send_processing_error(
        self,
        bot: Bot,
        submission: CandidateSubmission,
        reason: str,
    ) -> None:
        await bot.send_message(
            self.settings.admin_chat_id,
            self._build_processing_error_message(submission, reason),
        )

    def _build_hot_candidate_message(
        self,
        submission: CandidateSubmission,
        score: LlmScore,
    ) -> str:
        return (
            "Hot candidate\n"
            f"submission_id: {submission.submission_id}\n"
            f"telegram_user_id: {submission.telegram_user_id}\n"
            f"telegram_username: {submission.telegram_username or '-'}\n"
            f"candidate: {submission.last_name} {submission.first_name} {submission.middle_name}\n"
            f"contacts: {submission.contacts or '-'}\n"
            f"project_link: {submission.project_link or '-'}\n"
            f"score: {score.criterion_1}/{score.criterion_2}/{score.criterion_3}\n"
            f"total: {score.total_score}\n"
            f"explanation: {score.model_explanation}"
        )

    def _build_fallback_message(
        self,
        submission: CandidateSubmission,
        score: LlmScore,
        reason: str,
    ) -> str:
        answers = "\n".join(
            f"Q{index}: {answer}" for index, answer in enumerate(submission.answers, start=1)
        )
        return (
            "Sheets fallback\n"
            f"reason: {reason}\n"
            f"submission_id: {submission.submission_id}\n"
            f"telegram_user_id: {submission.telegram_user_id}\n"
            f"telegram_username: {submission.telegram_username or '-'}\n"
            f"name: {submission.last_name} {submission.first_name} {submission.middle_name}\n"
            f"contacts: {submission.contacts or '-'}\n"
            f"project_link: {submission.project_link or '-'}\n"
            f"scores: {score.criterion_1}, {score.criterion_2}, {score.criterion_3}\n"
            f"total: {score.total_score}\n"
            f"explanation: {score.model_explanation}\n"
            f"answers:\n{answers}"
        )

    def _build_processing_error_message(
        self,
        submission: CandidateSubmission,
        reason: str,
    ) -> str:
        return (
            "Processing error\n"
            f"submission_id: {submission.submission_id}\n"
            f"telegram_user_id: {submission.telegram_user_id}\n"
            f"telegram_username: {submission.telegram_username or '-'}\n"
            f"reason: {reason}"
        )
