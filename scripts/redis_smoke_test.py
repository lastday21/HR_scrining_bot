from __future__ import annotations

import asyncio
from uuid import uuid4

from redis.asyncio import Redis

from app.core.settings import get_settings
from app.domain.models import CandidateDraft
from app.storage.redis_storage import RedisDraftStorage


async def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    storage = RedisDraftStorage(redis=redis, ttl_seconds=30)
    telegram_user_id = f"smoke-{uuid4()}"
    draft = CandidateDraft(telegram_user_id=telegram_user_id)
    await storage.save_draft(draft)
    loaded = await storage.get_draft(telegram_user_id)
    print("redis smoke ok:", loaded is not None and loaded.submission_id == draft.submission_id)
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
