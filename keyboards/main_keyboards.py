from telegram import ReplyKeyboardMarkup
from authorized_users import is_authorized, is_admin

def get_main_keyboard():
    """Создает главное меню для авторизованных пользователей"""
    keyboard = [
        ["📋 Шаблоны"],
        ["🧪 Тестирование"],
        ["⚙️ ЕЩЕ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Выберите раздел...")

def get_unauthorized_keyboard():
    """Создает меню для неавторизованных пользователей"""
    keyboard = [
        ["🆔 Получить ID"],
        ["📋 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Для доступа обратитесь к администратору")
