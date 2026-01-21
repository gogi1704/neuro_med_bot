from telegram.ext import ContextTypes
from telegram import Update
from db import dialogs_db
from tg.tg_intro_handlers  import start
from telegram.constants import ChatAction

async def update_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await dialogs_db.sync_to_google_sheets()
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id,
                                   text= "База данных обновлена")

async def clear_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    user_id = update.effective_user.id
    await dialogs_db.delete_dialog(user_id)
    await dialogs_db.delete_neuro_dialog_states(user_id)

    await start(update, context)
