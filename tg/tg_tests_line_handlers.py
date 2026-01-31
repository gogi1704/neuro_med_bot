from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from util_funs import parse_int , write_and_sleep, parse_base_answer
from resources import *
from db import dialogs_db as db
from tg_keyboards import tests_keyboards , intro_keyboards
from tg import tg_manager_chat_handlers
from ai import open_ai_main
from ai.ai_prompts import COLLECT_SYSTEM_PROMPT, BASE_USER_PROMPT, BASE_SYSTEM_PROMPT
from util_funs import send_wait_emoji, replace_wait_with_text

async def response_to_laborant_sheet(user_id):
    return True, "В завышен \nC занижен \nСахар сладкий \n Кровь красная"
async def laborant_sheet_bad_or_nice_tests():
    return False



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

    elif q.data in ("tests_main_menu_get_tests", "tests_main_menu_get_decode"):
        med_id = await db.get_med_id(user_id)

        if med_id:
            is_has_tests, tests = await response_to_laborant_sheet(user_id)
            is_tests_bad = await laborant_sheet_bad_or_nice_tests()

            if is_has_tests:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_IS_HAS_TRUE)

                await write_and_sleep(update, context, 5)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"Вот ваши анализы :{tests}")

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
    text = update.message.text.strip()
    number = parse_int(text)
    print(f"handle_get_med_id\nтекст{text}\nномер{number}")

    if number is None:
        await update.message.reply_text(
            "❌ Нужно ввести целое число.\nПопробуйте ещё раз:"
        )
        return
    else:
        await db.create_dialog_user_with_med_id(update.message.from_user.id, text)
        await db.delete_neuro_dialog_states(update.message.from_user.id)

        is_has_tests, tests = await response_to_laborant_sheet(update.message.from_user.id)
        is_tests_bad = await laborant_sheet_bad_or_nice_tests()

        if is_has_tests:
            await update.message.reply_text(text= TEXT_TESTS_IS_HAS_TRUE)
            await write_and_sleep(update, context, 5)
            await update.message.reply_text(text=f"Вот ваши анализы :{tests}")

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

async def handle_decode_yes_no(update, context):
    q = update.callback_query
    await q.answer()

    if q.data == "tests_decode_yes":
        is_has_tests, tests = await response_to_laborant_sheet(update.effective_user.id)
        text_to_manager = f"Пользователь просит расшифровать анализы. Вот анализы :{tests} \n\n(#Диалог_{update.effective_user.id}). "
        await tg_manager_chat_handlers.send_to_chat(update, context, text_to_manager)
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
