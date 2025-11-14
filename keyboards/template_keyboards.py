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
        ["🏷️ Название", "📝 Текст"],
        ["🖼️ Изображение", "⏰ Время"],
        ["📅 Дни отправки", "🔄 Периодичность"],
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

def get_days_keyboard(selected_days=None, is_additional=False):
    """Клавиатура выбора дней недели"""
    if selected_days is None:
        selected_days = []
    
    days = {
        '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
        '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
    }
    
    keyboard = []
    row = []
    
    for day_num, day_name in days.items():
        # Помечаем выбранные дни
        display_name = f"✅ {day_name}" if day_num in selected_days else day_name
        row.append(display_name)
        
        if len(row) == 2:  # 2 кнопки в строке
            keyboard.append(row)
            row = []
    
    if row:  # Добавляем последнюю неполную строку
        keyboard.append(row)
    
    # Кнопки действий
    if is_additional:
        keyboard.append(["✅ Завершить выбор дней"])
    else:
        if selected_days:
            keyboard.append(["✅ Завершить выбор дней"])
        else:
            keyboard.append(["➕ Выбрать еще день"])
    
    keyboard.append(["🔙 Назад"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_frequency_keyboard():
    """Клавиатура выбора периодичности"""
    keyboard = [
        ["📅 1 в неделю", "🗓️ 2 в месяц"],
        ["📆 1 в месяц", "🔙 Назад"]
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