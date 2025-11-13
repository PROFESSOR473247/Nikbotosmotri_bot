from telegram import ReplyKeyboardMarkup

def get_templates_main_keyboard():
    """Главное меню шаблонов"""
    keyboard = [
        ["➕ Создать шаблон", "📋 Список шаблонов"],
        ["✏️ Редактировать шаблон", "🗑️ Удалить шаблон"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_keyboard(user_id, action_type="create"):
    """Клавиатура с группами для выбора"""
    from template_manager import get_user_accessible_groups
    
    accessible_groups = get_user_accessible_groups(user_id)
    keyboard = []
    
    for group_id, group_data in accessible_groups.items():
        keyboard.append([group_data['name']])
    
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
    """Клавиатура редактирования шаблона"""
    keyboard = [
        ["🏷️ Изменить название", "📝 Изменить текст"],
        ["🖼️ Изменить изображение", "⏰ Изменить время"],
        ["📅 Изменить дни", "🔄 Изменить периодичность"],
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

def get_days_keyboard():
    """Клавиатура выбора дней недели"""
    keyboard = [
        ["Понедельник", "Вторник", "Среда"],
        ["Четверг", "Пятница", "Суббота"],
        ["Воскресенье", "✅ Завершить выбор"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_frequency_keyboard():
    """Клавиатура выбора периодичности"""
    keyboard = [
        ["1 в неделю", "2 в месяц"],
        ["1 в месяц", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_template_list_keyboard():
    """Клавиатура для списка шаблонов"""
    keyboard = [
        ["📋 Показать все шаблоны", "🏷️ По группам"],
        ["🔍 Поиск шаблона", "🔙 К шаблонам"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_template_details_keyboard():
    """Клавиатура для деталей шаблона"""
    keyboard = [
        ["✏️ Редактировать", "🗑️ Удалить"],
        ["🔙 К списку"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_delete_confirmation_keyboard():
    """Клавиатура подтверждения удаления"""
    keyboard = [
        ["✅ Да, удалить", "❌ Нет, отменить"],
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

def get_time_input_keyboard():
    """Клавиатура для ввода времени"""
    keyboard = [
        ["⏭️ Пропустить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_frequency_types_keyboard():
    """Клавиатура типов периодичности"""
    keyboard = [
        ["1 в неделю", "2 в месяц"],
        ["1 в месяц", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_edit_choice_keyboard():
    """Клавиатура выбора редактирования"""
    keyboard = [
        ["🏷️ Название", "📝 Текст", "🖼️ Изображение"],
        ["⏰ Время", "📅 Дни", "🔄 Периодичность"],
        ["✅ Завершить", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)