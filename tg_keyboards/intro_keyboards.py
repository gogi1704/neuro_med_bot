from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def kb_intro_1():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Согласен", callback_data="intro_agree")]
    ])


def kb_headache_pills():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Пью таблетку", callback_data="headache_pill")],
        [InlineKeyboardButton("Жду, пока пройдёт", callback_data="headache_wait")],
        [InlineKeyboardButton("Пью воду", callback_data="headache_water")],
        [InlineKeyboardButton("Ничего не делаю", callback_data="headache_ignore")]
    ])

def kb_choose_user_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 Анализы (уже были или планирую)", callback_data="choose_type_user_tests")],
        [InlineKeyboardButton("🩺 Медосмотр (уже был или планирую)", callback_data="choose_type_user_anamnez")],
        [InlineKeyboardButton("👤 Я здесь впервые", callback_data="choose_type_user_newUser")]
    ])


def kb_pills():
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

def kb_after_good_tests():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Хочу", callback_data="after_good_tests_yes")],
        [InlineKeyboardButton("Нет, спасибо", callback_data="after_good_tests_no")]
    ])

def kb_new_user():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🩺 Консультация врача", callback_data="tests_main_menu_consult_med")],
        [InlineKeyboardButton("🤖 Поддержка Челика", callback_data="tests_main_menu_consult_neuro")]
    ])

def kb_else_text():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Закончить и открыть главное меню", callback_data="choose_type_user_tests")]
    ])