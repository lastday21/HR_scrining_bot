from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import (
    contacts_keyboard,
    middle_name_keyboard,
    project_link_keyboard,
    remove_keyboard,
    restart_keyboard,
)
from app.bot.messages import (
    ADMIN_PANEL_MESSAGE,
    ADMIN_START_MESSAGE,
    COMMAND_UNAVAILABLE_MESSAGE,
    CONTACTS_MESSAGE,
    FIRST_NAME_MESSAGE,
    INVALID_ANSWER_MESSAGE,
    INVALID_CONTACTS_MESSAGE,
    INVALID_FOREIGN_CONTACT_MESSAGE,
    INVALID_NAME_MESSAGE,
    INVALID_URL_MESSAGE,
    MIDDLE_NAME_MESSAGE,
    PROJECT_LINK_MESSAGE,
    RESTART_DECLINED_MESSAGE,
    RESTART_MESSAGE,
    START_MESSAGE,
    THANK_YOU_MESSAGE,
    UNKNOWN_COMMAND_MESSAGE,
    build_question_message,
    build_resume_message,
    build_stats_message,
    build_top3_message,
)
from app.bot.states import CandidateStates
from app.core.errors import RedisStorageError, SheetsWriteError, ValidationError
from app.core.settings import Settings
from app.domain.service import ScreeningService

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def handle_start(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    if settings.is_admin_user(telegram_user_id):
        await state.clear()
        await message.answer(ADMIN_START_MESSAGE, reply_markup=remove_keyboard())
        return

    await _start_candidate_flow(message, state, screening_service)


@router.message(Command("candidate"))
async def handle_candidate_mode(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    if not settings.is_admin_user(telegram_user_id):
        await message.answer(COMMAND_UNAVAILABLE_MESSAGE, reply_markup=remove_keyboard())
        return

    await state.clear()
    await _start_candidate_flow(message, state, screening_service)


@router.message(Command("admin"))
async def handle_admin_mode(message: Message, state: FSMContext, settings: Settings) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    if not settings.is_admin_user(telegram_user_id):
        await message.answer(COMMAND_UNAVAILABLE_MESSAGE, reply_markup=remove_keyboard())
        return

    await state.clear()
    await message.answer(ADMIN_PANEL_MESSAGE, reply_markup=remove_keyboard())


@router.message(Command("stats"))
async def handle_stats(
    message: Message,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    if not settings.is_admin_user(telegram_user_id):
        await message.answer(COMMAND_UNAVAILABLE_MESSAGE, reply_markup=remove_keyboard())
        return

    try:
        stats = await screening_service.get_screening_stats()
    except SheetsWriteError:
        logger.exception("Failed to fetch screening stats", extra={"telegram_user_id": telegram_user_id})
        await message.answer("Не удалось получить статистику из Google Sheets.")
        return

    if stats.total_candidates == 0:
        await message.answer("Пока нет завершенных кандидатов.")
        return

    await message.answer(build_stats_message(stats.total_candidates, stats.average_total))


@router.message(Command("top3"))
async def handle_top3(
    message: Message,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    if not settings.is_admin_user(telegram_user_id):
        await message.answer(COMMAND_UNAVAILABLE_MESSAGE, reply_markup=remove_keyboard())
        return

    try:
        candidates = await screening_service.get_top_candidates()
    except SheetsWriteError:
        logger.exception("Failed to fetch top candidates", extra={"telegram_user_id": telegram_user_id})
        await message.answer("Не удалось получить топ кандидатов из Google Sheets.")
        return

    lines = [
        (
            f"{candidate.first_name} - {candidate.last_name} - {candidate.telegram_username} - "
            f"{candidate.contacts} - {candidate.total_score} баллов"
        )
        for candidate in candidates
    ]
    await message.answer(build_top3_message(lines))


@router.message(CandidateStates.wait_restart_confirmation)
async def handle_restart_confirmation(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    answer = (message.text or "").strip().lower()

    if answer == "да":
        await screening_service.restart_draft(
            _get_telegram_user_id(message),
            _get_telegram_username(message),
        )
        await state.set_state(CandidateStates.wait_last_name)
        await message.answer(START_MESSAGE, reply_markup=remove_keyboard())
        return

    await message.answer(RESTART_DECLINED_MESSAGE, reply_markup=remove_keyboard())
    await _resume_existing_flow(message, state, screening_service, settings)


@router.message(CandidateStates.wait_last_name)
async def handle_last_name(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
) -> None:
    try:
        await screening_service.save_last_name(
            _get_telegram_user_id(message),
            message.text or "",
            _get_telegram_username(message),
        )
    except ValidationError:
        await message.answer(INVALID_NAME_MESSAGE)
        return

    await state.set_state(CandidateStates.wait_first_name)
    await message.answer(FIRST_NAME_MESSAGE)


@router.message(CandidateStates.wait_first_name)
async def handle_first_name(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
) -> None:
    try:
        await screening_service.save_first_name(
            _get_telegram_user_id(message),
            message.text or "",
            _get_telegram_username(message),
        )
    except ValidationError:
        await message.answer(INVALID_NAME_MESSAGE)
        return

    await state.set_state(CandidateStates.wait_middle_name)
    await message.answer(MIDDLE_NAME_MESSAGE, reply_markup=middle_name_keyboard())


@router.message(CandidateStates.wait_middle_name)
async def handle_middle_name(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
) -> None:
    try:
        await screening_service.save_middle_name(
            _get_telegram_user_id(message),
            message.text or "",
            _get_telegram_username(message),
        )
    except ValidationError:
        await message.answer(INVALID_NAME_MESSAGE, reply_markup=middle_name_keyboard())
        return

    await state.set_state(CandidateStates.wait_contacts)
    await message.answer(CONTACTS_MESSAGE, reply_markup=contacts_keyboard())


@router.message(CandidateStates.wait_contacts, F.contact)
async def handle_contacts_share(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    contact = message.contact
    if contact is None:
        await message.answer(INVALID_CONTACTS_MESSAGE, reply_markup=contacts_keyboard())
        return

    try:
        await screening_service.save_contacts_shared(
            _get_telegram_user_id(message),
            contact.phone_number,
            contact.user_id,
            _get_telegram_username(message),
        )
    except ValidationError as error:
        error_message = INVALID_FOREIGN_CONTACT_MESSAGE if "user id" in str(error).lower() else INVALID_CONTACTS_MESSAGE
        await message.answer(error_message, reply_markup=contacts_keyboard())
        return

    await _go_to_first_question(message, state, settings)


@router.message(CandidateStates.wait_contacts)
async def handle_contacts_text(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    try:
        await screening_service.save_contacts_text(
            _get_telegram_user_id(message),
            message.text or "",
            _get_telegram_username(message),
        )
    except ValidationError:
        await message.answer(INVALID_CONTACTS_MESSAGE, reply_markup=contacts_keyboard())
        return

    await _go_to_first_question(message, state, settings)


@router.message(CandidateStates.wait_question_answer)
async def handle_question_answer(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    try:
        draft = await screening_service.save_answer(_get_telegram_user_id(message), message.text or "")
    except ValidationError:
        await message.answer(INVALID_ANSWER_MESSAGE)
        return

    if draft.q_index < len(settings.screening_questions):
        await message.answer(
            build_question_message(
                draft.q_index + 1,
                settings.screening_questions[draft.q_index],
            )
        )
        return

    await state.set_state(CandidateStates.wait_project_link)
    await message.answer(PROJECT_LINK_MESSAGE, reply_markup=project_link_keyboard())


@router.message(CandidateStates.wait_project_link)
async def handle_project_link(
    message: Message,
    bot: Bot,
    state: FSMContext,
    screening_service: ScreeningService,
) -> None:
    try:
        submission = await screening_service.complete_screening(
            telegram_user_id=_get_telegram_user_id(message),
            project_link_text=message.text or "",
            telegram_username=_get_telegram_username(message),
        )
    except ValidationError:
        await message.answer(INVALID_URL_MESSAGE, reply_markup=project_link_keyboard())
        return
    except RedisStorageError:
        logger.exception(
            "Failed to finalize submission",
            extra={"telegram_user_id": _get_telegram_user_id(message)},
        )
        await state.clear()
        await message.answer(
            "Не удалось сохранить анкету. Напиши /start и попробуй еще раз.",
            reply_markup=remove_keyboard(),
        )
        return

    await message.answer(THANK_YOU_MESSAGE, reply_markup=remove_keyboard())
    await state.clear()
    await screening_service.process_submission(bot, submission)


@router.message()
async def handle_unknown_message(message: Message) -> None:
    await message.answer(UNKNOWN_COMMAND_MESSAGE)


async def _start_candidate_flow(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    draft = await screening_service.get_draft(telegram_user_id)
    if draft and not draft.sheets_written:
        await state.set_state(CandidateStates.wait_restart_confirmation)
        await message.answer(RESTART_MESSAGE, reply_markup=restart_keyboard())
        return

    await screening_service.restart_draft(telegram_user_id, _get_telegram_username(message))
    await state.set_state(CandidateStates.wait_last_name)
    await message.answer(START_MESSAGE, reply_markup=remove_keyboard())


async def _resume_existing_flow(
    message: Message,
    state: FSMContext,
    screening_service: ScreeningService,
    settings: Settings,
) -> None:
    telegram_user_id = _get_telegram_user_id(message)
    draft = await screening_service.get_draft(telegram_user_id)
    if draft is None:
        await screening_service.restart_draft(telegram_user_id, _get_telegram_username(message))
        await state.set_state(CandidateStates.wait_last_name)
        await message.answer(START_MESSAGE, reply_markup=remove_keyboard())
        return

    if not draft.last_name:
        await state.set_state(CandidateStates.wait_last_name)
        await message.answer(START_MESSAGE, reply_markup=remove_keyboard())
        return

    if not draft.first_name:
        await state.set_state(CandidateStates.wait_first_name)
        await message.answer(FIRST_NAME_MESSAGE, reply_markup=remove_keyboard())
        return

    if draft.middle_name is None:
        await state.set_state(CandidateStates.wait_middle_name)
        await message.answer(MIDDLE_NAME_MESSAGE, reply_markup=middle_name_keyboard())
        return

    if draft.contacts is None:
        await state.set_state(CandidateStates.wait_contacts)
        await message.answer(CONTACTS_MESSAGE, reply_markup=contacts_keyboard())
        return

    if draft.q_index < len(settings.screening_questions):
        await state.set_state(CandidateStates.wait_question_answer)
        await message.answer(
            build_resume_message(draft, settings.screening_questions[draft.q_index]),
            reply_markup=remove_keyboard(),
        )
        return

    await state.set_state(CandidateStates.wait_project_link)
    await message.answer(PROJECT_LINK_MESSAGE, reply_markup=project_link_keyboard())


async def _go_to_first_question(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.set_state(CandidateStates.wait_question_answer)
    await message.answer(
        build_question_message(1, settings.screening_questions[0], include_intro=True),
        reply_markup=remove_keyboard(),
    )


def _get_telegram_user_id(message: Message) -> int:
    return message.from_user.id if message.from_user else 0


def _get_telegram_username(message: Message) -> str | None:
    return message.from_user.username if message.from_user else None
