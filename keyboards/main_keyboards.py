from telegram import ReplyKeyboardMarkup
from config import REQUIRE_AUTHORIZATION
from authorized_users import is_authorized, is_admin

def get_main_keyboard():
    """Главное меню для всех пользователей"""
    keyboard = [
        ["📋 Шаблоны"],  # Основная функция
        ["ℹ️ Помощь", "🆔 Мой ID"]
    ]
    
    # Добавляем админские функции только для админа
    if is_admin(812934047):  # Ваш ID как администратора
        keyboard.insert(1, ["👥 Пользователи", "⚙️ Настройки"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_unauthorized_keyboard():
    """Меню для неавторизованных пользователей (не используется при REQUIRE_AUTHORIZATION=False)"""
    keyboard = [
        ["🆔 Получить ID"],
        ["📋 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Для доступа обратитесь к администратору")

def get_simple_keyboard():
    """Простое меню без проверки авторизации"""
    keyboard = [
        ["📋 Шаблоны"],
        ["ℹ️ Помощь", "🆔 Мой ID"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)