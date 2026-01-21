from resources import *
from tg_keyboards.intro_keyboards import *
import asyncio
from telegram.constants import ChatAction
from db import dialogs_db as db

async def start(update, context):
    message = update.effective_message
    if message:
        await message.delete()

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=TEXT_INTRO_1,
        reply_markup=kb_intro_1()
    )

async def intro_agree(update, context):
    q = update.callback_query
    await q.answer()

    await update.effective_message.delete()

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_INTRO_2,
        reply_markup=kb_intro_2()
    )

async def headache_answer(update, context):
    q = update.callback_query
    await q.answer()

    await update.effective_message.delete()

    if q.data == "headache_pill":
        text = "Ты не оригинален. 99% отвечают именно так."
    else:
        text = "99% говорят, что выпили бы таблетку."

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=text
    )

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(2)

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_INTRO_3,
        reply_markup=kb_intro_3()
    )


# async def intro_next_4(update, context):
#     q = update.callback_query
#     await q.answer()
#
#     await update.effective_message.delete()
#
#     await context.bot.send_message(
#         chat_id=q.from_user.id,
#         text=TEXT_INTRO_3,
#         reply_markup=kb_intro_3()
#     )

async def pill_answer(update, context):
    q = update.callback_query
    await q.answer()

    await update.effective_message.delete()

    if q.data == "pill_citramon":
        text = "Не знаю почему, но большинство отвечают именно так."
    else:
        text = "Не знаю почему, но большинство отвечают — Цитрамон."

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=text
    )

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_INTRO_4,
    )

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(2)

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_INTRO_5,
        reply_markup= kb_next()
    )

async def intro_hello_user(update, context):
    q = update.callback_query
    await q.answer()
    await update.effective_message.delete()

    user = await db.get_user(update.effective_chat.id)
    print(user)
    if user:
        # ТУТ ВВОДИТ ИДЕНТИФИКАТОР КЛИЕНТА
        await db.set_neuro_dialog_states(
            update.effective_chat.id,
            dialog_states_dict["get_med_id"]
        )
        text = TEXT_INTRO_7.format(user_name = user['name'])
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=text,
        )

    else:
        # ТУТ ВВОДИТ ИМЯ
        await db.set_neuro_dialog_states(
            update.effective_chat.id,
            dialog_states_dict["get_name"]
        )

        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=TEXT_INTRO_6,
        )


