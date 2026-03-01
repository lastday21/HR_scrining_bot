from app.domain.models import CandidateDraft

START_MESSAGE = (
    "Привет! Я задам тебе вопросы, чтобы определить твой подход к AI-first разработке.\n"
    "Давай познакомимся для начала. Напиши свою фамилию."
)
ADMIN_START_MESSAGE = (
    "Привет!\n"
    "Выбери режим:\n"
    "/candidate - пройти скрининг как кандидат\n"
    "/admin - открыть режим администратора"
)
ADMIN_PANEL_MESSAGE = (
    "Режим администратора.\n"
    "Выбери действие:\n"
    "/stats - статистика\n"
    "/top3 - топ-3 кандидата"
)
COMMAND_UNAVAILABLE_MESSAGE = "Команда недоступна."
RESTART_MESSAGE = "У вас уже есть анкета в процессе. Хотите заново заполнить анкету?"
FIRST_NAME_MESSAGE = "Напиши свое имя."
MIDDLE_NAME_MESSAGE = "Напиши свое отчество (если оно есть)."
CONTACTS_MESSAGE = "Напиши номер телефона, по которому мы сможем связаться с тобой."
QUESTION_INTRO = "Отлично! Теперь перейдем к вопросам."
PROJECT_LINK_MESSAGE = "Отправь ссылку на свой проект, который ты делал с помощью AI."
THANK_YOU_MESSAGE = "Спасибо за ответы. Мы вернемся с обратной связью в течение нескольких дней."
INVALID_NAME_MESSAGE = (
    "Имя должно содержать только буквы, пробел, дефис или апостроф. Попробуй еще раз."
)
INVALID_CONTACTS_MESSAGE = (
    "Номер не похож на корректный. Нужен формат +7XXXXXXXXXX или 8XXXXXXXXXX. "
    "Попробуй еще раз."
)
INVALID_FOREIGN_CONTACT_MESSAGE = "Нужно отправить именно свой контакт."
INVALID_URL_MESSAGE = "Пришли корректную ссылку на проект. Если забыл https://, я добавлю его сам."
INVALID_ANSWER_MESSAGE = "Нужен содержательный ответ. Попробуй сформулировать его чуть подробнее."
RESTART_DECLINED_MESSAGE = "Продолжаем с текущего места."
UNKNOWN_COMMAND_MESSAGE = "Напиши /start, чтобы начать или продолжить анкету."
STATS_EMPTY_MESSAGE = "Пока нет завершенных кандидатов."
TOP3_HEADER_MESSAGE = "Имя - Фамилия - Telegram - Контакты - Баллы"


def build_question_message(index: int, question: str, *, include_intro: bool = False) -> str:
    prefix = f"{QUESTION_INTRO}\n\n" if include_intro else ""
    return f"{prefix}{index}) {question}"


def build_resume_message(draft: CandidateDraft, question: str) -> str:
    return (
        "Продолжаем с текущего состояния.\n"
        f"Сейчас вопрос {draft.q_index + 1} из 7:\n{draft.q_index + 1}) {question}"
    )


def build_stats_message(total_candidates: int, average_total: float) -> str:
    return (
        "Статистика по завершенным кандидатам:\n"
        f"Прошло скрининг: {total_candidates}\n"
        f"Средний балл: {average_total:.2f}"
    )


def build_top3_message(lines: list[str]) -> str:
    if not lines:
        return STATS_EMPTY_MESSAGE
    return "Топ-3 кандидата:\n" + TOP3_HEADER_MESSAGE + "\n" + "\n".join(lines)
