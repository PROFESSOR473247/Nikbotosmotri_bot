from telegram import ReplyKeyboardMarkup
from authorized_users import is_admin

def get_more_keyboard(user_id):
    """Создает меню дополнительных функций"""
    keyboard = [
        ["📊 Статус команд", "🕒 Текущее время"],
        ["🆔 Мой ID"]
    ]

    # Добавляем кнопку управления пользователями только для администратора
    if is_admin(user_id):
        keyboard.append(["👥 Управление пользователями"])

    keyboard.append(["🔙 Главное меню"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
