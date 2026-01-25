from db import dialogs_db as db
from ai import  open_ai_main
import util_funs
from ai.ai_prompts import  *
from resources import *
import asyncio
from telegram.constants import ChatAction
from telegram.error import BadRequest, RetryAfter
from tg import tg_manager_chat_handlers


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


async def handle_text_message(update, context):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    state = await db.get_neuro_dialog_states(user_id)
    dialog = await db.get_dialog(user_id) or ""

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

    if state == dialog_states_dict["get_name"]:
        await db.create_dialog_user(update.message.from_user.id, text)
        await update.message.reply_text(text=TEXT_INTRO_FINAL)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(4)

        await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
        await update.message.reply_text(text=TEXT_INTRO_SUPER_FINAL)

    elif state == dialog_states_dict["get_med_id"]:
        await db.create_dialog_user_with_med_id(update.message.from_user.id, text)
        await update.message.reply_text(text=TEXT_INTRO_FINAL)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(4)

        await db.set_neuro_dialog_states(update.message.from_user.id, dialog_states["base_speak"])
        await update.message.reply_text(text=TEXT_INTRO_SUPER_FINAL)

    # ---------- BASE ----------
    elif state == dialog_states["base_speak"]:
        print("base_speak")
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

            msg_text = "Вы хотите обратиться за помощью к специалисту. Я верно вас понял?"
            await replace_wait_with_text(update, context, wait_msg, msg_text)

            dialog = add("Assistant", msg_text)
            await db.append_answer(user_id, "Assistant", msg_text)
            return

        if answer == "get_manager":
            print("get_manager")
            await db.set_neuro_dialog_states(user_id, dialog_states["manager_collect"])

            msg_text = "Позвать менеджера?Если да, то опишите проблему, пожалуйста."
            dialog = add("Assistant", msg_text)
            await db.append_answer(user_id, "Assistant", msg_text)

            await replace_wait_with_text(update, context, wait_msg, msg_text)
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

        dialog = add("Assistant", answer)
        await db.append_answer(user_id, "Assistant", answer)

        await replace_wait_with_text(update, context, wait_msg, answer)
        return

    # ---------- COLLECT (MED / MANAGER) ----------
    elif state in (dialog_states["med_collect"], dialog_states["manager_collect"]):
        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        user_data = await db.get_user(user_id)
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
                text_to_manager = f"Пользователь: {user_data['name']} Просит помощи специалиста. У него следующая проблема :{data} \n\n(#Диалог_{update.effective_user.id}). "
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
                text_to_manager = f"Пользователь: {user_data['name']} Просит помощи специалиста. У него следующая проблема :{data} \n\n(#Диалог_{update.effective_user.id}). "
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
        user_data = await db.get_user(user_id)

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
            text_to_manager = f"Пользователь: {user_data['name']} Обращается к руководству. У него следующая проблема :{data} \n\n(#Диалог_{update.effective_user.id}). "
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


async def complete_dialog( telegram_id: int, last_text):
    await db.delete_dialog(telegram_id)
    await db.append_answer(telegram_id, "Assistant", last_text)



