import traceback
from telegram.error import RetryAfter, TimedOut, NetworkError

async def error_handler(update, context):
    try:
        raise context.error

    except RetryAfter as e:
        wait_time = int(e.retry_after)
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                f"Слишком частые запросы. Подождите {wait_time} секунд и попробуйте снова."
            )

    except TimedOut:
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                "Сервер Telegram долго не отвечает. Попробуйте ещё раз через пару секунд."
            )

    except NetworkError:
        if update and update.effective_chat:
            await update.effective_chat.send_message(
                "Проблема с соединением. Попробуйте позже."
            )

    except Exception as e:
        # Полный traceback
        tb = traceback.format_exc()

        print("=== НЕОЖИДАННАЯ ОШИБКА ===")
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Сообщение: {e}")
        print("Traceback:")
        print(tb)

        if update and update.effective_chat:
            await update.effective_chat.send_message(
                "Произошла внутренняя ошибка. Мы уже разбираемся 🙏"
            )
