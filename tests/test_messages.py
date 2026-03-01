from app.bot.messages import STATS_EMPTY_MESSAGE, build_top3_message


def test_build_top3_message_returns_empty_state_message() -> None:
    assert build_top3_message([]) == STATS_EMPTY_MESSAGE


def test_build_top3_message_adds_header_and_preserves_lines() -> None:
    message = build_top3_message([
        "Иван - Иванов - @ivanov - +79991234567 - 87 баллов",
        "Петр - Петров - - - 75 баллов",
    ])

    assert message.startswith("Топ-3 кандидата:\nИмя - Фамилия - Telegram - Контакты - Баллы\n")
    assert "Иван - Иванов - @ivanov - +79991234567 - 87 баллов" in message
    assert "Петр - Петров - - - 75 баллов" in message
