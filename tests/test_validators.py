import pytest

from app.core.errors import ValidationError
from app.domain.validators import (
    validate_answer,
    validate_optional_middle_name,
    validate_person_name,
    validate_project_link,
    normalize_phone_number,
)


def test_validate_person_name_accepts_supported_chars() -> None:
    assert validate_person_name("  Анна-Мария  ") == "Анна-Мария"
    assert validate_person_name("O'Connor") == "O'Connor"


def test_validate_person_name_rejects_invalid_chars() -> None:
    with pytest.raises(ValidationError):
        validate_person_name("Иван123")


def test_validate_optional_middle_name_supports_missing_value() -> None:
    assert validate_optional_middle_name("Нет отчества") == ""
    assert validate_optional_middle_name("-") == ""
    assert validate_optional_middle_name("") == ""


def test_validate_project_link_accepts_http_and_https() -> None:
    assert validate_project_link("https://example.com/project") == "https://example.com/project"
    assert validate_project_link("http://gitlab.com/group/project") == "http://gitlab.com/group/project"


def test_validate_project_link_adds_https_when_scheme_missing() -> None:
    assert validate_project_link("github.com/test/repo") == "https://github.com/test/repo"


def test_validate_project_link_rejects_host_only_url() -> None:
    with pytest.raises(ValidationError):
        validate_project_link("https://example.com")


def test_validate_project_link_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        validate_project_link("not a link")


def test_normalize_phone_number_accepts_plus7_and_eight_formats() -> None:
    assert normalize_phone_number("+7 (999) 123-45-67") == "+79991234567"
    assert normalize_phone_number("8 999 123-45-67") == "+79991234567"


def test_normalize_phone_number_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        normalize_phone_number("+1 555 123 4567")


def test_validate_answer_rejects_skip_value() -> None:
    with pytest.raises(ValidationError):
        validate_answer("Не хочу отвечать")
