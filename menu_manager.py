from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from authorized_users import get_user_role, is_admin, get_user_info
from database import get_user_accessible_groups, load_groups

def get_main_menu(user_id):
    """Get main menu based on user role"""
    user_info = get_user_info(user_id)
    
    if not user_info:  # User not authorized
        return get_guest_keyboard()
    
    user_role = user_info.get('role', 'гость')
    
    if user_role == "admin":
        keyboard = [
            ["📋 Задачи", "📁 Шаблоны"],
            ["👥 Пользователи", "🏘️ Группы"],
            ["ℹ️ Еще"]
        ]
    elif user_role == "руководитель":
        keyboard = [
            ["📋 Задачи", "📁 Шаблоны"],
            ["🏘️ Группы", "ℹ️ Еще"]
        ]
    elif user_role == "водитель":
        keyboard = [
            ["📋 Задачи", "ℹ️ Еще"]
        ]
    else:  # гость - минимальные права
        return get_guest_keyboard()
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_guest_keyboard():
    """Keyboard for guests - only Get ID button"""
    keyboard = [
        ["🆔 Получить ID"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_unauthorized_keyboard():
    """Alias for guest keyboard"""
    return get_guest_keyboard()

def get_templates_menu():
    """Get templates management menu"""
    keyboard = [
        ["📋 Список шаблонов", "➕ Добавить новый"],
        ["✏️ Редактировать", "🗑️ Удалить"],
        ["🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_tasks_menu():
    """Get tasks management menu"""
    keyboard = [
        ["📝 Создать задачу", "❌ Отменить задачу"],
        ["🧪 Тестирование", "📊 Статус задач"],
        ["🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_users_menu():
    """Get users management menu (admin only)"""
    keyboard = [
        ["➕ Добавить", "✏️ Изменить доступ"],
        ["📋 Список пользователей", "🗑️ Удалить"],
        ["🧪 Тест прав", "🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_menu(user_id):
    """Get groups management menu"""
    user_role = get_user_role(user_id)
    
    if user_role == "admin":
        keyboard = [
            ["📋 Список групп", "➕ Создать группу"],
            ["📁 Создать подгруппу", "✏️ Изменить доступ"],
            ["🗑️ Удалить группу", "🗑️ Удалить подгруппу"],
            ["🔙 Назад в главное меню"]
        ]
    else:  # руководитель
        keyboard = [
            ["📁 Создать подгруппу", "🗑️ Удалить подгруппу"],
            ["🔙 Назад в главное меню"]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_more_menu(user_id):
    """Get more options menu based on role"""
    user_role = get_user_role(user_id)
    
    if user_role in ["admin", "руководитель"]:
        keyboard = [
            ["📊 Статус задач", "🕒 Текущее время"],
            ["🆔 Мой ID", "🔙 Назад в главное меню"]
        ]
    elif user_role == "водитель":
        keyboard = [
            ["📊 Статус задач", "🕒 Текущее время"],
            ["🆔 Мой ID", "🔙 Назад в главное меню"]
        ]
    else:  # гость
        return get_guest_keyboard()
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_group_selection_keyboard(user_id):
    """Keyboard for group selection"""
    accessible_groups = get_user_accessible_groups(user_id)
    keyboard = []
    
    for group_id, group_info in accessible_groups.items():
        keyboard.append([f"🏘️ {group_info.get('title', f'Группа {group_id}')}"])
    
    keyboard.append(["🔙 Назад"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Simple back keyboard"""
    return ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True)

def get_confirmation_keyboard():
    """Confirmation keyboard"""
    return ReplyKeyboardMarkup([["✅ Да", "❌ Нет"], ["🔙 Назад"]], resize_keyboard=True)

def get_days_keyboard():
    """Days of week keyboard"""
    return ReplyKeyboardMarkup([
        ["Пн", "Вт", "Ср", "Чт"],
        ["Пт", "Сб", "Вс"],
        ["🔙 Назад"]
    ], resize_keyboard=True)

def get_frequency_keyboard():
    """Frequency selection keyboard"""
    return ReplyKeyboardMarkup([
        ["2 в неделю", "1 в неделю"],
        ["2 в месяц", "1 в месяц"],
        ["🔙 Назад"]
    ], resize_keyboard=True)

def get_edit_template_keyboard():
    """Template editing options keyboard"""
    return ReplyKeyboardMarkup([
        ["🏘️ Группу", "📝 Текст"],
        ["🖼️ Изображение", "🕒 Время"],
        ["📅 Периодичность", "🔙 Назад"]
    ], resize_keyboard=True)

def get_image_options_keyboard():
    """Image options keyboard"""
    return ReplyKeyboardMarkup([
        ["📎 Прикрепить изображение", "⏭️ Пропустить"],
        ["🔙 Назад"]
    ], resize_keyboard=True)
