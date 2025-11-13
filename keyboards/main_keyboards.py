from telegram import ReplyKeyboardMarkup
from config import REQUIRE_AUTHORIZATION
from authorized_users import is_authorized, is_admin

def get_main_keyboard(user_id):
    """Главное меню с учетом прав пользователя"""
    keyboard = [
        ["📋 Шаблоны", "📋 Задачи"],
        ["ℹ️ Помощь", "🆔 Мой ID"]
    ]
    
    # Добавляем админские функции только для админа
    if is_admin(user_id):
        keyboard.insert(1, ["⚙️ Администрирование"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_unauthorized_keyboard():
    """Меню для неавторизованных пользователей"""
    keyboard = [
        ["🆔 Получить ID"],
        ["📋 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Для доступа обратитесь к администратору")

def get_simple_keyboard(user_id):
    """Простое меню с проверкой админских прав"""
    keyboard = [
        ["📋 Шаблоны", "📋 Задачи"],
        ["ℹ️ Помощь", "🆔 Мой ID"]
    ]
    
    if is_admin(user_id):
        keyboard.insert(1, ["⚙️ Администрирование"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)