import html
import json
import asyncio
from telegram.constants import ChatAction
from telegram.error import BadRequest, RetryAfter
from db import dialogs_db as data_base
from datetime import timedelta

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

from telegram.ext import ContextTypes

async def process_pending_kind(context: ContextTypes.DEFAULT_TYPE, kind: str):
    kind = str(kind).strip().lower()

    tasks = await data_base.get_all_pending_by_kind(kind)
    print(f"[JOB] process_pending_kind kind={kind} tasks={len(tasks)}")

    for row_id, med_id, telegram_id, chat_id in tasks:
        # if kind == "results":
        #     payload = data_base.get_results_only(med_id)
        #     if not payload or not str(payload).strip():
        #         continue
        #
        #     try:
        #         await context.bot.send_message(
        #             chat_id=chat_id,
        #             text=f"Вот результаты ваших анализов:\n{payload}"
        #         )
        #         await data_base.delete_pending_by_id(row_id)  # ✅ после успеха
        #     except Exception as e:
        #         print(f"[ERR] send results med_id={med_id} chat_id={chat_id}: {e}")

        if kind == "decode":
            result = await data_base.get_results_only(med_id)
            payload = await data_base.get_decode_only(med_id)
            if not result or not str(result).strip():
                continue

            try:
                if payload is None:
                    payload = "Пока нет расшифровки результатов!"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Вот результаты ваших анализов:\n{result} \n\n+Расшифровка: {payload}"
                )
                await data_base.delete_pending_by_id(row_id)  # ✅ после успеха
            except Exception as e:
                print(f"[ERR] send decode med_id={med_id} chat_id={chat_id}: {e}")

# async def pending_results_job(context: ContextTypes.DEFAULT_TYPE):
#     print("[JOB] pending_results_job fired")
#     await process_pending_kind(context, "results")

async def pending_decode_job(context: ContextTypes.DEFAULT_TYPE):
    print("[JOB] pending_decode_job fired")
    await process_pending_kind(context, "decode")


def setup_jobs(application):
    # application.job_queue.run_repeating(
    #     pending_results_job,
    #     interval=timedelta(minutes=2),
    #     first=5,
    #     name="pending_results_job"
    # )
    application.job_queue.run_repeating(
        pending_decode_job,
        interval=timedelta(minutes=120),
        first=1800,
        name="pending_decode_job"
    )
    application.job_queue.run_repeating(
        data_base.sync_tests_job,
        interval=timedelta(minutes=180),
        first=3600,
        name="sync_tests_job"
    )

    # DEBUG: покажем, что задачи реально зарегистрированы
    print("[DEBUG] jobs:", [j.name for j in application.job_queue.jobs()])

def bold_html(text: str) -> str:
    """
    Экранирует текст для HTML и оборачивает его в <b>...</b>
    """
    safe_text = html.escape(text)
    return f"<b>{safe_text}</b>"

async def get_list_and_price(list_tests,tests_price ):
    text = ""
    price = 0
    for test in list_tests:
        text += f"{test} - {tests_price[test]}₽\n"
        price += tests_price[test]

    return text, price