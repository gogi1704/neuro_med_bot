from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def kb_intro_1():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Согласен", callback_data="intro_agree")]
    ])


def kb_intro_2():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Пью таблетку", callback_data="headache_pill")],
        [InlineKeyboardButton("Жду, пока пройдёт", callback_data="headache_wait")],
        [InlineKeyboardButton("Пью воду", callback_data="headache_water")],
        [InlineKeyboardButton("Ничего не делаю", callback_data="headache_ignore")]
    ])


def kb_intro_3():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Темпалгин", callback_data="pill_tempalgin")],
        [InlineKeyboardButton("Активированный уголь", callback_data="pill_charcoal")],
        [InlineKeyboardButton("Цитрамон", callback_data="pill_citramon")],
        [InlineKeyboardButton("Анальгин", callback_data="pill_analgin")]
    ])


def kb_next():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Дальше", callback_data="intro_next")]
    ])
#
#
# def kb_next_5():
#     return InlineKeyboardMarkup([
#         [InlineKeyboardButton("Дальше", callback_data="intro_next_5")]
#     ])


def kb_finish():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Хочу Человека", callback_data="get_human")],
        [InlineKeyboardButton("Позвать менеджера", callback_data="get_manager")],
        [InlineKeyboardButton("Связь с руководителем", callback_data="get_boss")]
    ])
