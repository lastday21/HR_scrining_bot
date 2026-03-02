# HR Screening Bot

Telegram-бот для первичного скрининга кандидатов на AI-first разработку.

Дополнительные материалы:
- [Пояснение по выбору критериев и вопросов](./questions_criteria%20_explanations.md)
- [ScreenCast](./ScreenCast.md)
- [Google sheet таблица](https://docs.google.com/spreadsheets/d/1b7hIjkxhbzw629-dlOmS4k-qZ6EQQ-yHZW0lQpuTWII/edit?gid=0#gid=0)
- Ник тг бота - @ai_first_screening_bot

Бот:
- проводит кандидата по анкете: ФИО -> контакты -> 7 вопросов -> ссылка на проект
- хранит черновик анкеты в Redis
- отправляет ответы в LLM для оценки по 3 критериям
- записывает результат в Google Sheets
- поддерживает админ-команды `/stats` и `/top3`
- отправляет уведомление о сильных кандидатах в админ-чат

## Настройка и запуск

### 1. Настрой `.env`

Создай `.env` на основе [.env.example](./.env.example) и заполни значения.

Для текущего проекта используются такие переменные:

```env
BOT_TOKEN=
REDIS_URL=redis://localhost:6379/0
ADMIN_CHAT_ID=
ADMIN_USER_ID=
GOOGLE_SPREADSHEET_ID=
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=google_sa.json
GOOGLE_WORKSHEET_TITLE=Sheet1
LLM_API_KEY=
LLM_MODEL_URI=
LLM_API_URL=https://llm.api.cloud.yandex.net/foundationModels/v1/completion
HOT_CANDIDATE_THRESHOLD=70
```

Откуда брать неочевидные значения:

- `BOT_TOKEN` - создать бота через `@BotFather`, команда `/newbot`
- `ADMIN_USER_ID` - можно узнать через `@userinfobot` или `@getmyid_bot`; это именно `user_id`, не username
- `ADMIN_CHAT_ID` - для личного чата обычно совпадает с вашим Telegram id; также можно посмотреть `chat.id` через `getUpdates`
- `GOOGLE_SPREADSHEET_ID` - взять из URL Google-таблицы: значение между `/d/` и `/edit`
- `LLM_API_KEY` - ключ доступа к Yandex Foundation Models API из Yandex Cloud
- `LLM_MODEL_URI` - идентификатор модели в формате `gpt://<folder_id>/<model_name>` из Yandex Cloud
- `HOT_CANDIDATE_THRESHOLD` - порог суммы баллов для уведомления о сильном кандидате, например `70`

### 2. Подготовь `google_sa.json`

Нужен JSON-файл сервисного аккаунта Google с доступом к нужной Google-таблице.

Что сделать:
- создать или взять готовый service account в Google Cloud
- скачать JSON-ключ
- переименовать файл в `google_sa.json`
- положить его в корень проекта рядом с [README.md](./README.md), [docker-compose.yml](./docker-compose.yml) и [main.py](./main.py)

В проекте по умолчанию ожидается именно такой путь:

```env
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=google_sa.json
```

Важно:
- файл `google_sa.json` уже добавлен в [.gitignore](./.gitignore)
- не коммить этот файл в репозиторий
- в Docker он монтируется в контейнер как volume, а не вшивается в образ

### 3. Собери и запусти через Docker

Требуется установленный Docker.

Запуск:

```bash
docker compose up --build -d
```

Остановка:

```bash
docker compose down
```

Логи бота:

```bash
docker compose logs -f bot
```

Что делает `docker-compose.yml`:
- поднимает контейнер с ботом
- поднимает Redis рядом
- внутри контейнера переопределяет `REDIS_URL` на `redis://redis:6379/0`
- монтирует `google_sa.json` в контейнер read-only

## Админ-команды

Если `Telegram user_id == ADMIN_USER_ID`, доступны:
- `/start` - выбор режима
- `/candidate` - пройти сценарий как кандидат
- `/admin` - открыть режим администратора
- `/stats` - показать число завершенных кандидатов и средний балл
- `/top3` - показать топ-3 кандидатов по сумме баллов

## Google Sheets

Структура строки кандидата:
- `A` - id
- `B` - `last_name`
- `C` - `first_name`
- `D` - `middle_name`
- `E` - `tg_id`
- `F` - `tg_username`
- `G` - `contacts`
- `H` - `started_at`
- `I..O` - `q1..q7`
- `P..R` - `criterion_1..criterion_3`
- `S` - `result`
- `T` - `model_explanation`
- `U` - `link_project`

Уникальность строки определяется по `tg_id`.
Если кандидат уже есть, бот обновляет существующую строку и сохраняет исходный `id` в колонке `A`.

## Проверка

Тесты:

```bash
poetry run pytest
```

## Структура проекта

```text
app/
  bot/           Telegram handlers, keyboards, messages, FSM states
  core/          settings, errors, logging
  domain/        models, validators, business logic
  integrations/  LLM, Google Sheets, admin notifications
  prompts/       prompt templates for LLM
  storage/       Redis draft storage
main.py          root entrypoint
Dockerfile       bot image build
docker-compose.yml  bot + redis deployment
```
