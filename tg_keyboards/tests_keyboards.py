from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def kb_tests_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 Сдать Анализы", callback_data="tests_main_menu_make_tests")],
        [InlineKeyboardButton("🧪 Получить результаты анализов", callback_data="tests_main_menu_get_tests")],
        [InlineKeyboardButton("📊 Расшифровка показателей", callback_data="tests_main_menu_get_decode")],
        [InlineKeyboardButton("🩺 Консультация врача", callback_data="tests_main_menu_consult_med")],
        [InlineKeyboardButton("🤖 Поддержка Челика", callback_data="tests_main_menu_consult_neuro")]
    ])

def kb_tests_decode():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="tests_decode_yes")],
        [InlineKeyboardButton("Нет", callback_data="tests_decode_no")],
    ])
