from telegram import ReplyKeyboardMarkup
from template_manager import get_user_accessible_groups, load_groups, DAYS_OF_WEEK

def get_templates_main_keyboard():
    """Главное меню шаблонов"""
    keyboard = [
        ["📋 Список шаблонов"],
        ["➕ Добавить новый"],
        ["✏️ Редактировать"], 
        ["🗑️ Удалить"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_keyboard(user_id, action="list"):
    """Клавиатура с группами - все пользователи имеют доступ ко всем группам"""
    accessible_groups = get_user_accessible_groups(user_id)
    keyboard = []
    
    for group_id, group_data in accessible_groups.items():
        keyboard.append([f"{group_data['name']}"])
    
    if action == "list":
        keyboard.append(["🔙 К шаблонам"])
    else:
        keyboard.append(["🔙 Назад"])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Простая кнопка назад"""
    return ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True)

def get_skip_keyboard():
    """Клавиатура с пропуском"""
    return ReplyKeyboardMarkup([["⏭️ Пропустить"], ["🔙 Назад"]], resize_keyboard=True)

def get_days_keyboard(selected_days=None, is_additional=False):
    """Клавиатура выбора дней недели"""
    if selected_days is None:
        selected_days = []
    
    keyboard = []
    days_list = list(DAYS_OF_WEEK.values())
    
    # Разбиваем дни на 2 строки
    keyboard.append(days_list[:4])  # Пн-Чт
    keyboard.append(days_list[4:])  # Пт-Вс
    
    # Добавляем кнопки навигации
    if is_additional:
        # Для дополнительного выбора дней
        keyboard.append(["✅ Завершить выбор дней"])
        keyboard.append(["🔙 Назад"])
    else:
        # Для основного выбора дней
        if selected_days:
            keyboard.append(["✅ Завершить выбор дней"])
        keyboard.append(["🔙 Назад"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_days_continue_keyboard(selected_days):
    """Клавиатура после выбора первого дня"""
    keyboard = []
    
    # Основные кнопки
    keyboard.append(["➕ Выбрать еще день"])
    keyboard.append(["➡️ Перейти к следующему шагу"])
    keyboard.append(["🔙 Назад"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_frequency_keyboard():
    """Клавиатура выбора периодичности"""
    keyboard = [
        ["📅 1 в неделю"],
        ["🗓️ 2 в месяц"], 
        ["📆 1 в месяц"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_confirmation_keyboard():
    """Клавиатура подтверждения создания шаблона"""
    keyboard = [
        ["✅ Подтвердить создание"],
        ["✏️ Внести изменения"], 
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_edit_fields_keyboard():
    """Клавиатура выбора поля для редактирования"""
    keyboard = [
        ["🏷️ Название", "📝 Текст"],
        ["🖼️ Изображение", "⏰ Время"],
        ["📅 Дни отправки", "🔄 Периодичность"],
        ["✅ Завершить редактирование", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_delete_confirmation_keyboard():
    """Клавиатура подтверждения удаления"""
    keyboard = [
        ["✅ Да, удалить шаблон"],
        ["❌ Нет, отменить удаление"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)