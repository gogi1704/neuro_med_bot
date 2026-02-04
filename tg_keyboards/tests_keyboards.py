from datetime import datetime

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

def kb_tests_decode_empty():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Попросить лаборанта", callback_data="empty_decode_get_laborant")],
        [InlineKeyboardButton("Обратиться к менеджеру", callback_data="empty_decode_get_manager")],
    ])

def kb_check_up_start():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Ознакомиться с комплексами",url=f"https://telegra.ph/CHek-apy-po-laboratorii-OOO-CHelovek-09-10?ver={int(datetime.now().timestamp())}")],
        [InlineKeyboardButton("Добавить обследования", callback_data="сheck_up_start_add")],
        [InlineKeyboardButton("Выйти", callback_data="сheck_up_start_back")],
            ])

def kb_check_up_final():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ОК", callback_data="сheck_up_start_back")],
            ])

def kb_check_up_final_nothing():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Заново", callback_data="сheck_up_final_repeat")],
        [InlineKeyboardButton("В главное меню", callback_data="сheck_up_start_back")],
            ])
