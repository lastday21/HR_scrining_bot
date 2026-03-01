from datetime import UTC, datetime

from app.domain.models import CandidateSubmission, LlmScore
from app.integrations.sheets_client import GoogleSheetsClient, build_sheet_row, plan_upsert


def build_submission(telegram_user_id: str = "123") -> CandidateSubmission:
    return CandidateSubmission(
        submission_id="submission-1",
        telegram_user_id=telegram_user_id,
        telegram_username="@ivanov",
        started_at=datetime(2026, 2, 28, tzinfo=UTC),
        last_name="Иванов",
        first_name="Иван",
        middle_name="Иванович",
        contacts="+79991234567",
        answers=[f"answer {index}" for index in range(1, 8)],
        project_link="https://github.com/example/project",
    )


def build_score() -> LlmScore:
    return LlmScore(
        criterion_1=30,
        criterion_2=25,
        criterion_3=20,
        result=75,
        model_explanation="Strong candidate",
    )


def test_plan_upsert_updates_existing_row_without_changing_id() -> None:
    operation = plan_upsert(
        existing_rows=[
            ["5", "Old", "Name", "", "123", "2026-02-27T12:00:00+00:00"],
        ],
        submission=build_submission(),
        score=build_score(),
    )

    assert operation.action == "update"
    assert operation.row_number == 2
    assert operation.row_values[0] == "5"
    assert operation.row_values[4] == "123"


def test_plan_upsert_appends_new_row_with_next_id() -> None:
    operation = plan_upsert(
        existing_rows=[
            ["1", "Old", "Name", "", "555", "2026-02-27T12:00:00+00:00"],
            ["7", "Old", "Name", "", "999", "2026-02-27T12:00:00+00:00"],
        ],
        submission=build_submission("123"),
        score=build_score(),
    )

    assert operation.action == "append"
    assert operation.row_number is None
    assert operation.row_values[0] == "8"


def test_build_sheet_row_has_fixed_column_count() -> None:
    row = build_sheet_row(row_id=1, submission=build_submission(), score=build_score())

    assert len(row) == 21
    assert row[5] == "@ivanov"
    assert row[6] == "+79991234567"
    assert row[18] == "75"
    assert row[20] == "https://github.com/example/project"


def test_parse_completed_candidate_requires_filled_q7_and_numeric_scores() -> None:
    client = GoogleSheetsClient.__new__(GoogleSheetsClient)

    assert client._parse_completed_candidate(["1"] * 14) is None

    missing_q7_row = ["1"] * 21
    missing_q7_row[14] = ""
    assert client._parse_completed_candidate(missing_q7_row) is None

    non_numeric_scores_row = ["1"] * 21
    non_numeric_scores_row[15] = "bad"
    assert client._parse_completed_candidate(non_numeric_scores_row) is None

    row = [
        "1",
        "Иванов",
        "Иван",
        "Иванович",
        "123",
        "@ivanov",
        "+79991234567",
        "2026-02-28T00:00:00+00:00",
        "a1",
        "a2",
        "a3",
        "a4",
        "a5",
        "a6",
        "a7",
        "30",
        "25",
        "20",
        "75",
        "Strong candidate",
        "https://github.com/example/project",
    ]
    candidate = client._parse_completed_candidate(row)

    assert candidate is not None
    assert candidate.first_name == "Иван"
    assert candidate.total_score == 75
