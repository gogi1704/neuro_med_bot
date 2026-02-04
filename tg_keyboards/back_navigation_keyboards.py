from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def kb_back_to_main_menu():
    return InlineKeyboardMarkup([
                    [InlineKeyboardButton("Вернуться назад", callback_data="choose_type_user_tests")]
                ])

def kb_back_complete_check_up():
    return InlineKeyboardMarkup([
                    [InlineKeyboardButton("Вернуться в меню", callback_data="choose_type_user_tests")]
                ])