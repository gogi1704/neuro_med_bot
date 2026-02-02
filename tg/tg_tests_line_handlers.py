from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from util_funs import parse_int , write_and_sleep, parse_base_answer
from resources import *
from db import dialogs_db as db
from tg_keyboards import tests_keyboards , intro_keyboards
from tg import tg_manager_chat_handlers
from ai import open_ai_main
from ai.ai_prompts import COLLECT_SYSTEM_PROMPT, BASE_USER_PROMPT, BASE_SYSTEM_PROMPT
from util_funs import send_wait_emoji, replace_wait_with_text
from doc_funs import *



async def handle_test_main_menu(update, context):
    q = update.callback_query
    await q.answer()

    user_id = update.effective_user.id          # универсально
    chat_id = update.effective_chat.id          # обычно тот же, но лучше так
    msg = update.effective_message              # message у callback есть тут

    await write_and_sleep(update, context, 2)

    if msg:  # на всякий случай
        await msg.delete()

    print(q.data)

    if q.data == "tests_main_menu_make_tests":
        await context.bot.send_message(
            chat_id=chat_id,
            text="тут будет ветка для Сдачи тестов",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Вернуться назад", callback_data="choose_type_user_tests")]
            ])
        )

    elif q.data == "tests_main_menu_get_tests":
        med_id = await db.get_med_id(user_id)

        if med_id:
            doc_url = await db.get_test_results(int(med_id))
            is_tests_bad = await db.get_deviations(int(med_id))

            if doc_url:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_IS_HAS_TRUE)

                await write_and_sleep(update, context, 5)
                await send_results_doc_and_text(update, context, doc_url)

                if is_tests_bad:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_TESTS_IS_BAD,
                        reply_markup=tests_keyboards.kb_tests_decode()
                    )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_TESTS_IS_GOOD)

                    await write_and_sleep(update, context, 2)
                    # await context.bot.send_message(
                    #     chat_id=update.effective_chat.id,
                    #     text=TEXT_TEST_ARE_YOU_WAKEUP,
                    #     reply_markup=intro_keyboards.kb_headache_pills()
                    # )

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_AFTER_GOOD_TESTS,
                        reply_markup=intro_keyboards.kb_after_good_tests()
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_IS_HAS_FALSE)
                await write_and_sleep(update, context, 2)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_MAIN_MENU,
                    reply_markup=tests_keyboards.kb_tests_main_menu()
                )

        else:
            await db.set_neuro_dialog_states(user_id, dialog_states["get_med_id"])
            await context.bot.send_message(
                chat_id=chat_id,
                text=TEXT_TESTS_GET_ID,
            )

    elif q.data == "tests_main_menu_get_decode":
        med_id = await db.get_med_id(user_id)

        if med_id:
            decode = await db.get_test_decode(int(med_id))

            if decode:
                decode_message = f"Вот ваша расшифровка: {decode}"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=decode_message,
                )
                return

            await context.bot.send_message(
                chat_id=chat_id,
                text=TEXT_TESTS_IS_HAS_TRUE_DECODE,
            )
            await write_and_sleep(update, context, 3)
            await send_manager_get_decode(update, context, med_id)
            await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
            await context.bot.send_message(
                chat_id=chat_id,
                text=TEXT_TESTS_GET_DECODE_FINAL,
            )

        else:
            await db.set_neuro_dialog_states(user_id, dialog_states["get_med_id_decode"])
            await context.bot.send_message(
                chat_id=chat_id,
                text=TEXT_TESTS_GET_ID,
            )

    elif q.data == "tests_main_menu_consult_med":
        await db.set_neuro_dialog_states(user_id, dialog_states["manager_collect"])
        wait_msg = await send_wait_emoji(update, context, "⏳")

        dialog = await db.get_dialog(user_id) or ""

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        decision = parse_base_answer(raw)

        await db.append_answer(user_id, "Assistant", decision)

        await replace_wait_with_text(
            update, context, wait_msg, decision
        )
        return

    elif q.data == "tests_main_menu_consult_neuro":
        await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
        wait_msg = await send_wait_emoji(update, context, "⏳")

        dialog = await db.get_dialog(user_id) or ""

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=BASE_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        answer = parse_base_answer(raw)

        await db.append_answer(user_id, "Assistant", answer)

        await replace_wait_with_text(
            update, context, wait_msg, answer
        )
        return

async def handle_get_med_id(update, context):
    med_id = update.message.text.strip()
    number = parse_int(med_id)
    print(f"handle_get_med_id\nтекст{med_id}\nномер{number}")

    if number is None:
        await update.message.reply_text(
            "❌ Нужно ввести целое число.\nПопробуйте ещё раз:"
        )
        return
    else:
        await db.create_dialog_user_with_med_id(update.message.from_user.id, med_id)
        await db.delete_neuro_dialog_states(update.message.from_user.id)

        doc_url = await db.get_test_results(med_id)
        is_tests_bad = await db.get_deviations(med_id)

        if doc_url:
            await update.message.reply_text(text= TEXT_TESTS_IS_HAS_TRUE)
            await write_and_sleep(update, context, 4)
            await send_results_doc_and_text(update, context, doc_url)

            if is_tests_bad:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_IS_BAD,
                    reply_markup= tests_keyboards.kb_tests_decode()
                )
            else:
                await update.message.reply_text(text=TEXT_TESTS_IS_GOOD)
                await write_and_sleep(update, context, 2)
                # await context.bot.send_message(
                #     chat_id=update.effective_chat.id,
                #     text=TEXT_TEST_ARE_YOU_WAKEUP,
                #     reply_markup= intro_keyboards.kb_headache_pills()
                # )

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_AFTER_GOOD_TESTS,
                    reply_markup=intro_keyboards.kb_after_good_tests()
                )
        else:
            await update.message.reply_text(text=TEXT_TESTS_IS_HAS_FALSE)
            await write_and_sleep(update, context, 2)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=TEXT_TESTS_MAIN_MENU,
                reply_markup=tests_keyboards.kb_tests_main_menu()
            )

async def handle_get_med_id_decode(update, context):
    med_id = update.message.text.strip()
    number = parse_int(med_id)
    print(f"handle_get_med_id\nтекст{med_id}\nномер{number}")

    if number is None:
        await update.message.reply_text(
            "❌ Нужно ввести целое число.\nПопробуйте ещё раз:"
        )
        return
    else:
        await db.create_dialog_user_with_med_id(update.effective_user.id , med_id)
        await db.delete_neuro_dialog_states(update.effective_user.id)
        doc_url = await db.get_test_results(number)

        if doc_url:
            await update.message.reply_text(text= TEXT_TESTS_IS_HAS_TRUE_DECODE)
            await write_and_sleep(update, context, 3)
            await send_manager_get_decode(update, context, med_id)
            await db.set_neuro_dialog_states(update.effective_user.id, dialog_states["base_speak"])
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=TEXT_TESTS_GET_DECODE_FINAL,
            )


        else:
            await write_and_sleep(update, context, 2)
            await update.message.reply_text(text=TEXT_TEST_IS_HAS_TRUE_DECODE_FALSE,
                                            reply_markup=tests_keyboards.kb_tests_decode_empty())

async def handle_decode_yes_no(update, context):
    q = update.callback_query
    med_id = await db.get_med_id(update.effective_user.id)
    await q.answer()

    if q.data == "tests_decode_yes":
        await send_manager_get_decode(update, context, med_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_SEND_TESTS_TO_DECODE)

        await write_and_sleep(update, context, 3)
        await update.effective_message.delete()

        await context.bot.send_message(
            chat_id=q.from_user.id,
            text=TEXT_CHELICL_INFO)
        await db.set_neuro_dialog_states(update.effective_chat.id, dialog_states["base_speak"])

    elif q.data == "tests_decode_no":
        await write_and_sleep(update, context, 2)
        await update.effective_message.delete()

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_TESTS_MAIN_MENU,
            reply_markup=tests_keyboards.kb_tests_main_menu()
        )

async def handle_after_good_tests_yes_no(update, context):
    q = update.callback_query
    await q.answer()
    await write_and_sleep(update, context, 2)
    await q.message.delete()

    if q.data == "after_good_tests_yes":
        await db.set_neuro_dialog_states(update.effective_user.id, dialog_states["after_tests_get_info"])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_QUESTION_AFTER_GOOD_TESTS,
        )

    elif q.data == "after_good_tests_no":
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_TEST_ARE_YOU_WAKEUP,
            reply_markup= intro_keyboards.kb_headache_pills()
        )

async def handle_empty_decode(update, context):
    q = update.callback_query
    await q.answer()
    med_id = await db.get_med_id(update.effective_user.id)

    if q.data == "empty_decode_get_laborant":
        await db.set_neuro_dialog_states(update.effective_user.id , dialog_states["base_speak"])
        await write_and_sleep(update, context, 3)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=TEXT_TESTS_IS_HAS_TRUE_DECODE)
        await send_manager_get_decode(update, context, med_id)
        await write_and_sleep(update, context, 3)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=TEXT_TESTS_GET_DECODE_FINAL)


    elif q.data == "empty_decode_get_manager":
        user_id = update.effective_user.id
        await db.set_neuro_dialog_states(user_id, dialog_states["manager_collect"])
        wait_msg = await send_wait_emoji(update, context, "⏳")

        dialog = await db.get_dialog(user_id) or ""

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        decision = parse_base_answer(raw)

        await db.append_answer(user_id, "Assistant", decision)

        await replace_wait_with_text(
            update, context, wait_msg, decision
        )
        return

async def send_manager_get_decode(update, context, med_id):
    doc_url = await db.get_test_results(int(med_id))
    if doc_url:
        text_to_manager = f"Пользователь просит расшифровать анализы. Вот ссылка на анализы :{doc_url} \n\n(#Диалог_{update.effective_user.id})."
    else:
        text_to_manager = f"Пользователь просит найти его анализы и сделать расшифровку. Вот номер его пробирки: {med_id}\n\n(#Диалог_{update.effective_user.id})."
    await tg_manager_chat_handlers.send_to_chat(update, context, text_to_manager)