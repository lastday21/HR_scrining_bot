from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.errors import LlmRequestError
from app.core.settings import Settings
from app.domain.models import CandidateSubmission, LlmScore

logger = logging.getLogger(__name__)
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "screening_prompt.txt"


def render_prompt_template(template: str, *, answers_block: str, project_link: str) -> str:
    return template.replace("{answers_block}", answers_block).replace("{project_link}", project_link)


def parse_llm_score_response(raw_text: str) -> LlmScore:
    cleaned = raw_text.strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    start_index = cleaned.find("{")
    end_index = cleaned.rfind("}")
    if start_index == -1 or end_index == -1:
        raise LlmRequestError("LLM response does not contain JSON.")

    try:
        payload = json.loads(cleaned[start_index : end_index + 1])
        return LlmScore.model_validate(payload)
    except (json.JSONDecodeError, PydanticValidationError, ValueError, TypeError) as error:
        raise LlmRequestError("LLM response is not valid JSON.") from error


class YandexLlmClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def score_submission(
        self,
        submission: CandidateSubmission,
        questions: tuple[str, ...],
    ) -> LlmScore:
        prompt = self._build_prompt(submission, questions)
        last_error: Exception | None = None

        for attempt in range(1, self.settings.llm_retry_attempts + 1):
            started_at = time.perf_counter()
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.llm_request_timeout_seconds,
                ) as client:
                    response = await client.post(
                        self.settings.llm_api_url,
                        headers={"Authorization": f"Api-Key {self.settings.llm_api_key}"},
                        json={
                            "modelUri": self.settings.llm_model_uri,
                            "completionOptions": {
                                "stream": False,
                                "temperature": 0.2,
                                "maxTokens": 2000,
                            },
                            "messages": [{"role": "user", "text": prompt}],
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()
                    text = payload["result"]["alternatives"][0]["message"]["text"]
                    score = parse_llm_score_response(text)
            except (
                httpx.HTTPError,
                json.JSONDecodeError,
                KeyError,
                IndexError,
                TypeError,
                LlmRequestError,
            ) as error:
                last_error = error
                duration_ms = int((time.perf_counter() - started_at) * 1000)
                logger.warning(
                    "LLM request attempt failed",
                    extra={
                        "telegram_user_id": submission.telegram_user_id,
                        "submission_id": submission.submission_id,
                        "state": "completed",
                        "step": "llm_request",
                        "attempt": attempt,
                        "duration_ms": duration_ms,
                        "success": False,
                    },
                )
                if attempt == self.settings.llm_retry_attempts:
                    break
                await asyncio.sleep(float(attempt))
                continue

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "LLM request completed",
                extra={
                    "telegram_user_id": submission.telegram_user_id,
                    "submission_id": submission.submission_id,
                    "state": "completed",
                    "step": "llm_request",
                    "attempt": attempt,
                    "duration_ms": duration_ms,
                    "success": True,
                },
            )
            return score

        raise LlmRequestError("LLM request failed after retries.") from last_error

    def _build_prompt(self, submission: CandidateSubmission, questions: tuple[str, ...]) -> str:
        template = PROMPT_PATH.read_text(encoding="utf-8")
        answers_block = "\n".join(
            f"Q{index}: {question}\nA{index}: {answer}"
            for index, (question, answer) in enumerate(
                zip(questions, submission.answers, strict=False),
                start=1,
            )
        )
        project_link = submission.project_link or "not provided"
        return render_prompt_template(
            template,
            answers_block=answers_block,
            project_link=project_link,
        )
