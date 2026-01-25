from dotenv import load_dotenv
from db import dialogs_db
import nest_asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import BotCommand, BotCommandScopeDefault
from db.dialogs_db import *
from ai.open_ai_main import get_gpt_answer
from tg.tg_error_handlers import error_handler
from tg.tg_intro_handlers import start, intro_agree, headache_answer, pill_answer, intro_hello_user
from tg.tg_bot_util_handlers import update_db, clear_all
from tg.tg_text_handler import handle_text_message
from tg.tg_manager_chat_handlers import *

load_dotenv()
TOKEN = os.environ.get("TG_TOKEN")

async def main():
    await dialogs_db.init_db()
    # asyncio.create_task(periodic_sync())

    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    await get_gpt_answer("test", "test", context= application)

    print('Бот запущен...')
    await application.bot.set_my_commands([
        BotCommand("start", "Старт")
        # BotCommand("clear_and_restart", "Очистить и перезапустить бот")
    ], scope=BotCommandScopeDefault())

    application.add_error_handler(error_handler)

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('update_db', update_db))
    application.add_handler(CommandHandler("clear_and_restart", clear_all))

    application.add_handler(CallbackQueryHandler(intro_agree, pattern="^intro_agree$"))
    application.add_handler(CallbackQueryHandler(
        headache_answer,
        pattern="^(headache_pill|headache_wait|headache_water|headache_ignore)$"
    ))

    application.add_handler(CallbackQueryHandler(
        pill_answer,
        pattern="^(pill_tempalgin|pill_charcoal|pill_citramon|pill_analgin)$"
    ))
    application.add_handler(CallbackQueryHandler(intro_hello_user, pattern="^intro_next$"))


    # application.add_handler(CallbackQueryHandler(handle_remind, pattern="^remind:"))

    # application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))

    application.add_handler(CallbackQueryHandler(handle_reply_button_pressed, pattern=r"^reply_to_manager\|"))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, handle_manager_reply))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))


    await application.run_polling()
    print('Бот остановлен')

if __name__ == "__main__":
    import asyncio


    nest_asyncio.apply()
    asyncio.run(main())

