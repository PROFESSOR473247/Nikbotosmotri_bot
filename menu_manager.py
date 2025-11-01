from telegram import ReplyKeyboardMarkup
from authorized_users import is_authorized, is_admin, get_user_role

def get_main_menu(user_id):
    """Главное меню в зависимости от роли"""
    if not is_authorized(user_id):
        return get_guest_keyboard()
    
    user_role = get_user_role(user_id)
    
    if user_role == "admin":
        return get_admin_keyboard()
    elif user_role == "руководитель":
        return get_manager_keyboard()
    elif user_role == "водитель":
        return get_driver_keyboard()
    else:  # гость
        return get_guest_keyboard()

def get_guest_keyboard():
    """ТОЛЬКО кнопка Получить ID для гостей"""
    keyboard = [
        ["🆔 Получить ID"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_admin_keyboard():
    """Меню администратора"""
    keyboard = [
        ["📋 Задачи", "📁 Шаблоны"],
        ["👥 Пользователи", "🏘️ Группы"],
        ["ℹ️ Еще"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_manager_keyboard():
    """Меню руководителя"""
    keyboard = [
        ["📋 Задачи", "📁 Шаблоны"],
        ["🏘️ Группы", "ℹ️ Еще"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_driver_keyboard():
    """Меню водителя"""
    keyboard = [
        ["📋 Задачи", "ℹ️ Еще"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_unauthorized_keyboard():
    """Псевдоним для гостевой клавиатуры"""
    return get_guest_keyboard()

def get_templates_menu():
    """Меню шаблонов"""
    keyboard = [
        ["📋 Список шаблонов", "➕ Добавить новый"],
        ["✏️ Редактировать", "🗑️ Удалить"],
        ["🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_tasks_menu():
    """Меню задач"""
    keyboard = [
        ["📝 Создать задачу", "❌ Отменить задачу"],
        ["🧪 Тестирование", "📊 Статус задач"],
        ["🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_users_menu():
    """Меню пользователей (только админ)"""
    keyboard = [
        ["➕ Добавить", "✏️ Изменить доступ"],
        ["📋 Список пользователей", "🗑️ Удалить"],
        ["🧪 Тест прав", "🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_menu(user_id):
    """Меню групп"""
    if is_admin(user_id):
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
    """Дополнительное меню"""
    if not is_authorized(user_id):
        return get_guest_keyboard()
    
    user_role = get_user_role(user_id)
    
    if user_role in ["admin", "руководитель", "водитель"]:
        keyboard = [
            ["📊 Статус задач", "🕒 Текущее время"],
            ["🆔 Мой ID", "🔙 Назад в главное меню"]
        ]
    else:
        return get_guest_keyboard()
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Кнопка Назад"""
    return ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True)

def get_confirmation_keyboard():
    """Клавиатура подтверждения"""
    return ReplyKeyboardMarkup([["✅ Да", "❌ Нет"], ["🔙 Назад"]], resize_keyboard=True)
