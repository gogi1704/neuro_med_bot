from db import dialogs_db as db
from ai import  open_ai_main
import util_funs
from doc_funs import *
from ai.ai_prompts import  *
from resources import *
import asyncio
from telegram.constants import ChatAction
from tg import tg_manager_chat_handlers, tg_tests_line_handlers
from util_funs import send_wait_emoji, replace_wait_with_text
from tg_keyboards.intro_keyboards import kb_after_good_tests
from tg_keyboards import back_navigation_keyboards
from tg_keyboards import tests_keyboards
from tg.tg_tests_line_handlers import send_manager_get_decode
from util_funs import write_and_sleep


async def handle_text_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    state = await db.get_neuro_dialog_states(user_id)
    dialog = await db.get_dialog(user_id) or ""
    print(state)

    def add(role, msg):
        return dialog + f"\n{role}: {msg}"

    manager_msg_id = await db.get_user_answer_state(update.effective_user.id)
    #Проверка на чат с менеджером
    if manager_msg_id is not None:
        # Получили ответ → очищаем состояние
        await db.delete_user_answer_state(update.effective_user.id)

        # Отправляем сообщение в группу
        await tg_manager_chat_handlers.send_to_chat(
            update, context,
            message_text=f"📨 Пользователь ответил:\n\n{update.message.text}\n\n\n#Диалог_с_{update.effective_user.id}"
        )

        await update.message.reply_text("✅ Ваш ответ отправлен менеджеру.")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)


    if state == dialog_states["after_tests_get_info"]:
        text_to_manager = f"У пользователя все в порядке с анализами, но он хочет поговорить со специалистом! Вот, как он в двух словах описал проблему :{text} \n\n(#Диалог_{update.effective_user.id}). "
        await tg_manager_chat_handlers.send_to_chat(update, context, text_to_manager)
        await complete_dialog(telegram_id=update.effective_chat.id,
                              last_text="Дайте знать, если вам что то понадобится!")

        await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(2)
        await update.message.reply_text(text="Дайте знать, если вам что то понадобится")

    elif state == dialog_states["get_med_id"]:
        await tg_tests_line_handlers.handle_get_med_id(update, context)

    elif state == dialog_states["get_med_id_decode"]:
        await tg_tests_line_handlers.handle_get_med_id_decode(update, context)

    elif state == dialog_states["get_med_id_consult"]:
        await tg_tests_line_handlers.handle_get_med_id_consult(update, context)
    # ---------- BASE ----------
    elif state == dialog_states["base_speak"]:
        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # >>> ДОБАВЛЕНО: один раз отправляем ⏳ и потом ЗАМЕНЯЕМ ЭТО ЖЕ сообщение на ответ
        wait_msg = await send_wait_emoji(update, context, "⏳")
        # <<< ДОБАВЛЕНО

        raw = await open_ai_main.get_gpt_answer(
            BASE_SYSTEM_PROMPT,
            BASE_USER_PROMPT.format(dialog=dialog)
        )
        answer = util_funs.parse_base_answer(raw)

        if answer == "get_med":
            print("get_med")
            await db.set_neuro_dialog_states(user_id, dialog_states["manager_collect"])

            raw = await open_ai_main.get_gpt_answer(
                system_prompt=COLLECT_SYSTEM_PROMPT,
                user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
            )
            decision = util_funs.parse_base_answer(raw)
            print(raw)
            dialog = add("Assistant", decision)
            await db.append_answer(user_id, "Assistant", decision)

            await replace_wait_with_text(update, context, wait_msg, decision)
            return

        if answer == "get_boss":
            await db.set_neuro_dialog_states(user_id, dialog_states["boss_collect"])

            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

            # Чтобы не плодить индикаторы, переиспользуем тот же wait_msg:
            raw = await open_ai_main.get_gpt_answer(
                system_prompt=BOSS_COLLECT_SYSTEM_PROMPT,
                user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
            )

            decision = util_funs.parse_base_answer(raw)
            print(raw)

            dialog = add("Assistant", decision)
            await db.append_answer(user_id, "Assistant", decision)

            await replace_wait_with_text(update, context, wait_msg, decision)
            return

        if answer == "get_analyses":
            await db.delete_neuro_dialog_states(update.effective_user.id)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=TEXT_MAKE_CHECK_UP,
                reply_markup=tests_keyboards.kb_check_up_start()
            )

        if answer == "get_results":
            med_id = await db.get_med_id(user_id)
            await db.delete_neuro_dialog_states(update.effective_user.id)

            if med_id:
                doc_url = await db.get_test_results(int(med_id))
                is_tests_bad = await db.get_deviations(int(med_id))

                if doc_url:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_TESTS_IS_HAS_TRUE)

                    await util_funs.write_and_sleep(update, context, 5)
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

                        await util_funs.write_and_sleep(update, context, 2)
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=TEXT_AFTER_GOOD_TESTS,
                            reply_markup=kb_after_good_tests()
                        )
                else:
                    await db.add_pending_notification(
                        med_id=int(med_id),
                        telegram_id=update.effective_user.id,
                        chat_id=update.effective_chat.id,
                        kind="decode"
                    )

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_TESTS_IS_HAS_FALSE)
                    await util_funs.write_and_sleep(update, context, 2)

                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_TESTS_MAIN_MENU,
                        reply_markup=tests_keyboards.kb_tests_main_menu()
                    )

            else:
                await db.set_neuro_dialog_states(user_id, dialog_states["get_med_id"])
                await context.bot.send_message(
                    chat_id= update.effective_chat.id,
                    text=TEXT_TESTS_GET_ID,
                )
            return

        if answer == "get_decode":
            med_id = await db.get_med_id(user_id)
            await db.delete_neuro_dialog_states(update.effective_user.id)

            if med_id:
                decode = await db.get_test_decode(int(med_id))

                if decode:
                    decode_message = f"Вот ваша расшифровка: {decode}"
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=decode_message,
                    )
                    await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
                    await write_and_sleep(update, context, 3)
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=TEXT_GET_DECODE_COMPLETE_MESSAGE,
                        reply_markup=back_navigation_keyboards.kb_back_complete_check_up()
                    )
                    return
                await db.add_pending_notification(
                    med_id=int(med_id),
                    telegram_id=update.effective_user.id,
                    chat_id=update.effective_chat.id,
                    kind="decode"
                )

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_IS_HAS_TRUE_DECODE,
                )
                await util_funs.write_and_sleep(update, context, 3)
                await send_manager_get_decode(update, context, med_id)
                await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_GET_DECODE_FINAL,
                )

            else:
                await db.set_neuro_dialog_states(user_id, dialog_states["get_med_id_decode"])
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=TEXT_TESTS_GET_ID,
                )
            return

        dialog = add("Assistant", answer)
        await db.append_answer(user_id, "Assistant", answer)

        await replace_wait_with_text(update, context, wait_msg, answer)
        return

    # ---------- COLLECT (MED / MANAGER) ----------
    elif state in (dialog_states["med_collect"], dialog_states["manager_collect"]):
        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        # >>> ДОБАВЛЕНО
        wait_msg = await send_wait_emoji(update, context, "⏳")
        # <<< ДОБАВЛЕНО

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        print(raw)
        result, data = util_funs.pars_answer_and_data(raw)

        if result == "complete":
            print("med_complete")
            if state == dialog_states["med_collect"]:
                #Отправка в группу
                text_to_manager = f"Пользователь просит помощи специалиста. У него следующая проблема :{data} \n\n(#Диалог_{update.effective_user.id}). "
                await tg_manager_chat_handlers.send_to_chat(update, context, text_to_manager)

                await complete_dialog(telegram_id= update.effective_chat.id, last_text= "Дайте знать, если вам что то понадобится!" )
                await replace_wait_with_text(
                    update, context, wait_msg,
                    "Спасибо. Я передал информацию специалисту. В ближайшее время с вами свяжутся."
                )

                await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                await asyncio.sleep(2)
                await update.message.reply_text(text="Дайте знать, если вам что то понадобится")
            else:
                await replace_wait_with_text(
                    update, context, wait_msg,
                    "Спасибо.Я передал информацию менеджеру. В ближайшее время с вами свяжутся."
                )
                await complete_dialog(telegram_id=update.effective_chat.id, last_text="Дайте знать, если вам что то понадобится!")

                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
                await asyncio.sleep(2)
                await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
                #Отправка в группу
                text_to_manager = f"Пользователь просит помощи специалиста. У него следующая проблема :{data} \n\n(#Диалог_{update.effective_user.id}). "
                await tg_manager_chat_handlers.send_to_chat(update, context, text_to_manager)

                await update.message.reply_text(text="Дайте знать, если вам что то понадобится")
            return

        elif result == "back":
            msg_text = "Ок. Дайте знать, если вам что то понадобится"
            # dialog = add("Assistant", msg_text)
            # await db.append_answer(user_id, "Assistant", msg_text)
            await complete_dialog(telegram_id=update.effective_chat.id, last_text=msg_text)
            await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
            await replace_wait_with_text(update, context, wait_msg, msg_text)
            return

        dialog = add("Assistant", result)
        await db.append_answer(user_id, "Assistant", result)
        await replace_wait_with_text(update, context, wait_msg, result)
        return

    # ---------- BOSS COLLECT ----------
    elif state == dialog_states["boss_collect"]:
        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)

        # >>> ДОБАВЛЕНО
        wait_msg = await send_wait_emoji(update, context, "⏳")
        # <<< ДОБАВЛЕНО

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=BOSS_COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )

        result, data = util_funs.pars_answer_and_data(raw)
        print(raw)

        if result == "complete":
            print("boss_complete")
            await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
            # Отправка в группу
            text_to_manager = f"Пользователь обращается к руководству. У него следующая проблема :{data} \n\n(#Диалог_{update.effective_user.id}). "
            await tg_manager_chat_handlers.send_to_chat(update, context, text_to_manager)

            await replace_wait_with_text(update, context, wait_msg, "Спасибо. Ваше обращение передано руководству.")
            await complete_dialog(telegram_id=update.effective_chat.id,
                                  last_text="Дайте знать, если вам что то понадобится!")
            return

        elif result == "back":
            msg_text = "Ок. Дайте знать, если вам что то понадобится"
            await complete_dialog(telegram_id=update.effective_chat.id,
                                  last_text=msg_text)
            await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
            await replace_wait_with_text(update, context, wait_msg, msg_text)
            return

        dialog = add("Assistant", result)
        await db.append_answer(user_id, "Assistant", result)
        await replace_wait_with_text(update, context, wait_msg, result)
        return

    else:
        await update.message.reply_text("Для начала закончите цикл с использованием кнопок☝️, а после перейдите к общению с нейро-помощником!Или используйте команду /start и попадете в главное меню!")


async def complete_dialog( telegram_id: int, last_text):
    await db.delete_dialog(telegram_id)
    await db.append_answer(telegram_id, "Assistant", last_text)



