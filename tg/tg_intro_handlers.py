from resources import *
from tg_keyboards.intro_keyboards import *
from tg_keyboards import tests_keyboards
import asyncio
from telegram.constants import ChatAction
from util_funs import write_and_sleep
from db import dialogs_db as db

async def start(update, context):
    message = update.effective_message
    if message:
        await message.delete()
    await db.delete_dialog(update.effective_chat.id)
    await db.delete_neuro_dialog_states(update.effective_user.id)

    user_from_manager = await db.get_from_manager(update.effective_user.id)
    if user_from_manager is None:
        args = context.args
        new_ref = args[0] if args else None
        ref_code = new_ref if new_ref else "base_url"
        print(ref_code)
        await db.set_from_manager(update.effective_chat.id, ref_code)


    # await dialogs_db.add_user(
    #     user_id=user_id,
    #     name="",
    #     from_manager=ref_code
    # )

    user_state = await db.get_user_state(update.effective_user.id)
    if user_state:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_TESTS_MAIN_MENU,
            reply_markup=tests_keyboards.kb_tests_main_menu()
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_INTRO_1,
            reply_markup=kb_intro_1()
        )

async def choose_user_type(update, context):
    q = update.callback_query
    await q.answer()
    await write_and_sleep(update, context, 2)
    await update.effective_message.delete()

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_CHOOSE_USER_TYPE,
        reply_markup= kb_choose_user_type()
    )

async def handle_choose_user(update, context):
    q = update.callback_query
    await q.answer()
    await write_and_sleep(update, context, 2)
    await update.effective_message.delete()


    if q.data == "choose_type_user_tests":
        await db.set_user_state(update.effective_user.id, "state_tests")
        await context.bot.send_message(
                chat_id=q.from_user.id,
                text=TEXT_TESTS_MAIN_MENU,
                reply_markup= tests_keyboards.kb_tests_main_menu()
            )

    elif q.data == "choose_type_user_anamnez":
        await db.set_user_state(update.effective_user.id, "state_anamnez")
        await context.bot.send_message(
                chat_id=q.from_user.id,
                text=TEXT_TESTS_MAIN_MENU,
                reply_markup= tests_keyboards.kb_tests_main_menu()
            )

    elif q.data == "choose_type_user_newUser":
        await db.set_user_state(update.effective_user.id, "state_new_user")
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text= TEXT_NEW_USER,
            reply_markup= kb_new_user()
        )

    elif q.data == "choose_type_user_else":
        await db.delete_neuro_dialog_states(update.effective_user.id)
        await context.bot.send_message(
                chat_id=q.from_user.id,
                text=TEXT_TESTS_MAIN_MENU,
                reply_markup= tests_keyboards.kb_tests_main_menu()
            )


async def handle_headache(update, context):
    q = update.callback_query
    await q.answer()
    await write_and_sleep(update, context, 2)
    await update.effective_message.delete()

    if q.data == "headache_pill":
        text = "Ты не оригинален. 99% отвечают именно так."
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=text
        )

        await write_and_sleep(update, context, 2)

        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=TEXT_INTRO_3,
            reply_markup=kb_pills()
        )

    else:
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=TEXT_PILLS_99)

        await write_and_sleep(update, context, 2)
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=TEXT_INTRO_4)

        await write_and_sleep(update, context, 4)
        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=TEXT_INTRO_5,
            reply_markup=kb_next()
        )


async def handle_pill_answer(update, context):
    q = update.callback_query
    await q.answer()
    await write_and_sleep(update, context, 2)
    await update.effective_message.delete()

    if q.data == "pill_citramon":
        text = "Не знаю почему, но большинство отвечают именно так."
    else:
        text = "Не знаю почему, но большинство отвечают — Цитрамон."

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=text
    )

    await write_and_sleep(update, context, 2)
    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_INTRO_4,
    )

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(5)

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_INTRO_5,
        reply_markup= kb_next()
    )

async def handle_send_chelik_info(update, context):
    q = update.callback_query
    await q.answer()
    await write_and_sleep(update, context, 2)
    await update.effective_message.delete()

    await context.bot.send_message(
        chat_id=q.from_user.id,
        text=TEXT_CHELICL_INFO)
    await db.set_neuro_dialog_states(update.effective_chat.id, dialog_states["base_speak"])

