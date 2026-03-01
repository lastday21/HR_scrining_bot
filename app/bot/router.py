from aiogram import Router

from app.bot.handlers import router as screening_router


def get_router() -> Router:
    root_router = Router()
    root_router.include_router(screening_router)
    return root_router
