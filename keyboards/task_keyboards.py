from telegram import ReplyKeyboardMarkup

def get_tasks_main_keyboard():
    """Главное меню задач"""
    keyboard = [
        ["➕ Создать задачу", "🗑️ Отменить задачу"],
        ["🧪 Тестирование", "📊 Статус задач"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_keyboard(user_id, action_type="task"):
    """Клавиатура выбора групп для задач"""
    from template_manager import get_user_accessible_groups
    
    accessible_groups = get_user_accessible_groups(user_id)
    keyboard = []
    
    for group_data in accessible_groups.values():
        keyboard.append([f"🏷️ {group_data['name']}"])
    
    if action_type == "task":
        keyboard.append(["🔙 К задачам"])
    elif action_type == "deactivate":
        keyboard.append(["🔙 К задачам"])
    elif action_type == "test":
        keyboard.append(["🔙 К задачам"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_task_confirmation_keyboard():
    """Клавиатура подтверждения создания задачи"""
    keyboard = [
        ["✅ Подтвердить", "✏️ Изменить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_task_edit_keyboard():
    """Клавиатура редактирования задачи"""
    keyboard = [
        ["🏷️ Изменить группу", "📝 Выбрать другой шаблон"],
        ["⚙️ Изменить настройки шаблона"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Простая кнопка назад"""
    keyboard = [
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)