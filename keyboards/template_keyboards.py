from telegram import ReplyKeyboardMarkup

def get_templates_main_keyboard():
    """Главное меню шаблонов (уровень 2)"""
    keyboard = [
        ["📋 Список шаблонов", "➕ Добавить новый"],
        ["✏️ Редактировать", "🗑️ Удалить"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_template_list_menu_keyboard():
    """Меню списка шаблонов (уровень 3)"""
    keyboard = [
        ["📋 Все шаблоны", "🏷️ По группам"],
        ["🔙 К шаблонам"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_keyboard(user_id, action_type="list"):
    """Клавиатура с группами для выбора"""
    from template_manager import get_user_accessible_groups
    
    accessible_groups = get_user_accessible_groups(user_id)
    keyboard = []
    
    for group_id, group_data in accessible_groups.items():
        keyboard.append([f"🏷️ {group_data['name']}"])
    
    if action_type == "list":
        keyboard.append(["🔙 Назад"])  # Изменено с "🔙 К шаблонам" на "🔙 Назад"
    elif action_type == "create":
        keyboard.append(["🔙 Назад"])
    elif action_type == "edit":
        keyboard.append(["🔙 Назад"])
    elif action_type == "delete":
        keyboard.append(["🔙 Назад"])
    else:
        keyboard.append(["🔙 Назад"])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
def get_template_confirmation_keyboard():
    """Клавиатура подтверждения создания шаблона"""
    keyboard = [
        ["✅ Подтвердить", "✏️ Изменить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_template_edit_keyboard():
    """Клавиатура редактирования упрощенного шаблона"""
    keyboard = [
        ["🏷️ Название", "📝 Текст"],
        ["🖼️ Изображение"],
        ["✅ Завершить редактирование"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Простая кнопка назад"""
    keyboard = [
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_delete_confirmation_keyboard():
    """Клавиатура подтверждения удаления"""
    keyboard = [
        ["✅ Да, удалить", "❌ Нет, отменить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_skip_keyboard():
    """Клавиатура для пропуска"""
    keyboard = [
        ["⏭️ Пропустить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_image_choice_keyboard():
    """Клавиатура выбора изображения"""
    keyboard = [
        ["🖼️ Добавить изображение", "⏭️ Пропустить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)