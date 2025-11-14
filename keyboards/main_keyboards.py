from telegram import ReplyKeyboardMarkup
from auth_manager import auth_manager

def get_main_keyboard(user_id):
    """Главное меню бота с проверкой прав"""
    # Проверяем права пользователя
    user_role = auth_manager.get_user_role(user_id)
    
    # Базовые кнопки для всех пользователей
    keyboard = [
        ["📋 Шаблоны", "📋 Задачи"],
        ["ℹ️ Помощь", "🆔 Мой ID"]
    ]
    
    # Добавляем кнопку администрирования для администраторов
    if user_role in ['admin', 'superadmin']:
        keyboard.insert(1, ["⚙️ Администрирование"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_simple_keyboard(user_id):
    """Упрощенная клавиатура для отмены действий"""
    # ВАЖНО: Эта клавиатура должна быть такой же как главное меню
    # чтобы пользователь мог нормально вернуться
    return get_main_keyboard(user_id)

def get_admin_keyboard():
    """Клавиатура для администраторов"""
    keyboard = [
        ["👥 Пользователи", "💬 Тг чаты"],
        ["📊 Статистика", "⚙️ Настройки"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_only_keyboard():
    """Простая кнопка назад"""
    keyboard = [
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)