import pytest

from app.core.errors import LlmRequestError
from app.integrations.llm_client import parse_llm_score_response, render_prompt_template


def test_parse_llm_score_response_accepts_plain_json() -> None:
    score = parse_llm_score_response(
        """
        {
          \"criterion_1\": 31,
          \"criterion_2\": 24,
          \"criterion_3\": 18,
          \"result\": 73,
          \"model_explanation\": \"Strong answers.\"
        }
        """
    )

    assert score.criterion_1 == 31
    assert score.result == 73


def test_parse_llm_score_response_accepts_markdown_block() -> None:
    score = parse_llm_score_response(
        """```json
        {
          \"criterion_1\": 20,
          \"criterion_2\": 15,
          \"criterion_3\": 10,
          \"result\": 45,
          \"model_explanation\": \"Ok\"
        }
        ```"""
    )

    assert score.criterion_2 == 15
    assert score.result == 45


def test_parse_llm_score_response_rejects_invalid_json() -> None:
    with pytest.raises(LlmRequestError):
        parse_llm_score_response("not a json payload")


def test_parse_llm_score_response_rejects_result_mismatch() -> None:
    with pytest.raises(LlmRequestError):
        parse_llm_score_response(
            """
            {
              \"criterion_1\": 20,
              \"criterion_2\": 15,
              \"criterion_3\": 10,
              \"result\": 99,
              \"model_explanation\": \"Broken total.\"
            }
            """
        )


def test_render_prompt_template_keeps_json_example_braces() -> None:
    template = """
    Return only JSON:
    {
      \"criterion_1\": 0,
      \"criterion_2\": 0
    }

    Answers:
    {answers_block}

    Project link:
    {project_link}
    """

    rendered = render_prompt_template(
        template,
        answers_block="Q1: Question\nA1: Answer",
        project_link="https://example.com/repo",
    )

    assert '\"criterion_1\": 0' in rendered
    assert "Q1: Question\nA1: Answer" in rendered
    assert "https://example.com/repo" in rendered
