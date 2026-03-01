from __future__ import annotations

import json

from redis.asyncio import Redis

from app.core.errors import RedisStorageError
from app.domain.models import CandidateDraft


class RedisDraftStorage:
    def __init__(self, *, redis: Redis, ttl_seconds: int) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds

    async def get_draft(self, telegram_user_id: int | str) -> CandidateDraft | None:
        try:
            raw_value = await self.redis.get(self._build_key(telegram_user_id))
        except Exception as error:
            raise RedisStorageError("Failed to read draft from Redis.") from error
        if raw_value is None:
            return None
        try:
            payload = json.loads(raw_value)
            return CandidateDraft.model_validate(payload)
        except Exception as error:
            raise RedisStorageError("Failed to deserialize draft from Redis.") from error

    async def save_draft(self, draft: CandidateDraft) -> None:
        try:
            await self.redis.set(
                self._build_key(draft.telegram_user_id),
                draft.model_dump_json(),
                ex=self.ttl_seconds,
            )
        except Exception as error:
            raise RedisStorageError("Failed to save draft to Redis.") from error

    async def mark_sheets_written(self, telegram_user_id: int | str) -> None:
        draft = await self.get_draft(telegram_user_id)
        if draft is None:
            return
        draft.sheets_written = True
        await self.save_draft(draft)

    def _build_key(self, telegram_user_id: int | str) -> str:
        return f"candidate:draft:{str(telegram_user_id).strip()}"
