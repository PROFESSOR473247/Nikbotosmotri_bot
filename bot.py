import logging
import asyncio
import os
import sys
import datetime
import pytz
import threading
import time
import requests
from datetime import timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    JobQueue
)

# Импорты конфигурации и пользователей
from config import BOT_TOKEN
from authorized_users import is_authorized, is_admin, add_user, remove_user, get_users_list, get_admin_id, get_user_groups, update_user_groups

# Импорты системы шаблонов
from template_manager import (
    get_user_accessible_groups, create_template, update_template, 
    delete_template, get_template, get_templates_by_group,
    save_image, format_template_info, DAYS_OF_WEEK, FREQUENCY_TYPES,
    load_groups, load_templates
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Состояния для ConversationHandler
(
    TEMPLATES_MAIN, TEMPLATE_LIST_GROUPS, TEMPLATE_LIST_SUBGROUPS, TEMPLATE_LIST_TEMPLATES,
    ADD_TEMPLATE_GROUP, ADD_TEMPLATE_SUBGROUP, ADD_TEMPLATE_NAME, ADD_TEMPLATE_TEXT,
    ADD_TEMPLATE_IMAGE, ADD_TEMPLATE_TIME, ADD_TEMPLATE_DAYS, ADD_TEMPLATE_FREQUENCY,
    ADD_TEMPLATE_SECOND_DAY, ADD_TEMPLATE_CONFIRM, EDIT_TEMPLATE_FIELD,
    EDIT_TEMPLATE_GROUP, EDIT_TEMPLATE_TEXT, EDIT_TEMPLATE_IMAGE, EDIT_TEMPLATE_TIME,
    EDIT_TEMPLATE_DAYS, EDIT_TEMPLATE_FREQUENCY, DELETE_TEMPLATE_CONFIRM,
    USER_MANAGEMENT_MAIN, USER_MANAGEMENT_ADD, USER_MANAGEMENT_REMOVE, USER_MANAGEMENT_LIST
) = range(26)

# Глобальные переменные для заданий
active_jobs = {}
test_jobs = {}

# Декоратор для проверки авторизации
def authorization_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            await update.message.reply_text(
                "❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n"
                "Для доступа к функциям бота обратитесь к администратору",
                reply_markup=get_unauthorized_keyboard()
            )
            print(f"🚫 Неавторизованный доступ от user_id: {user_id} к функции: {func.__name__}")
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

# Декоратор для проверки прав администратора
def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text(
                "❌ Эта функция доступна только администратору",
                reply_markup=get_main_keyboard()
            )
            print(f"🚫 Попытка доступа к админ-функции от user_id: {user_id}")
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

# Клавиатуры
def get_main_keyboard():
    """Создает главное меню для авторизованных пользователей"""
    keyboard = [
        ["📋 Шаблоны"],
        ["🧪 Тестирование"],
        ["⚙️ ЕЩЕ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Выберите раздел...")

def get_unauthorized_keyboard():
    """Создает меню для неавторизованных пользователей"""
    keyboard = [
        ["🆔 Получить ID"],
        ["📋 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Для доступа обратитесь к администратору")

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
    """Клавиатура с группами пользователя"""
    accessible_groups = get_user_accessible_groups(user_id)
    keyboard = []
    
    for group_id, group_data in accessible_groups.items():
        keyboard.append([f"{group_data['name']}"])
    
    if action == "list":
        keyboard.append(["🔙 К шаблонам"])
    else:
        keyboard.append(["🔙 Назад"])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_subgroups_keyboard(group_id, action="list"):
    """Клавиатура с подгруппами группы"""
    groups_data = load_groups()
    group_data = groups_data['groups'].get(group_id, {})
    subgroups = group_data.get('subgroups', {})
    
    keyboard = []
    for subgroup_id, subgroup_name in subgroups.items():
        keyboard.append([f"{subgroup_name}"])
    
    keyboard.append(["📁 Без подгруппы"])
    
    if action == "list":
        keyboard.append(["🔙 К группам"])
    else:
        keyboard.append(["🔙 Назад"])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_back_keyboard():
    """Простая кнопка назад"""
    return ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True)

def get_skip_keyboard():
    """Клавиатура с пропуском"""
    return ReplyKeyboardMarkup([["⏭️ Пропустить"], ["🔙 Назад"]], resize_keyboard=True)

def get_days_keyboard():
    """Клавиатура выбора дней недели"""
    keyboard = []
    days_list = list(DAYS_OF_WEEK.values())
    
    # Разбиваем на 2 строки
    keyboard.append(days_list[:4])  # Пн-Чт
    keyboard.append(days_list[4:])  # Пт-Вс
    keyboard.append(["🔙 Назад"])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_frequency_keyboard():
    """Клавиатура выбора периодичности"""
    keyboard = [
        ["🔄 2 в неделю"],
        ["📅 1 в неделю"],
        ["🗓️ 2 в месяц"],
        ["📆 1 в месяц"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_edit_fields_keyboard():
    """Клавиатура выбора поля для редактирования"""
    keyboard = [
        ["🏷️ Группу", "📂 Подгруппу"],
        ["📝 Текст", "🖼️ Изображение"],
        ["⏰ Время", "🔄 Периодичность"],
        ["✅ Подтвердить", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_confirmation_keyboard():
    """Клавиатура подтверждения"""
    keyboard = [
        ["✅ Подтвердить"],
        ["✏️ Изменить"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_yes_no_keyboard():
    """Клавиатура Да/Нет"""
    keyboard = [
        ["✅ Да", "❌ Нет"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_testing_keyboard():
    """Создает меню тестирования"""
    keyboard = [
        ["🚗 Тест Hongqi", "🚙 Тест TurboMatiz"],
        ["🛑 Остановить все тестирования"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_more_keyboard(user_id):
    """Создает меню дополнительных функций"""
    keyboard = [
        ["📊 Статус команд", "🕒 Текущее время"],
        ["🆔 Мой ID"]
    ]

    # Добавляем кнопку управления пользователями только для администратора
    if is_admin(user_id):
        keyboard.append(["👥 Управление пользователями"])

    keyboard.append(["🔙 Главное меню"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_management_keyboard():
    """Создает меню управления пользователями"""
    keyboard = [
        ["➕ Добавить пользователя", "➖ Удалить пользователя"],
        ["📋 Список пользователей", "🎯 Назначить группы"],
        ["🔙 Назад к ЕЩЕ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функции для работы со временем
def moscow_to_utc(time_str):
    """Конвертирует время из московского в UTC"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.datetime.now(moscow_tz)
        moscow_time = moscow_tz.localize(datetime.datetime(now.year, now.month, now.day, hours, minutes))
        utc_time = moscow_time.astimezone(pytz.utc)
        return utc_time.time()
    except Exception as time_error:
        raise ValueError(f"Ошибка конвертации времени: {time_error}")

def format_time_delta(delta):
    """Форматирует разницу времени в читаемый вид"""
    if delta.total_seconds() < 0:
        return "уже прошло"

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} дн")
    if hours > 0:
        parts.append(f"{hours} час")
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if seconds > 0 and days == 0 and hours == 0:
        parts.append(f"{seconds} сек")

    return " ".join(parts) if parts else "менее секунды"

# Основные команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 БОТ С МНОГОУРОВНЕВЫМ МЕНЮ\n'
            f'Текущее время: {current_time} (МСК)\n'
            f'ID чата: {chat_id}\n'
            f'Ваш ID: {user_id}\n\n'
            '❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n'
            'Для доступа к функциям бота обратитесь к администратору\n\n'
            '🎹 Доступные функции:\n'
            '• 🆔 Получить ID - узнать ваш идентификатор\n'
            '• /help - справка по командам'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_unauthorized_keyboard()
        )
        print(f"🚫 Неавторизованный доступ от user_id: {user_id}")
        return

    welcome_text = (
        f'🤖 БОТ С МНОГОУРОВНЕВЫМ МЕНЮ\n'
        f'Текущее время: {current_time} (МСК)\n'
        f'ID чата: {chat_id}\n'
        f'Ваш ID: {user_id}\n\n'
        '🎹 Используйте кнопки меню для навигации!\n\n'
        '💡 Также доступны текстовые команды:\n'
        '/help - справка по командам\n'
        '/update_menu - обновить меню\n'
        '/my_id - показать ваш ID'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
    print(f"✅ Отправлено главное меню в чат {chat_id} для user_id: {user_id}")

@authorization_required
async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно обновляет меню"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    print(f"🔄 Принудительное обновление на новое меню для чат {chat_id}, user_id: {user_id}")

    await update.message.reply_text(
        "🔄 Удаляю старое меню...",
        reply_markup=ReplyKeyboardRemove()
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "✅ Новое меню загружено!\n\n"
        "🎹 Теперь у вас:\n"
        "• 📋 Шаблоны - управление рассылками\n"
        "• 🧪 Тестирование - тестовые отправки\n"
        "• ⚙️ ЕЩЕ - дополнительные функции",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам"""
    user_id = update.effective_user.id

    help_text = """
🤖 СПРАВКА ПО КОМАНДАМ:

🎹 ДОСТУПНЫЕ ВСЕМ:
/start - перезапустить бота
/my_id - показать ваш ID (для получения доступа)
/help - эта справка

🎹 ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ:
📋 Шаблоны - управление основными рассылками
🧪 Тестирование - тестовые отправки
⚙️ ЕЩЕ - дополнительные функции
/update_menu - обновить меню
/status - статус шаблонов
/now - текущее время

🔐 Для получения доступа обратитесь к администратору
"""

    if is_authorized(user_id):
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(help_text, reply_markup=get_unauthorized_keyboard())

@authorization_required
async def now(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает текущее время"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    await update.message.reply_text(
        f'🕒 Текущее время: {current_time} (МСК)',
        reply_markup=get_main_keyboard()
    )

async def my_id(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает user_id пользователя"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_authorized(user_id):
        reply_markup = get_main_keyboard()
        additional_text = "✅ Вы авторизованы и имеете доступ ко всем функциям бота"
    else:
        reply_markup = get_unauthorized_keyboard()
        additional_text = "❌ Вы не авторизованы. Обратитесь к администратору для получения доступа"

    await update.message.reply_text(
        f'🆔 Ваш ID: `{user_id}`\n'
        f'💬 ID чата: `{chat_id}`\n\n'
        f'{additional_text}',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    print(f"📋 Показан ID для user_id: {user_id}")

# ===== СИСТЕМА ШАБЛОНОВ =====

@authorization_required
async def templates_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню шаблонов"""
    await update.message.reply_text(
        "🎯 **Управление шаблонами**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# === СПИСОК ШАБЛОНОВ ===
@authorization_required
async def template_list_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало просмотра списка шаблонов"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов\n\n"
            "Обратитесь к администратору для получения доступа",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    await update.message.reply_text(
        "📋 **Список шаблонов**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "list")
    )
    return TEMPLATE_LIST_GROUPS

@authorization_required
async def template_list_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора группы для просмотра"""
    group_name = update.message.text
    user_id = update.effective_user.id
    
    # Находим ID группы по имени
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа не найдена",
            reply_markup=get_groups_keyboard(user_id, "list")
        )
        return TEMPLATE_LIST_GROUPS
    
    context.user_data['current_group'] = group_id
    context.user_data['current_group_name'] = group_name
    
    # Проверяем есть ли подгруппы
    groups_data = load_groups()
    group_data = groups_data['groups'].get(group_id, {})
    subgroups = group_data.get('subgroups', {})
    
    if subgroups:
        await update.message.reply_text(
            f"📂 **{group_name}**\n\n"
            "Выберите подгруппу:",
            parse_mode='Markdown',
            reply_markup=get_subgroups_keyboard(group_id, "list")
        )
        return TEMPLATE_LIST_SUBGROUPS
    else:
        # Если подгрупп нет, сразу показываем шаблоны
        return await show_templates_list(update, context)

@authorization_required
async def template_list_choose_subgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора подгруппы для просмотра"""
    subgroup_text = update.message.text
    group_id = context.user_data.get('current_group')
    
    if subgroup_text == "📁 Без подгруппы":
        context.user_data['current_subgroup'] = None
    else:
        # Находим ID подгруппы по имени
        groups_data = load_groups()
        group_data = groups_data['groups'].get(group_id, {})
        subgroups = group_data.get('subgroups', {})
        
        subgroup_id = None
        for sid, sname in subgroups.items():
            if sname == subgroup_text:
                subgroup_id = sid
                break
        
        if subgroup_id:
            context.user_data['current_subgroup'] = subgroup_id
        else:
            context.user_data['current_subgroup'] = None
    
    return await show_templates_list(update, context)

async def show_templates_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список шаблонов в выбранной группе/подгруппе"""
    group_id = context.user_data.get('current_group')
    subgroup_id = context.user_data.get('current_subgroup')
    group_name = context.user_data.get('current_group_name', '')
    
    templates = get_templates_by_group(group_id, subgroup_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 **{group_name}**\n\n"
            "В этой группе пока нет шаблонов",
            parse_mode='Markdown',
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Показываем первые 5 шаблонов (для простоты)
    message_text = f"📋 **Шаблоны в {group_name}**\n\n"
    for i, (template_id, template) in enumerate(templates[:5], 1):
        message_text += f"{i}. **{template['name']}**\n"
        message_text += f"   ⏰ {template.get('time', 'Не указано')}\n"
        message_text += f"   📅 {len(template.get('days', []))} дней\n\n"
    
    if len(templates) > 5:
        message_text += f"📄 ... и еще {len(templates) - 5} шаблонов\n\n"
    
    message_text += "Для управления шаблонами используйте соответствующие кнопки в меню"
    
    await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# === ДОБАВЛЕНИЕ ШАБЛОНА ===
@authorization_required
async def add_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания шаблона"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    context.user_data['new_template'] = {
        'created_by': user_id
    }
    
    await update.message.reply_text(
        "➕ **Создание нового шаблона**\n\n"
        "Шаг 1 из 8: Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "add")
    )
    return ADD_TEMPLATE_GROUP

@authorization_required
async def add_template_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для нового шаблона"""
    group_name = update.message.text
    user_id = update.effective_user.id
    
    # Находим ID группы по имени
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа не найдена",
            reply_markup=get_groups_keyboard(user_id, "add")
        )
        return ADD_TEMPLATE_GROUP
    
    context.user_data['new_template']['group'] = group_id
    context.user_data['current_group'] = group_id
    
    # Проверяем есть ли подгруппы
    groups_data = load_groups()
    group_data = groups_data['groups'].get(group_id, {})
    subgroups = group_data.get('subgroups', {})
    
    if subgroups:
        await update.message.reply_text(
            "Шаг 2 из 8: Выберите подгруппу:",
            reply_markup=get_subgroups_keyboard(group_id, "add")
        )
        return ADD_TEMPLATE_SUBGROUP
    else:
        context.user_data['new_template']['subgroup'] = None
        await update.message.reply_text(
            "Шаг 3 из 8: Введите название шаблона:",
            reply_markup=get_back_keyboard()
        )
        return ADD_TEMPLATE_NAME

@authorization_required
async def add_template_choose_subgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор подгруппы для нового шаблона"""
    subgroup_text = update.message.text
    group_id = context.user_data.get('current_group')
    
    if subgroup_text == "📁 Без подгруппы":
        context.user_data['new_template']['subgroup'] = None
    else:
        # Находим ID подгруппы по имени
        groups_data = load_groups()
        group_data = groups_data['groups'].get(group_id, {})
        subgroups = group_data.get('subgroups', {})
        
        subgroup_id = None
        for sid, sname in subgroups.items():
            if sname == subgroup_text:
                subgroup_id = sid
                break
        
        if subgroup_id:
            context.user_data['new_template']['subgroup'] = subgroup_id
        else:
            context.user_data['new_template']['subgroup'] = None
    
    await update.message.reply_text(
        "Шаг 3 из 8: Введите название шаблона:",
        reply_markup=get_back_keyboard()
    )
    return ADD_TEMPLATE_NAME

@authorization_required
async def add_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия шаблона"""
    name = update.message.text.strip()
    
    if not name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название:",
            reply_markup=get_back_keyboard()
        )
        return ADD_TEMPLATE_NAME
    
    context.user_data['new_template']['name'] = name
    
    await update.message.reply_text(
        "Шаг 4 из 8: Введите текст шаблона:",
        reply_markup=get_back_keyboard()
    )
    return ADD_TEMPLATE_TEXT

@authorization_required
async def add_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод текста шаблона"""
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text(
            "❌ Текст не может быть пустым. Введите текст:",
            reply_markup=get_back_keyboard()
        )
        return ADD_TEMPLATE_TEXT
    
    context.user_data['new_template']['text'] = text
    
    await update.message.reply_text(
        "Шаг 5 из 8: Пришлите изображение для шаблона или нажмите 'Пропустить':",
        reply_markup=get_skip_keyboard()
    )
    return ADD_TEMPLATE_IMAGE

@authorization_required
async def add_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображения для шаблона"""
    if update.message.text == "⏭️ Пропустить":
        context.user_data['new_template']['image'] = None
        await update.message.reply_text(
            "Шаг 6 из 8: Введите время отправки в формате ЧЧ:ММ (МСК):",
            reply_markup=get_back_keyboard()
        )
        return ADD_TEMPLATE_TIME
    
    if update.message.photo:
        # Берем самое большое фото
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_content = await photo_file.download_as_bytearray()
        
        image_path = save_image(photo_content, f"template_{context.user_data['new_template']['name']}.jpg")
        
        if image_path:
            context.user_data['new_template']['image'] = image_path
            await update.message.reply_text(
                "✅ Изображение сохранено!\n\n"
                "Шаг 6 из 8: Введите время отправки в формате ЧЧ:ММ (МСК):",
                reply_markup=get_back_keyboard()
            )
            return ADD_TEMPLATE_TIME
        else:
            await update.message.reply_text(
                "❌ Ошибка сохранения изображения. Попробуйте еще раз или пропустите:",
                reply_markup=get_skip_keyboard()
            )
            return ADD_TEMPLATE_IMAGE
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, пришлите изображение или нажмите 'Пропустить':",
            reply_markup=get_skip_keyboard()
        )
        return ADD_TEMPLATE_IMAGE

@authorization_required
async def add_template_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени отправки"""
    time_str = update.message.text.strip()
    
    try:
        # Проверяем формат времени
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError
        
        context.user_data['new_template']['time'] = time_str
        
        await update.message.reply_text(
            "Шаг 7 из 8: Выберите дни отправки:",
            reply_markup=get_days_keyboard()
        )
        return ADD_TEMPLATE_DAYS
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 14:30):",
            reply_markup=get_back_keyboard()
        )
        return ADD_TEMPLATE_TIME

@authorization_required
async def add_template_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор дней отправки"""
    day_text = update.message.text
    
    # Находим номер дня по тексту
    day_number = None
    for num, text in DAYS_OF_WEEK.items():
        if text == day_text:
            day_number = num
            break
    
    if day_number is None:
        await update.message.reply_text(
            "❌ Неверный день. Выберите из списка:",
            reply_markup=get_days_keyboard()
        )
        return ADD_TEMPLATE_DAYS
    
    if 'days' not in context.user_data['new_template']:
        context.user_data['new_template']['days'] = []
    
    # Добавляем день если его еще нет
    if day_number not in context.user_data['new_template']['days']:
        context.user_data['new_template']['days'].append(day_number)
    
    # Показываем выбранные дни
    selected_days = [DAYS_OF_WEEK[day] for day in context.user_data['new_template']['days']]
    
    await update.message.reply_text(
        f"✅ Выбранные дни: {', '.join(selected_days)}\n\n"
        "Выберите еще дни или нажмите 'Далее' для продолжения:",
        reply_markup=ReplyKeyboardMarkup([
            ["➡️ Далее"],
            ["🔙 Назад"]
        ], resize_keyboard=True)
    )
    return ADD_TEMPLATE_DAYS

@authorization_required
async def add_template_days_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к выбору периодичности после выбора дней"""
    if not context.user_data['new_template'].get('days'):
        await update.message.reply_text(
            "❌ Нужно выбрать хотя бы один день",
            reply_markup=get_days_keyboard()
        )
        return ADD_TEMPLATE_DAYS
    
    await update.message.reply_text(
        "Шаг 8 из 8: Выберите периодичность:",
        reply_markup=get_frequency_keyboard()
    )
    return ADD_TEMPLATE_FREQUENCY

@authorization_required
async def add_template_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор периодичности"""
    frequency_text = update.message.text
    
    frequency_map = {
        "🔄 2 в неделю": "2_per_week",
        "📅 1 в неделю": "weekly", 
        "🗓️ 2 в месяц": "2_per_month",
        "📆 1 в месяц": "monthly"
    }
    
    if frequency_text not in frequency_map:
        await update.message.reply_text(
            "❌ Неверный выбор. Выберите из списка:",
            reply_markup=get_frequency_keyboard()
        )
        return ADD_TEMPLATE_FREQUENCY
    
    context.user_data['new_template']['frequency'] = frequency_map[frequency_text]
    
    # Если выбрано "2 в неделю", запрашиваем второй день
    if frequency_map[frequency_text] == "2_per_week":
        await update.message.reply_text(
            "🔄 Выберите второй день отправки:",
            reply_markup=get_days_keyboard()
        )
        return ADD_TEMPLATE_SECOND_DAY
    
    # Переходим к подтверждению
    return await show_template_confirmation(update, context)

@authorization_required
async def add_template_second_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор второго дня для периодичности 2 в неделю"""
    day_text = update.message.text
    
    # Находим номер дня по тексту
    day_number = None
    for num, text in DAYS_OF_WEEK.items():
        if text == day_text:
            day_number = num
            break
    
    if day_number is None:
        await update.message.reply_text(
            "❌ Неверный день. Выберите из списка:",
            reply_markup=get_days_keyboard()
        )
        return ADD_TEMPLATE_SECOND_DAY
    
    # Добавляем второй день
    if day_number not in context.user_data['new_template']['days']:
        context.user_data['new_template']['days'].append(day_number)
    
    return await show_template_confirmation(update, context)

async def show_template_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подтверждение создания шаблона"""
    template_data = context.user_data['new_template']
    
    # Форматируем информацию для показа
    info = format_template_info(template_data)
    
    await update.message.reply_text(
        f"✅ **ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ШАБЛОНА**\n\n{info}\n"
        "Всё верно?",
        parse_mode='Markdown',
        reply_markup=get_confirmation_keyboard()
    )
    return ADD_TEMPLATE_CONFIRM

@authorization_required
async def add_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания шаблона"""
    if update.message.text == "✅ Подтвердить":
        template_data = context.user_data['new_template']
        
        success, template_id = create_template(template_data)
        
        if success:
            await update.message.reply_text(
                f"✅ Шаблон успешно создан!\n\n"
                f"ID: {template_id}",
                reply_markup=get_templates_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании шаблона",
                reply_markup=get_templates_main_keyboard()
            )
        
        # Очищаем временные данные
        context.user_data.pop('new_template', None)
        context.user_data.pop('current_group', None)
        context.user_data.pop('current_subgroup', None)
        
        return TEMPLATES_MAIN
    
    elif update.message.text == "✏️ Изменить":
        await update.message.reply_text(
            "🔧 Какой пункт вы хотите изменить?",
            reply_markup=get_edit_fields_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_confirmation_keyboard()
        )
        return ADD_TEMPLATE_CONFIRM

# === РЕДАКТИРОВАНИЕ ШАБЛОНА ===
@authorization_required
async def edit_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования шаблона"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    await update.message.reply_text(
        "✏️ **Редактирование шаблона**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "edit")
    )
    # Для простоты пропускаем полную реализацию редактирования
    await update.message.reply_text(
        "⚠️ Функция редактирования в разработке\n\n"
        "Используйте удаление и создание нового шаблона",
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# === УДАЛЕНИЕ ШАБЛОНА ===
@authorization_required
async def delete_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления шаблона"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    await update.message.reply_text(
        "🗑️ **Удаление шаблона**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "delete")
    )
    # Для простоты пропускаем полную реализацию удаления
    await update.message.reply_text(
        "⚠️ Функция удаления в разработке\n\n"
        "Для управления используйте список шаблонов",
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# === ОБРАБОТЧИК НАВИГАЦИИ ===
@authorization_required
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для навигации по меню"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📋 Шаблоны":
        await templates_main(update, context)
        return TEMPLATES_MAIN

    elif text == "🧪 Тестирование":
        await update.message.reply_text(
            "🧪 ТЕСТИРОВАНИЕ ШАБЛОНОВ\n\n"
            "Тестовые отправки работают так же как основные,\n"
            "но отправляются через 10 секунд после активации\n"
            "и выполняются только один раз",
            reply_markup=get_testing_keyboard()
        )

    elif text == "⚙️ ЕЩЕ":
        await update.message.reply_text(
            "⚙️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ",
            reply_markup=get_more_keyboard(user_id)
        )

    elif text == "🔙 Главное меню":
        await update.message.reply_text(
            "🔙 Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    elif text == "📊 Статус команд":
        await update.message.reply_text(
            "⚠️ Статус временно недоступен",
            reply_markup=get_main_keyboard()
        )

    elif text == "🕒 Текущее время":
        await now(update, context)

    elif text == "🆔 Мой ID":
        await my_id(update, context)

    elif text == "👥 Управление пользователями" and is_admin(user_id):
        await update.message.reply_text(
            "👥 Управление пользователями\n\n"
            "Выберите действие:",
            reply_markup=get_user_management_keyboard()
        )

    elif text == "🔙 Назад к ЕЩЕ":
        await update.message.reply_text(
            "🔙 Возврат к дополнительным функциям",
            reply_markup=get_more_keyboard(user_id)
        )

    elif text == "🆔 Получить ID":
        await my_id(update, context)

    elif text == "📋 Справка":
        await help_command(update, context)

    else:
        await update.message.reply_text(
            "❌ Неизвестная команда\n"
            "Используйте кнопки меню или /help для справки",
            reply_markup=get_main_keyboard() if is_authorized(user_id) else get_unauthorized_keyboard()
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любого действия"""
    user_id = update.effective_user.id
    
    # Очищаем временные данные
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# Keep-alive функция
def keep_alive():
    """Периодически пингует приложение чтобы не дать ему заснуть"""
    def ping():
        while True:
            try:
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    response = requests.get(render_url, timeout=10)
                    print(f"🔄 Пинг отправлен: {response.status_code}")
                else:
                    print("🔄 Keep-alive: бот активен")
            except Exception as e:
                print(f"⚠️ Ошибка пинга: {e}")
            time.sleep(300)
    
    ping_thread = threading.Thread(target=ping, daemon=True)
    ping_thread.start()
    print("✅ Keep-alive система запущена")

def main():
    print("🚀 Запуск бота...")
    
    # Исправляем структуру данных при запуске
    try:
        from fix_data import fix_users_data, init_required_files
        fix_users_data()
        init_required_files()
        print("✅ Структура данных проверена и исправлена")
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке данных: {e}")
    
    keep_alive()

    application = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для шаблонов
    template_conv_handler = ConversationHandler(
        # ... остальной код без изменений
        entry_points=[
            MessageHandler(filters.Regex("^📋 Шаблоны$"), templates_main)
        ],
        states={
            TEMPLATES_MAIN: [
                MessageHandler(filters.Regex("^📋 Список шаблонов$"), template_list_start),
                MessageHandler(filters.Regex("^➕ Добавить новый$"), add_template_start),
                MessageHandler(filters.Regex("^✏️ Редактировать$"), edit_template_start),
                MessageHandler(filters.Regex("^🗑️ Удалить$"), delete_template_start),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), lambda u, c: ConversationHandler.END)
            ],
            TEMPLATE_LIST_GROUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_choose_group),
                MessageHandler(filters.Regex("^🔙 К шаблонам$"), templates_main)
            ],
            TEMPLATE_LIST_SUBGROUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_choose_subgroup),
                MessageHandler(filters.Regex("^🔙 К группам$"), template_list_start)
            ],
            ADD_TEMPLATE_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_choose_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            ADD_TEMPLATE_SUBGROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_choose_subgroup),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_start)
            ],
            ADD_TEMPLATE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_name),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_start)
            ],
            ADD_TEMPLATE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_text),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_choose_subgroup)
            ],
            ADD_TEMPLATE_IMAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_image),
                MessageHandler(filters.PHOTO, add_template_image),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_text)
            ],
            ADD_TEMPLATE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_time),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_image)
            ],
            ADD_TEMPLATE_DAYS: [
                MessageHandler(filters.Regex("^➡️ Далее$"), add_template_days_next),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_time)
            ],
            ADD_TEMPLATE_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_frequency),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_days)
            ],
            ADD_TEMPLATE_SECOND_DAY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_second_day),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_frequency)
            ],
            ADD_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_frequency)
            ],
            EDIT_TEMPLATE_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_confirm)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END
        }
    )

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("update_menu", update_menu))

    # Обработчики кнопок главного меню
    application.add_handler(MessageHandler(filters.Regex("^🧪 Тестирование$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ ЕЩЕ$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Главное меню$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📊 Статус команд$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🕒 Текущее время$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Мой ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^👥 Управление пользователями$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Назад к ЕЩЕ$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Получить ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📋 Справка$"), handle_text))

    # Добавляем ConversationHandler для шаблонов
    application.add_handler(template_conv_handler)

    # Обработчик для всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Запуск бота
    print("✅ Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == '__main__':
    # Для Render Web Service
    import os
    from threading import Thread
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        
        def log_message(self, format, *args):
            return
    
    def run_http_server():
        port = int(os.environ.get('PORT', 5000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"✅ HTTP server listening on port {port}")
        server.serve_forever()
    
    http_thread = Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    main()
