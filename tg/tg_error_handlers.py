import traceback
from telegram.error import RetryAfter, TimedOut, NetworkError, Forbidden, BadRequest

ADMIN_CHAT_ID = 1106334332  # <-- поставь сюда свой telegram user_id или chat_id

TELEGRAM_LIMIT = 4096

def _chunk_text(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    # режем по лимиту Telegram, чтобы send_message не падал
    if not text:
        return [""]
    return [text[i:i + limit] for i in range(0, len(text), limit)]

async def error_handler(update, context):
    err = context.error

    # 1) Пытаемся отдать пользователю "человеческую" реакцию на сетевые ошибки
    try:
        raise err

    except RetryAfter as e:
        wait_time = int(e.retry_after)
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                f"Слишком частые запросы. Подождите {wait_time} секунд и попробуйте снова."
            )
        return

    except TimedOut:
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                "Сервер Telegram долго не отвечает. Попробуйте ещё раз через пару секунд."
            )
        # всё равно уведомим админа
        pass

    except NetworkError:
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                "Проблема с соединением. Попробуйте позже."
            )
        # всё равно уведомим админа
        pass

    except Exception:
        # просто идём дальше к уведомлению админа
        pass

    # 2) Формируем диагностическое сообщение для админа
    tb = traceback.format_exc()

    # достаём "последний кадр" (файл/строка/функция) если есть traceback
    file_line = ""
    try:
        if err and err.__traceback__:
            last = traceback.extract_tb(err.__traceback__)[-1]
            file_line = f"{last.filename}:{last.lineno} in {last.name}"
    except Exception:
        file_line = ""

    user_id = getattr(getattr(update, "effective_user", None), "id", None)
    chat_id = getattr(getattr(update, "effective_chat", None), "id", None)

    # кусочек текста апдейта (что именно пришло)
    update_hint = ""
    try:
        if update:
            if getattr(update, "message", None) and update.message.text:
                update_hint = f"message.text={update.message.text!r}"
            elif getattr(update, "callback_query", None):
                q = update.callback_query
                update_hint = f"callback.data={getattr(q, 'data', None)!r}"
    except Exception:
        update_hint = ""

    header = (
        "🚨 *Ошибка в боте*\n"
        f"*Type:* `{type(err).__name__}`\n"
        f"*Where:* `{file_line}`\n"
        f"*User:* `{user_id}`\n"
        f"*Chat:* `{chat_id}`\n"
        f"*Update:* `{update_hint}`\n"
        "\n*Traceback:*\n"
    )

    # Telegram markdown может ломаться из-за спецсимволов → безопаснее отправлять как code block
    admin_text = header + "```text\n" + tb + "\n```"

    # 3) Отправляем админу (тебе)
    try:
        for part in _chunk_text(admin_text):
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=part,
                parse_mode="Markdown"
            )
    except (Forbidden, BadRequest) as e:
        # если админ-чат недоступен или markdown сломался
        # fallback: без parse_mode
        fallback = header + tb
        for part in _chunk_text(fallback):
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=part)
    except Exception as e:
        # если даже так не получилось — хотя бы в консоль
        print("Не смог отправить ошибку админу:", e)

    # 4) Пользователю — коротко (без деталей)
    if update and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                "Произошла внутренняя ошибка. Я уже отправил детали разработчику 🙏"
            )
        except Exception:
            pass
