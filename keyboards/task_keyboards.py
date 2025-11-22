from telegram import ReplyKeyboardMarkup

def get_tasks_main_keyboard():
    """Главное меню задач (уровень 2)"""
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

def get_back_keyboard():
    """Простая кнопка назад"""
    keyboard = [
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chat_selection_keyboard(accessible_chats):
    """Клавиатура для выбора чата"""
    keyboard = []
    
    for i, chat in enumerate(accessible_chats, 1):
        keyboard.append([f"{i}. {chat['chat_name']}"])
    
    keyboard.append(["🔙 Назад"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_deactivate_confirmation_keyboard():
    """Клавиатура подтверждения деактивации"""
    keyboard = [
        ["✅ Да, отменить задачу"],
        ["❌ Нет, оставить активной"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_schedule_type_keyboard():
    """Клавиатура выбора типа расписания"""
    keyboard = [
        ["📅 По дням недели", "📆 По числам месяца"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_week_days_keyboard(selected_days=None):
    """Клавиатура выбора дней недели"""
    if selected_days is None:
        selected_days = []
    
    days = [
        "Понедельник", "Вторник", "Среда",
        "Четверг", "Пятница", "Суббота", "Воскресенье"
    ]
    
    keyboard = []
    row = []
    
    for i, day in enumerate(days):
        # Помечаем выбранные дни
        display_name = f"✅ {day}" if i in selected_days else day
        row.append(display_name)
        
        if len(row) == 2:  # 2 кнопки в строке
            keyboard.append(row)
            row = []
    
    if row:  # Добавляем последнюю неполную строку
        keyboard.append(row)
    
    # Кнопка завершения выбора
    if selected_days:
        keyboard.append(["✅ Завершить выбор дней"])
    
    keyboard.append(["🔙 Назад"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_frequency_keyboard():
    """Клавиатура выбора периодичности"""
    keyboard = [
        ["📅 1 раз в неделю", "🔄 1 раз в 2 недели"],
        ["📆 1 раз в месяц", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_task_edit_keyboard():
    """Клавиатура редактирования задачи на этапе подтверждения"""
    keyboard = [
        ["🏷️ Изменить группу", "📝 Выбрать другой шаблон"],
        ["⚙️ Изменить настройки шаблона", "💬 Изменить чат"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_template_edit_keyboard():
    """Клавиатура редактирования шаблона (используется из template_keyboards)"""
    from keyboards.template_keyboards import get_template_edit_keyboard as get_template_edit_kb
    return get_template_edit_kb()