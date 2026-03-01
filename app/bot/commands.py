from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

from app.core.settings import Settings


async def setup_bot_commands(bot: Bot, settings: Settings) -> None:
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Начать или продолжить анкету"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        commands=[
            BotCommand(command="candidate", description="Режим кандидата"),
            BotCommand(command="admin", description="Режим администратора"),
        ],
        scope=BotCommandScopeChat(chat_id=settings.admin_user_id),
    )
