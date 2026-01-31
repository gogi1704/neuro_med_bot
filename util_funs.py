import json
import asyncio
from telegram.constants import ChatAction
from telegram.error import BadRequest, RetryAfter

def parse_base_answer(model_response: str) -> str:
    """
    Извлекает значение поля 'answer' из JSON-ответа модели.
    Возвращает строку answer или выбрасывает исключение при ошибке.
    """
    try:
        data = json.loads(model_response)
        answer = data.get("answer")

        if answer is None:
            raise ValueError("Поле 'answer' отсутствует в ответе модели")

        return answer

    except json.JSONDecodeError as e:
        raise ValueError(f"Ответ модели не является валидным JSON: {e}. \n\n Ответ модели: {model_response}")

def pars_answer_and_data(model_response: str) :
    """
    Извлекает значение поля 'answer' из JSON-ответа модели.
    Возвращает строку answer или выбрасывает исключение при ошибке.
    """
    try:
        data = json.loads(model_response)
        answer = data.get("answer")
        user_data = data.get("data")
        if answer is None:
            raise ValueError("Поле 'answer' отсутствует в ответе модели")

        return answer, user_data

    except json.JSONDecodeError as e:
        raise ValueError(f"Ответ модели не является валидным JSON: {e}. \n\n Ответ модели: {model_response}")

async def write_and_sleep(update, context, sleep_time):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(sleep_time)

def parse_int(text: str) -> int | None:
        try:
            return int(text)
        except ValueError:
            return None

async def send_wait_emoji(update, context, wait_text: str = "⏳"):
    """
    Отправляет ОДНО сообщение-индикатор и возвращает объект Message (или None, если не удалось отправить).
    """
    chat_id = update.effective_chat.id
    try:
        return await context.bot.send_message(chat_id=chat_id, text=wait_text)
    except RetryAfter as e:
        await asyncio.sleep(float(getattr(e, "retry_after", 1.0)))
        try:
            return await context.bot.send_message(chat_id=chat_id, text=wait_text)
        except Exception:
            return None
    except Exception:
        return None

async def replace_wait_with_text(update, context, wait_msg, answer_text: str):
    """
    Пытается заменить (edit) ТО САМОЕ сообщение wait_msg (⏳) на answer_text.
    Если редактирование невозможно — удаляет wait_msg и отправляет answer_text отдельным сообщением.
    """
    chat_id = update.effective_chat.id

    if wait_msg and getattr(wait_msg, "message_id", None):
        mid = wait_msg.message_id

        # 1) Попытка отредактировать исходное сообщение
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=mid, text=answer_text)
            return
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 1.0)))
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=mid, text=answer_text)
                return
            except Exception:
                pass
        except BadRequest:
            pass
        except Exception:
            pass

        # 2) Если edit не сработал — пробуем удалить ⏳
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:
            pass

    # 3) Fallback: отправляем ответ отдельным сообщением
    await update.message.reply_text(answer_text)
