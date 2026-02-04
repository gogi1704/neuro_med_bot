from dotenv import load_dotenv
from db import dialogs_db
import nest_asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import BotCommand, BotCommandScopeDefault
from db.dialogs_db import *
from ai.open_ai_main import get_gpt_answer
from tg.tg_error_handlers import error_handler
from tg.tg_intro_handlers import start, choose_user_type, handle_choose_user, handle_headache, handle_send_chelik_info, handle_pill_answer
from tg.tg_bot_util_handlers import update_db, clear_all
from tg.tg_text_handler import handle_text_message
from tg.tg_manager_chat_handlers import *
from tg.tg_tests_line_handlers import handle_test_main_menu, handle_decode_yes_no, handle_after_good_tests_yes_no, handle_empty_decode
from util_funs import setup_jobs
from tg.tg_check_up_handlers import handle_start_check_up, handle_toggle, handle_final_check_up
load_dotenv()
TOKEN = os.environ.get("TG_TOKEN")

async def main():
    await dialogs_db.init_db()
    asyncio.create_task(periodic_sync())

    application = Application.builder().token(TOKEN).concurrent_updates(True).build()
    setup_jobs(application)
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


    application.add_handler(CallbackQueryHandler(handle_choose_user,pattern="^choose_type_user_"))
    application.add_handler(CallbackQueryHandler(handle_test_main_menu,pattern="^tests_main_menu_"))
    application.add_handler(CallbackQueryHandler(choose_user_type, pattern="^intro_agree$"))
    application.add_handler(CallbackQueryHandler(handle_headache,pattern="^headache_"))
    application.add_handler(CallbackQueryHandler(handle_decode_yes_no, pattern="^tests_decode_"))
    application.add_handler(CallbackQueryHandler(handle_empty_decode, pattern="^empty_decode_"))

    application.add_handler(CallbackQueryHandler(handle_start_check_up, pattern="^сheck_up_start_"))
    application.add_handler(CallbackQueryHandler(handle_final_check_up, pattern="^сheck_up_final_"))

    application.add_handler(CallbackQueryHandler(handle_toggle, pattern="^(toggle:|done)"))

    application.add_handler(CallbackQueryHandler(handle_after_good_tests_yes_no, pattern="^after_good_tests_"))
    application.add_handler(CallbackQueryHandler(handle_pill_answer,pattern="^pill_"))
    application.add_handler(CallbackQueryHandler(handle_send_chelik_info, pattern="^intro_next$"))

    application.add_handler(CallbackQueryHandler(handle_reply_button_pressed, pattern=r"^reply_to_manager\|"))
    application.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, handle_manager_reply))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))


    await application.run_polling()
    print('Бот остановлен')

if __name__ == "__main__":
    import asyncio


    nest_asyncio.apply()
    asyncio.run(main())

