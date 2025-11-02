# -*- coding: utf-8 -*-
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from database import is_authorized, is_admin, get_user_role
from user_roles import can_manage_users, can_manage_groups, can_create_templates

def get_main_menu(user_id):
    """Главное меню в зависимости от роли"""
    if not is_authorized(user_id):
        return get_guest_keyboard()
    
    # Проверяем, тестирует ли администратор другую роль
    from telegram.ext import ContextTypes
    import asyncio
    
    user_role = get_user_role(user_id)
    
    # Если администратор тестирует другую роль
    if is_admin(user_id):
        # Здесь мы не имеем доступа к context, поэтому используем глобальный флаг
        # В реальной реализации это должно быть через context.user_data
        # Пока оставляем стандартное меню администратора
        return get_admin_keyboard()
    
    if user_role == "admin":
        return get_admin_keyboard()
    elif user_role == "руководитель":
        return get_manager_keyboard()
    elif user_role == "водитель":
        return get_driver_keyboard()
    else:  # гость
        return get_guest_keyboard()

def get_guest_keyboard():
    """Меню для гостей"""
    keyboard = [
        ["🆔 Получить ID", "❓ Помощь"]
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

def get_testing_role_keyboard(original_role):
    """Меню при тестировании роли с кнопкой возврата"""
    if original_role == "admin":
        keyboard = [
            ["📋 Задачи", "📁 Шаблоны"],
            ["🏘️ Группы", "ℹ️ Еще"],
            ["👑 Назад к админ"]
        ]
    elif original_role == "руководитель":
        keyboard = [
            ["📋 Задачи", "📁 Шаблоны"],
            ["🏘️ Группы", "ℹ️ Еще"],
            ["👑 Назад к админ"]
        ]
    else:
        keyboard = [
            ["📋 Задачи", "ℹ️ Еще"],
            ["👑 Назад к админ"]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_templates_menu(user_id):
    """Меню шаблонов"""
    user_role = get_user_role(user_id)
    
    if not can_create_templates(user_role):
        keyboard = [
            ["📋 Список шаблонов"],
            ["🔙 Назад в главное меню"]
        ]
    else:
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

def get_users_menu(user_id):
    """Меню пользователей (только админ)"""
    if not is_admin(user_id):
        return get_main_menu(user_id)
        
    keyboard = [
        ["➕ Добавить", "✏️ Изменить доступ"],
        ["📋 Список пользователей", "🗑️ Удалить"],
        ["🧪 Тест прав", "🔙 Назад в главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_groups_menu(user_id):
    """Меню групп"""
    user_role = get_user_role(user_id)
    
    if is_admin(user_id):
        keyboard = [
            ["📋 Список групп", "➕ Создать группу"],
            ["📁 Создать подгруппу", "✏️ Изменить доступ"],
            ["🗑️ Удалить группу", "🗑️ Удалить подгруппу"],
            ["🔙 Назад в главное меню"]
        ]
    elif user_role == "руководитель":
        keyboard = [
            ["📁 Создать подгруппу", "🗑️ Удалить подгруппу"],
            ["🔙 Назад в главное меню"]
        ]
    else:
        keyboard = [
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

def get_back_button():
    """Кнопка возврата"""
    return [InlineKeyboardButton("🔙 Назад", callback_data="back")]

def get_pagination_buttons(page, total_pages, prefix):
    """Кнопки пагинации"""
    buttons = []
    if total_pages > 1:
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_page_{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"{prefix}_page_{page+1}"))
    return buttons

def get_groups_keyboard(groups, page=0, groups_per_page=8):
    """Клавиатура для выбора групп"""
    start_idx = page * groups_per_page
    end_idx = start_idx + groups_per_page
    groups_page = list(groups.items())[start_idx:end_idx]
    
    keyboard = []
    for group_id, group_info in groups_page:
        keyboard.append([InlineKeyboardButton(
            f"🏘️ {group_info.get('name', group_id)}", 
            callback_data=f"select_group_{group_id}"
        )])
    
    # Добавляем пагинацию
    total_pages = (len(groups) + groups_per_page - 1) // groups_per_page
    pagination_buttons = get_pagination_buttons(page, total_pages, "groups")
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append(get_back_button())
    
    return InlineKeyboardMarkup(keyboard)

def get_subgroups_keyboard(subgroups, group_id, page=0, subgroups_per_page=8):
    """Клавиатура для выбора подгрупп"""
    if not subgroups:
        return InlineKeyboardMarkup([get_back_button()])
    
    start_idx = page * subgroups_per_page
    end_idx = start_idx + subgroups_per_page
    subgroups_page = list(subgroups.items())[start_idx:end_idx]
    
    keyboard = []
    for subgroup_id, subgroup_name in subgroups_page:
        keyboard.append([InlineKeyboardButton(
            f"📁 {subgroup_name}", 
            callback_data=f"select_subgroup_{group_id}_{subgroup_id}"
        )])
    
    # Добавляем пагинацию
    total_pages = (len(subgroups) + subgroups_per_page - 1) // subgroups_per_page
    pagination_buttons = get_pagination_buttons(page, total_pages, f"subgroups_{group_id}")
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append(get_back_button())
    
    return InlineKeyboardMarkup(keyboard)

def get_templates_keyboard(templates, page=0, templates_per_page=8):
    """Клавиатура для выбора шаблонов"""
    start_idx = page * templates_per_page
    end_idx = start_idx + templates_per_page
    templates_page = list(templates.items())[start_idx:end_idx]
    
    keyboard = []
    for template_id, template_info in templates_page:
        keyboard.append([InlineKeyboardButton(
            f"📝 {template_info.get('name', 'Без названия')}", 
            callback_data=f"select_template_{template_id}"
        )])
    
    # Добавляем пагинацию
    total_pages = (len(templates) + templates_per_page - 1) // templates_per_page
    pagination_buttons = get_pagination_buttons(page, total_pages, "templates")
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append(get_back_button())
    
    return InlineKeyboardMarkup(keyboard)

def get_tasks_keyboard(tasks, page=0, tasks_per_page=8):
    """Клавиатура для выбора задач"""
    start_idx = page * tasks_per_page
    end_idx = start_idx + tasks_per_page
    tasks_page = list(tasks.items())[start_idx:end_idx]
    
    keyboard = []
    for task_id, task_info in tasks_page:
        keyboard.append([InlineKeyboardButton(
            f"📋 {task_info.get('template_name', 'Без названия')}", 
            callback_data=f"select_task_{task_id}"
        )])
    
    # Добавляем пагинацию
    total_pages = (len(tasks) + tasks_per_page - 1) // tasks_per_page
    pagination_buttons = get_pagination_buttons(page, total_pages, "tasks")
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append(get_back_button())
    
    return InlineKeyboardMarkup(keyboard)

def get_roles_keyboard():
    """Клавиатура для выбора ролей"""
    from user_roles import USER_ROLES
    
    keyboard = []
    for role_key, role_data in USER_ROLES.items():
        if role_key != "admin":  # Админа нельзя выбрать при создании
            keyboard.append([InlineKeyboardButton(
                role_data["name"],
                callback_data=f"select_role_{role_key}"
            )])
    
    keyboard.append(get_back_button())
    return InlineKeyboardMarkup(keyboard)

def get_test_roles_keyboard():
    """Клавиатура для тестирования ролей"""
    from user_roles import USER_ROLES
    
    keyboard = []
    for role_key, role_data in USER_ROLES.items():
        keyboard.append([InlineKeyboardButton(
            role_data["name"],
            callback_data=f"test_role_{role_key}"
        )])
    
    keyboard.append(get_back_button())
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(confirm_data, cancel_data):
    """Клавиатура подтверждения"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=confirm_data),
            InlineKeyboardButton("❌ Нет", callback_data=cancel_data)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_edit_template_keyboard():
    """Клавиатура для редактирования шаблона"""
    keyboard = [
        [InlineKeyboardButton("🏘️ Группу", callback_data="edit_field_group")],
        [InlineKeyboardButton("📁 Подгруппу", callback_data="edit_field_subgroup")],
        [InlineKeyboardButton("📝 Текст", callback_data="edit_field_text")],
        [InlineKeyboardButton("🖼️ Изображение", callback_data="edit_field_image")],
        [InlineKeyboardButton("⏰ Время", callback_data="edit_field_time")],
        [InlineKeyboardButton("🔄 Периодичность", callback_data="edit_field_frequency")],
        get_back_button()[0]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_days_keyboard():
    """Клавиатура для выбора дней недели"""
    days = {
        "monday": "Понедельник",
        "tuesday": "Вторник", 
        "wednesday": "Среда",
        "thursday": "Четверг",
        "friday": "Пятница",
        "saturday": "Суббота",
        "sunday": "Воскресенье"
    }
    
    keyboard = []
    row = []
    for day_key, day_name in days.items():
        row.append(InlineKeyboardButton(day_name, callback_data=f"select_day_{day_key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append(get_back_button())
    return InlineKeyboardMarkup(keyboard)

def get_frequency_keyboard():
    """Клавиатура для выбора периодичности"""
    keyboard = [
        [InlineKeyboardButton("2 раза в неделю", callback_data="frequency_2_week")],
        [InlineKeyboardButton("1 раз в неделю", callback_data="frequency_1_week")],
        [InlineKeyboardButton("2 раза в месяц", callback_data="frequency_2_month")],
        [InlineKeyboardButton("1 раз в месяц", callback_data="frequency_1_month")],
        get_back_button()[0]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_users_list_keyboard(users, page=0, users_per_page=8):
    """Клавиатура для выбора пользователей"""
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    users_page = list(users.items())[start_idx:end_idx]
    
    keyboard = []
    for user_id, user_info in users_page:
        keyboard.append([InlineKeyboardButton(
            f"👤 {user_info.get('name', f'User_{user_id}')}", 
            callback_data=f"select_user_{user_id}"
        )])
    
    # Добавляем пагинацию
    total_pages = (len(users) + users_per_page - 1) // users_per_page
    pagination_buttons = get_pagination_buttons(page, total_pages, "users")
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append(get_back_button())
    
    return InlineKeyboardMarkup(keyboard)

def get_edit_user_keyboard():
    """Клавиатура для редактирования пользователя"""
    keyboard = [
        [InlineKeyboardButton("🎭 Изменить должность", callback_data="edit_user_role")],
        [InlineKeyboardButton("🏘️ Изменить группы доступа", callback_data="edit_user_groups")],
        get_back_button()[0]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_group_access_keyboard():
    """Клавиатура для управления доступом к группе"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить пользователя", callback_data="group_access_add")],
        [InlineKeyboardButton("➖ Удалить пользователя", callback_data="group_access_remove")],
        get_back_button()[0]
    ]
    return InlineKeyboardMarkup(keyboard)
