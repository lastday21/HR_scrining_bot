from __future__ import annotations

import re
from urllib.parse import urlparse

from app.core.errors import ValidationError

NO_MIDDLE_NAME_TEXT = "Нет отчества"
DECLINE_TO_ANSWER_TEXT = "Не хочу отвечать"

NAME_ALLOWED_PATTERN = re.compile(r"^[A-Za-zА-Яа-яЁё]+(?:[ '-][A-Za-zА-Яа-яЁё]+)*$")
REJECTED_ANSWER_VALUES = {
    "",
    DECLINE_TO_ANSWER_TEXT.lower(),
    "пропуск",
    "skip",
    "n/a",
}


def normalize_person_name(value: str) -> str:
    normalized = value.strip().replace("—", "-").replace("–", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized


def validate_person_name(value: str) -> str:
    normalized = normalize_person_name(value)
    if not 2 <= len(normalized) <= 60:
        raise ValidationError("Name length must be between 2 and 60 characters.")
    if not NAME_ALLOWED_PATTERN.fullmatch(normalized):
        raise ValidationError("Name contains unsupported characters.")
    return normalized


def validate_optional_middle_name(value: str) -> str:
    normalized = normalize_person_name(value)
    if normalized in {"", "-", NO_MIDDLE_NAME_TEXT}:
        return ""
    return validate_person_name(normalized)


def validate_project_link(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError("Project link is required.")
    if "://" not in normalized:
        normalized = f"https://{normalized}"

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationError("Project link must include a scheme and host.")
    if not parsed.path or parsed.path == "/":
        raise ValidationError("Project link must include a path after the host.")
    return normalized


def normalize_phone_number(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ValidationError("Contacts are required.")

    digits = re.sub(r"\D+", "", raw)
    if digits.startswith("8") and len(digits) == 11:
        digits = f"7{digits[1:]}"
    if digits.startswith("7") and len(digits) == 11:
        return f"+{digits}"
    raise ValidationError("Phone number must be in +7XXXXXXXXXX or 8XXXXXXXXXX format.")


def validate_answer(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    if normalized.lower() in REJECTED_ANSWER_VALUES or len(normalized) < 10:
        raise ValidationError("Answer is too short.")
    return normalized
