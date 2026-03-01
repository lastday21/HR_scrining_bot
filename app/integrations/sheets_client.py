from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from app.core.errors import SheetsWriteError
from app.core.settings import Settings
from app.domain.models import CandidateSubmission, LlmScore

gspread_module: Any | None = None
value_input_option_user_entered: Any = None

try:
    import gspread as _gspread
    from gspread.utils import ValueInputOption
except ModuleNotFoundError:  # pragma: no cover - optional during local test runs.
    pass
else:
    gspread_module = _gspread
    value_input_option_user_entered = ValueInputOption.user_entered

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UpsertOperation:
    action: str
    row_number: int | None
    row_values: list[str]


@dataclass(slots=True)
class ScreeningStats:
    total_candidates: int
    average_total: float


@dataclass(slots=True)
class TopCandidate:
    first_name: str
    last_name: str
    telegram_username: str
    contacts: str
    total_score: int


def normalize_tg_id(value: str | int) -> str:
    return str(value).strip()


def build_sheet_row(
    *,
    row_id: int,
    submission: CandidateSubmission,
    score: LlmScore,
) -> list[str]:
    answers = submission.answers + [""] * max(0, 7 - len(submission.answers))
    return [
        str(row_id),
        submission.last_name,
        submission.first_name,
        submission.middle_name,
        normalize_tg_id(submission.telegram_user_id),
        submission.telegram_username or "",
        submission.contacts or "",
        submission.started_at.isoformat(),
        *answers[:7],
        str(score.criterion_1),
        str(score.criterion_2),
        str(score.criterion_3),
        str(score.result),
        score.model_explanation,
        submission.project_link or "",
    ]


def plan_upsert(
    existing_rows: list[list[str]],
    submission: CandidateSubmission,
    score: LlmScore,
) -> UpsertOperation:
    target_tg_id = normalize_tg_id(submission.telegram_user_id)
    max_id = 0

    for index, row in enumerate(existing_rows, start=2):
        if row and row[0].isdigit():
            max_id = max(max_id, int(row[0]))
        row_tg_id = row[4].strip() if len(row) > 4 else ""
        if row_tg_id == target_tg_id:
            row_id = int(row[0]) if row and row[0].isdigit() else index - 1
            return UpsertOperation(
                action="update",
                row_number=index,
                row_values=build_sheet_row(row_id=row_id, submission=submission, score=score),
            )

    new_id = max_id + 1 if max_id else 1
    return UpsertOperation(
        action="append",
        row_number=None,
        row_values=build_sheet_row(row_id=new_id, submission=submission, score=score),
    )


class GoogleSheetsClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def upsert_submission(self, submission: CandidateSubmission, score: LlmScore) -> None:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.sheets_retry_attempts + 1):
            started_at = time.perf_counter()
            try:
                await asyncio.to_thread(self._upsert_submission_sync, submission, score)
            except Exception as error:
                last_error = error
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                logger.warning(
                    "Google Sheets attempt failed",
                    extra={
                        "telegram_user_id": submission.telegram_user_id,
                        "submission_id": submission.submission_id,
                        "state": "completed",
                        "step": "sheets_upsert",
                        "attempt": attempt,
                        "duration_ms": duration_ms,
                        "success": False,
                    },
                )
                if attempt == self.settings.sheets_retry_attempts:
                    break
                await asyncio.sleep(float(attempt))
                continue

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "Google Sheets upsert completed",
                extra={
                    "telegram_user_id": submission.telegram_user_id,
                    "submission_id": submission.submission_id,
                    "state": "completed",
                    "step": "sheets_upsert",
                    "attempt": attempt,
                    "duration_ms": duration_ms,
                    "success": True,
                },
            )
            return

        raise SheetsWriteError("Google Sheets write failed after retries.") from last_error

    async def get_screening_stats(self) -> ScreeningStats:
        rows = await asyncio.to_thread(self._get_all_candidate_rows_sync)
        totals = [candidate.total_score for candidate in self._extract_completed_candidates(rows)]
        if not totals:
            return ScreeningStats(total_candidates=0, average_total=0.0)
        return ScreeningStats(
            total_candidates=len(totals),
            average_total=sum(totals) / len(totals),
        )

    async def get_top_candidates(self, limit: int = 3) -> list[TopCandidate]:
        rows = await asyncio.to_thread(self._get_all_candidate_rows_sync)
        candidates = sorted(
            self._extract_completed_candidates(rows),
            key=lambda candidate: candidate.total_score,
            reverse=True,
        )
        return candidates[:limit]

    def _upsert_submission_sync(self, submission: CandidateSubmission, score: LlmScore) -> None:
        worksheet = self._open_worksheet()
        all_values = worksheet.get_all_values()
        existing_rows = all_values[1:] if all_values else []
        operation = plan_upsert(existing_rows, submission, score)

        if operation.action == "update" and operation.row_number is not None:
            worksheet.update(
                range_name=f"A{operation.row_number}:U{operation.row_number}",
                values=[operation.row_values],
            )
            return

        worksheet.append_row(
            operation.row_values,
            value_input_option=value_input_option_user_entered,
        )

    def _get_all_candidate_rows_sync(self) -> list[list[str]]:
        worksheet = self._open_worksheet()
        all_values = worksheet.get_all_values()
        return all_values[1:] if all_values else []

    def _open_worksheet(self) -> Any:
        if gspread_module is None or value_input_option_user_entered is None:
            raise SheetsWriteError("gspread is not installed.")

        client = gspread_module.service_account(
            filename=self.settings.google_service_account_json_path
        )
        spreadsheet = client.open_by_key(self.settings.google_spreadsheet_id)
        return spreadsheet.worksheet(self.settings.google_worksheet_title)

    def _extract_completed_candidates(self, rows: list[list[str]]) -> list[TopCandidate]:
        candidates: list[TopCandidate] = []
        for row in rows:
            candidate = self._parse_completed_candidate(row)
            if candidate is not None:
                candidates.append(candidate)
        return candidates

    def _parse_completed_candidate(self, row: list[str]) -> TopCandidate | None:
        if len(row) < 21:
            return None
        if not row[14].strip():
            return None
        try:
            criterion_1 = int(row[15])
            criterion_2 = int(row[16])
            criterion_3 = int(row[17])
        except ValueError:
            return None
        return TopCandidate(
            first_name=row[2].strip(),
            last_name=row[1].strip(),
            telegram_username=row[5].strip() or "-",
            contacts=row[6].strip() or "-",
            total_score=criterion_1 + criterion_2 + criterion_3,
        )
