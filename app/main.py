from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.bot.commands import setup_bot_commands
from app.bot.router import get_router
from app.core.logging_config import configure_logging
from app.core.settings import get_settings
from app.domain.service import ScreeningService
from app.integrations.llm_client import YandexLlmClient
from app.integrations.notifier import TelegramNotifier
from app.integrations.sheets_client import GoogleSheetsClient
from app.storage.redis_storage import RedisDraftStorage


async def run_bot() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=RedisStorage(redis=redis_client))
    dispatcher.include_router(get_router())

    screening_service = ScreeningService(
        settings=settings,
        storage=RedisDraftStorage(
            redis=redis_client,
            ttl_seconds=settings.redis_draft_ttl_seconds,
        ),
        llm_client=YandexLlmClient(settings=settings),
        sheets_client=GoogleSheetsClient(settings=settings),
        notifier=TelegramNotifier(settings=settings),
    )

    await setup_bot_commands(bot, settings)

    logger.info("Starting bot polling")
    try:
        await dispatcher.start_polling(bot, screening_service=screening_service, settings=settings)
    finally:
        await bot.session.close()
        await redis_client.aclose()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
