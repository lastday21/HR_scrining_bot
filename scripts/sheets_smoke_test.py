from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings
from app.domain.models import CandidateSubmission, LlmScore
from app.integrations.sheets_client import GoogleSheetsClient


async def main() -> None:
    settings = get_settings()
    client = GoogleSheetsClient(settings)
    submission = CandidateSubmission(
        submission_id=str(uuid4()),
        telegram_user_id=f"smoke-{uuid4()}",
        telegram_username="@smoke_test",
        started_at=datetime.now(UTC),
        last_name="Smoke",
        first_name="Test",
        middle_name="",
        contacts="+79991234567",
        answers=[f"answer {index}" for index in range(1, 8)],
        project_link="https://github.com/example/example",
    )
    score = LlmScore(
        criterion_1=30,
        criterion_2=25,
        criterion_3=18,
        result=73,
        model_explanation="Smoke test row",
    )
    await client.upsert_submission(submission, score)
    print("sheets smoke ok")


if __name__ == "__main__":
    asyncio.run(main())
