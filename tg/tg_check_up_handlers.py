from telegram import InlineKeyboardMarkup, InlineKeyboardButton
import resources
from resources import *
from tg_keyboards import tests_keyboards
from doc_funs import *
from util_funs import get_list_and_price

async def handle_start_check_up(update, context):
    q = update.callback_query
    message = q.message
    await q.answer()
    if q.data == "сheck_up_start_back" :
        await context.bot.send_message(
                chat_id=q.from_user.id,
                text=TEXT_TESTS_MAIN_MENU,
                reply_markup= tests_keyboards.kb_tests_main_menu()
            )
    elif q.data == "сheck_up_start_add" :
        await choose_tests(update, context)
        await message.delete()

async def handle_final_check_up(update, context):
    q = update.callback_query
    message = q.message
    await q.answer()
    if q.data == "сheck_up_final_repeat":
        await message.delete()
        await choose_tests(update, context)

def get_tests_keyboard(selected_tests: set):
    keyboard = []

    for idx, test in enumerate(resources.TESTS):
        # текст кнопки
        text = test
        if test in selected_tests:
            text = f"✅ *{test}*"   # жирный + галочка

        # callback_data используем короткий ID (индекс), а не весь текст
        callback_data = f"toggle:{idx}"

        # длинные названия — в отдельном ряду, короткие можно по 2
        if len(test) > 15:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        else:
            if not keyboard or len(keyboard[-1]) == 2 or "ГОТОВО" in keyboard[-1][0].text:
                keyboard.append([])
            keyboard[-1].append(InlineKeyboardButton(text, callback_data=callback_data))

    # кнопка "ГОТОВО" внизу
    keyboard.append([InlineKeyboardButton("ГОТОВО", callback_data="done")])
    return InlineKeyboardMarkup(keyboard)

async def choose_tests(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["selected_tests"] = set()  # список выбранных сбрасываем

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=resources.TEXT_CHOOSE_TESTS,
        reply_markup=get_tests_keyboard(context.user_data["selected_tests"]),
        parse_mode="Markdown"
    )

async def handle_toggle(update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    message = query.message
    await query.answer()

    if "selected_tests" not in context.user_data:
        context.user_data["selected_tests"] = set()

    data = query.data

    if data.startswith("toggle:"):
        idx = int(data.split(":", 1)[1])  # достаём индекс
        test = resources.TESTS[idx]       # получаем название теста

        if test in context.user_data["selected_tests"]:
            context.user_data["selected_tests"].remove(test)
        else:
            context.user_data["selected_tests"].add(test)

        # обновляем клавиатуру
        await query.edit_message_reply_markup(
            reply_markup=get_tests_keyboard(context.user_data["selected_tests"])
        )

    elif data == "done":
        chosen = ", ".join(context.user_data["selected_tests"]) or "ничего"

        if "dop_message_id" in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data["dop_message_id"]
                )
                await query.message.delete()
            except Exception as e:
                print(f"Не удалось удалить сообщение с вопросом: {e}")

        text, price = await get_list_and_price(list_tests=context.user_data["selected_tests"] , tests_price= resources.TESTS_PRICE)
        # Удаляем сообщение с кнопками
        await message.delete()
        if chosen == "ничего":
            await query.message.reply_text(text= "Вы не выбрали никаких обследований. Если хотите, добавить то попробуйте заново!",
                                           parse_mode="HTML",
                                           reply_markup=tests_keyboards.kb_check_up_final_nothing())
        else:
            await query.message.reply_text(text=resources.get_final_text_tests_with_price2(tests=text, price = price),
                                           parse_mode= "HTML",
                                           reply_markup= tests_keyboards.kb_check_up_final() )
