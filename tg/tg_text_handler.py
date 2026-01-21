from telegram.ext import ContextTypes
import asyncio
import resources
from db import dialogs_db as db
from resources import dialog_states_dict
from telegram.constants import ChatAction

async def handle_text_message(update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    state = await db.get_neuro_dialog_states(update.message.from_user.id)

    if state == dialog_states_dict["get_name"]:
        await db.create_dialog_user(update.message.from_user.id, text)
        await update.message.reply_text(text= resources.TEXT_INTRO_FINAL)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(2)

        await update.message.reply_text(text=resources.TEXT_INTRO_SUPER_FINAL)

    elif state == dialog_states_dict["get_med_id"]:
        await db.create_dialog_user_with_med_id(update.message.from_user.id, text)
        await update.message.reply_text(text=resources.TEXT_INTRO_FINAL)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(2)

        await update.message.reply_text(text=resources.TEXT_INTRO_SUPER_FINAL)
