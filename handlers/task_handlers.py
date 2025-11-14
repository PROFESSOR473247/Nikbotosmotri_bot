from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.task_keyboards import (
    get_tasks_main_keyboard, get_groups_keyboard,
    get_task_confirmation_keyboard, get_task_edit_keyboard,
    get_back_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from template_manager import (
    get_user_accessible_groups, get_templates_by_group,
    get_template_by_id, format_template_info
)
from task_manager import (
    create_task_from_template, get_active_tasks_by_group,
    deactivate_task, format_task_info, get_all_active_tasks
)
from auth_manager import auth_manager
from chat_selection_manager import chat_selection_manager

# Состояния для ConversationHandler задач
(
    TASKS_MAIN, CREATE_TASK_GROUP, CREATE_TASK_SELECT, CREATE_TASK_CHAT_SELECT, CREATE_TASK_CONFIRM,
    CREATE_TASK_EDIT, DEACTIVATE_TASK_GROUP, DEACTIVATE_TASK_SELECT, DEACTIVATE_TASK_CONFIRM,
    TEST_TASK_GROUP, TEST_TASK_SELECT, TEST_TASK_CHAT_SELECT, TEST_TASK_CONFIRM
) = range(13)

# ===== ЗАЩИТНЫЕ ФУНКЦИИ =====

def safe_format_days_list(days):
    """Безопасно форматирует список дней"""
    try:
        if not days:
            return []
        if not isinstance(days, list):
            return []
        
        DAYS_OF_WEEK = {
            '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
            '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
        }
        
        return [DAYS_OF_WEEK.get(str(day), f"День {day}") for day in days]
    except Exception as e:
        print(f"⚠️ Ошибка форматирования дней {days}: {e}")
        return []

def safe_get_frequency_name(frequency):
    """Безопасно возвращает название периодичности"""
    try:
        frequency_map = {
            "weekly": "1 в неделю",
            "2_per_month": "2 в месяц", 
            "monthly": "1 в месяц"
        }
        return frequency_map.get(frequency, frequency)
    except Exception as e:
        print(f"⚠️ Ошибка получения периодичности {frequency}: {e}")
        return frequency

def safe_get_template_value(template, key, default=""):
    """Безопасно получает значение из шаблона"""
    try:
        return template.get(key, default)
    except Exception as e:
        print(f"⚠️ Ошибка получения значения {key} из шаблона: {e}")
        return default

# ===== ОСНОВНЫЕ ФУНКЦИИ ЗАДАЧ =====

async def tasks_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню задач"""
    user_id = update.effective_user.id
    auth_manager.update_user_role_if_needed(user_id)
    
    await update.message.reply_text(
        "📋 **Управление задачами**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_tasks_main_keyboard()
    )
    return TASKS_MAIN

# ===== СОЗДАНИЕ ЗАДАЧИ =====

async def create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания задачи"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Инициализируем данные для создания задачи
    context.user_data['task_creation'] = {
        'created_by': user_id,
        'is_test': False
    }
    
    await update.message.reply_text(
        "➕ **Создание новой задачи**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "task")
    )
    return CREATE_TASK_GROUP

async def create_task_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для создания задачи"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    print(f"🔍 Пользователь выбрал группу: {user_text}")
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 К задачам":
        await tasks_main(update, context)
        return TASKS_MAIN
    
    # Определяем группу по тексту
    group_name = None
    if user_text in ["🚗 Hongqi", "Hongqi"]:
        group_name = "🚗 Hongqi"
    elif user_text in ["🚙 TurboMatiz", "TurboMatiz"]:
        group_name = "🚙 TurboMatiz"
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите группу из предложенных кнопок",
            reply_markup=get_groups_keyboard(user_id, "task")
        )
        return CREATE_TASK_GROUP
    
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
            reply_markup=get_groups_keyboard(user_id, "task")
        )
        return CREATE_TASK_GROUP
    
    # Сохраняем данные группы
    context.user_data['task_creation']['group'] = group_id
    context.user_data['current_group'] = group_id
    
    # Получаем шаблоны этой группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе '{group_name}' нет шаблонов для создания задач",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Создаем клавиатуру с шаблонами
    keyboard = []
    for template_id, template in templates:
        button_text = f"📝 {template['name']}"
        keyboard.append([button_text])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"➕ **Выберите шаблон для задачи:**\n\n"
        f"Группа: {group_name}\n"
        f"Доступно шаблонов: {len(templates)}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CREATE_TASK_SELECT

async def create_task_select_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для задачи"""
    template_text = update.message.text
    user_id = update.effective_user.id
    
    print(f"🔍 Пользователь выбрал шаблон: {template_text}")
    
    # Если нажата кнопка "Назад"
    if template_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору группы",
            reply_markup=get_groups_keyboard(user_id, "task")
        )
        return CREATE_TASK_GROUP
    
    # Извлекаем название шаблона из текста (убираем эмодзи)
    if template_text.startswith("📝 "):
        template_name = template_text[2:].strip()
    else:
        template_name = template_text
    
    # Получаем ID группы из контекста
    group_id = context.user_data['task_creation']['group']
    
    # Ищем шаблон по имени в этой группе
    templates = get_templates_by_group(group_id)
    template_id = None
    template_data = None
    
    for tid, tdata in templates:
        if tdata['name'] == template_name:
            template_id = tid
            template_data = tdata
            break
    
    if not template_data:
        await update.message.reply_text(
            "❌ Шаблон не найден",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Сохраняем данные шаблона
    context.user_data['task_creation']['template'] = template_data
    context.user_data['task_creation']['template_id'] = template_id
    
    # ПЕРЕХОДИМ К ВЫБОРУ ЧАТА
    accessible_chats, message = chat_selection_manager.get_user_accessible_chats_for_selection(user_id)

    if not accessible_chats:
        await update.message.reply_text(
            message,
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN

    context.user_data['accessible_chats'] = accessible_chats

    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=chat_selection_manager.get_back_keyboard()
    )
    return CREATE_TASK_CHAT_SELECT

async def create_task_select_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора чата для задачи"""
    return await chat_selection_manager.handle_chat_selection(update, context, CREATE_TASK_CONFIRM)

def format_task_confirmation(template, chat_name=None):
    """Форматирует подтверждение создания задачи"""
    try:
        # Безопасно обрабатываем дни недели
        days_names = safe_format_days_list(template.get('days', []))
        frequency = safe_get_frequency_name(template.get('frequency', 'Не указана'))
        
        template_name = safe_get_template_value(template, 'name', 'Без названия')
        template_text = safe_get_template_value(template, 'text', '')
        template_time = safe_get_template_value(template, 'time', 'Не указано')
        has_image = '✅ Есть' if template.get('image') else '❌ Нет'
        
        info = "✅ **ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ЗАДАЧИ**\n\n"
        info += "Вы собираетесь создать задачу. Проверьте пожалуйста все данные:\n\n"
        info += f"📝 **Шаблон:** {template_name}\n"
        
        if chat_name:
            info += f"💬 **Чат для отправки:** {chat_name}\n"
        
        info += f"📄 **Текст:** {template_text[:200]}...\n"
        info += f"🖼️ **Изображение:** {has_image}\n"
        info += f"⏰ **Время отправки:** {template_time} (МСК)\n"
        info += f"📅 **Дни отправки:** {', '.join(days_names) if days_names else 'Не указаны'}\n"
        info += f"🔄 **Периодичность:** {frequency}\n\n"
        info += "**Всё верно?**"
        
        return info
    except Exception as e:
        print(f"❌ Ошибка форматирования подтверждения задачи: {e}")
        return "❌ Ошибка загрузки подтверждения задачи"

async def create_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания задачи"""
    user_choice = update.message.text
    task_data = context.user_data['task_creation']
    template = task_data['template']
    target_chat_id = task_data.get('target_chat_id')
    
    if user_choice == "✅ Подтвердить":
        success, task_id = create_task_from_template(
            template, 
            task_data['created_by'],
            is_test=task_data.get('is_test', False),
            target_chat_id=target_chat_id
        )
        
        if success:
            task_type = "тестовую" if task_data.get('is_test') else "регулярную"
            chat_info = f" в чате '{task_data.get('target_chat_name', 'Не указан')}'" if target_chat_id else ""
            
            await update.message.reply_text(
                f"✅ {task_type.capitalize()} задача успешно создана{chat_info}!\n\n"
                f"ID задачи: `{task_id}`",
                parse_mode='Markdown',
                reply_markup=get_tasks_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании задачи",
                reply_markup=get_tasks_main_keyboard()
            )
        
        # Очищаем временные данные
        context.user_data.clear()
        return TASKS_MAIN
    
    elif user_choice == "✏️ Изменить":
        await update.message.reply_text(
            "🔧 **Что вы хотите изменить?**",
            reply_markup=get_task_edit_keyboard()
        )
        return CREATE_TASK_EDIT
    
    elif user_choice == "🔙 Назад":
        # Возвращаемся к выбору чата
        return await chat_selection_manager.go_back_to_template_selection(update, context)
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_task_confirmation_keyboard()
        )
        return CREATE_TASK_CONFIRM

async def create_task_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора редактирования"""
    choice = update.message.text
    
    if choice == "🔙 Назад":
        # Возвращаемся к подтверждению
        task_data = context.user_data['task_creation']
        template = task_data['template']
        info = format_task_confirmation(template, task_data.get('target_chat_name'))
        
        await update.message.reply_text(
            info,
            parse_mode='Markdown',
            reply_markup=get_task_confirmation_keyboard()
        )
        return CREATE_TASK_CONFIRM
    
    elif choice == "🏷️ Изменить группу":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 **Выберите новую группу:**",
            reply_markup=get_groups_keyboard(user_id, "task")
        )
        return CREATE_TASK_GROUP
    
    elif choice == "📝 Выбрать другой шаблон":
        group_id = context.user_data['task_creation']['group']
        templates = get_templates_by_group(group_id)
        
        # Создаем клавиатуру с шаблонами
        keyboard = []
        for template_id, template in templates:
            keyboard.append([f"📝 {template['name']}"])
        
        keyboard.append(["🔙 Назад"])
        
        await update.message.reply_text(
            "🔄 **Выберите другой шаблон:**",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return CREATE_TASK_SELECT
    
    elif choice == "⚙️ Изменить настройки шаблона":
        await update.message.reply_text(
            "⚠️ Редактирование шаблонов доступно в основном меню шаблонов\n\n"
            "Выберите другой шаблон или вернитесь к подтверждению",
            reply_markup=get_task_edit_keyboard()
        )
        return CREATE_TASK_EDIT
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_task_edit_keyboard()
        )
        return CREATE_TASK_EDIT

# ===== ДЕАКТИВАЦИЯ ЗАДАЧИ =====

async def deactivate_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало деактивации задачи"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    await update.message.reply_text(
        "🗑️ **Отмена задачи**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "deactivate")
    )
    return DEACTIVATE_TASK_GROUP

async def deactivate_task_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для деактивации задачи"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 К задачам":
        await tasks_main(update, context)
        return TASKS_MAIN
    
    # Определяем группу по тексту
    group_name = None
    if user_text in ["🚗 Hongqi", "Hongqi"]:
        group_name = "🚗 Hongqi"
    elif user_text in ["🚙 TurboMatiz", "TurboMatiz"]:
        group_name = "🚙 TurboMatiz"
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите группу из предложенных кнопок",
            reply_markup=get_groups_keyboard(user_id, "deactivate")
        )
        return DEACTIVATE_TASK_GROUP
    
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
            reply_markup=get_groups_keyboard(user_id, "deactivate")
        )
        return DEACTIVATE_TASK_GROUP
    
    # Сохраняем ID группы в контекст для использования в следующем шаге
    context.user_data['deactivate_group'] = group_id
    
    # Получаем активные задачи этой группы
    tasks = get_active_tasks_by_group(group_id)
    
    if not tasks:
        await update.message.reply_text(
            f"📭 В группе '{group_name}' нет активных задач",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Создаем клавиатуру с задачами
    keyboard = []
    for task_id, task in tasks:
        keyboard.append([f"🗑️ {task['template_name']}"])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"🗑️ **Выберите задачу для отмены:**\n\n"
        f"Группа: {group_name}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DEACTIVATE_TASK_SELECT

async def deactivate_task_select_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор задачи для деактивации"""
    task_text = update.message.text
    
    # Если нажата кнопка "Назад"
    if task_text == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы",
            reply_markup=get_groups_keyboard(user_id, "deactivate")
        )
        return DEACTIVATE_TASK_GROUP
    
    # Извлекаем название шаблона из текста (убираем эмодзи)
    if task_text.startswith("🗑️ "):
        template_name = task_text[2:].strip()
    else:
        template_name = task_text
    
    # Получаем ID группы из контекста
    group_id = context.user_data.get('deactivate_group')
    
    # Ищем задачу по имени шаблона в этой группе
    tasks = get_active_tasks_by_group(group_id)
    task_id = None
    task_data = None
    
    for tid, tdata in tasks:
        if tdata['template_name'] == template_name:
            task_id = tid
            task_data = tdata
            break
    
    if not task_data:
        await update.message.reply_text(
            "❌ Задача не найдена",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Сохраняем ID для деактивации
    context.user_data['deactivating_task_id'] = task_id
    context.user_data['deactivating_task'] = task_data
    
    # Показываем подтверждение
    info = format_task_info(task_data)
    
    await update.message.reply_text(
        f"⚠️ **ПОДТВЕРЖДЕНИЕ ОТМЕНЫ ЗАДАЧИ**\n\n{info}\n"
        "❌ **ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ ОТМЕНИТЬ ДАННУЮ ЗАДАЧУ?**\n\n"
        "Это действие нельзя отменить!",
        parse_mode='Markdown',
        reply_markup=get_deactivate_confirmation_keyboard()
    )
    return DEACTIVATE_TASK_CONFIRM

def get_deactivate_confirmation_keyboard():
    """Клавиатура подтверждения деактивации"""
    keyboard = [
        ["✅ Да, отменить задачу"],
        ["❌ Нет, оставить активной"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def deactivate_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение деактивации задачи"""
    user_choice = update.message.text
    task_id = context.user_data.get('deactivating_task_id')
    task = context.user_data.get('deactivating_task')
    
    if user_choice == "✅ Да, отменить задачу":
        if task_id and task:
            success, message = deactivate_task(task_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Задача '{task['template_name']}' успешно отменена!",
                    reply_markup=get_tasks_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при отмене: {message}",
                    reply_markup=get_tasks_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "❌ Ошибка: данные задачи не найдены",
                reply_markup=get_tasks_main_keyboard()
            )
    
    elif user_choice == "❌ Нет, оставить активной":
        await update.message.reply_text(
            "✅ Отмена отменена",
            reply_markup=get_tasks_main_keyboard()
        )
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_deactivate_confirmation_keyboard()
        )
        return DEACTIVATE_TASK_CONFIRM
    
    # Очищаем временные данные
    context.user_data.clear()
    return TASKS_MAIN

# ===== ТЕСТИРОВАНИЕ =====

async def test_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало тестирования задачи"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    context.user_data['task_creation'] = {
        'created_by': user_id,
        'is_test': True
    }
    
    await update.message.reply_text(
        "🧪 **Тестирование задачи**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "test")
    )
    return TEST_TASK_GROUP

async def test_task_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для тестирования"""
    return await create_task_select_group(update, context)

async def test_task_select_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для тестирования"""
    return await create_task_select_template(update, context)

async def test_task_select_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора чата для тестовой задачи"""
    return await chat_selection_manager.handle_chat_selection(update, context, TEST_TASK_CONFIRM)

async def test_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение тестирования"""
    user_choice = update.message.text
    task_data = context.user_data['task_creation']
    template = task_data['template']
    target_chat_id = task_data.get('target_chat_id')
    
    if user_choice == "✅ Подтвердить":
        success, task_id = create_task_from_template(
            template, 
            task_data['created_by'],
            is_test=task_data.get('is_test', True),
            target_chat_id=target_chat_id
        )
        
        if success:
            # Для тестовых задач сразу выполняем отправку
            from task_scheduler import execute_test_task
            await execute_test_task(template, update, context, target_chat_id)
            
            chat_info = f" в чате '{task_data.get('target_chat_name', 'Не указан')}'" if target_chat_id else ""
            
            await update.message.reply_text(
                f"✅ Тестовая задача успешно создана и отправлена{chat_info}!\n\n"
                f"ID задачи: `{task_id}`",
                parse_mode='Markdown',
                reply_markup=get_tasks_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании тестовой задачи",
                reply_markup=get_tasks_main_keyboard()
            )
        
        # Очищаем временные данные
        context.user_data.clear()
        return TASKS_MAIN
    
    elif user_choice == "✏️ Изменить":
        await update.message.reply_text(
            "🔧 **Что вы хотите изменить?**",
            reply_markup=get_task_edit_keyboard()
        )
        return CREATE_TASK_EDIT
    
    elif user_choice == "🔙 Назад":
        # Возвращаемся к выбору чата
        return await chat_selection_manager.go_back_to_template_selection(update, context)
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_task_confirmation_keyboard()
        )
        return TEST_TASK_CONFIRM

# ===== СТАТУС ЗАДАЧ =====

async def show_tasks_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус всех активных задач"""
    active_tasks = get_all_active_tasks()
    
    if not active_tasks:
        await update.message.reply_text(
            "📊 **Статус задач**\n\n"
            "❌ Нет активных задач",
            parse_mode='Markdown',
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    message_text = "📊 **Статус активных задач:**\n\n"
    
    for i, (task_id, task) in enumerate(active_tasks.items(), 1):
        task_type = "🧪 Тест" if task.get('is_test') else "📅 Регулярная"
        chat_info = f" (💬 {task.get('target_chat_id', 'Не указан')})" if task.get('target_chat_id') else ""
        
        message_text += f"{i}. **{task['template_name']}** ({task_type}){chat_info}\n"
        message_text += f"   🏷️ Группа: {task.get('group_name', 'Не указана')}\n"
        message_text += f"   ⏰ Время: {task.get('time', 'Не указано')}\n"
        
        if task.get('next_execution'):
            message_text += f"   ⏱️ Следующее: {task['next_execution']}\n"
        
        message_text += "\n"
    
    message_text += f"Всего активных задач: {len(active_tasks)}"
    
    await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=get_tasks_main_keyboard()
    )
    return TASKS_MAIN

# ===== ФУНКЦИЯ ОТМЕНЫ =====

async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена и возврат в главное меню"""
    # Очищаем временные данные
    context.user_data.clear()
    
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🔙 Возврат в главное меню",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END

# ===== CONVERSATION HANDLER =====

def get_task_conversation_handler():
    """Возвращает настроенный ConversationHandler для задач"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Задачи$"), tasks_main)],
        states={
            TASKS_MAIN: [
                MessageHandler(filters.Regex("^➕ Создать задачу$"), create_task_start),
                MessageHandler(filters.Regex("^🗑️ Отменить задачу$"), deactivate_task_start),
                MessageHandler(filters.Regex("^🧪 Тестирование$"), test_task_start),
                MessageHandler(filters.Regex("^📊 Статус задач$"), show_tasks_status),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), cancel_task)
            ],
            
            # === СОЗДАНИЕ ЗАДАЧ ===
            CREATE_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_select_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), create_task_select_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), create_task_select_group),
                MessageHandler(filters.Regex("^🔙 К задачам$"), tasks_main)
            ],
            CREATE_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_select_template),
                MessageHandler(filters.Regex("^📝 .*"), create_task_select_template),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_task_start)
            ],
            CREATE_TASK_CHAT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_select_chat),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_task_select_template)
            ],
            CREATE_TASK_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_confirm),
                MessageHandler(filters.Regex("^✅ Подтвердить$"), create_task_confirm),
                MessageHandler(filters.Regex("^✏️ Изменить$"), create_task_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_task_select_chat)
            ],
            CREATE_TASK_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_edit_choice),
                MessageHandler(filters.Regex("^🏷️ Изменить группу$"), create_task_edit_choice),
                MessageHandler(filters.Regex("^📝 Выбрать другой шаблон$"), create_task_edit_choice),
                MessageHandler(filters.Regex("^⚙️ Изменить настройки шаблона$"), create_task_edit_choice),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_task_edit_choice)
            ],
            
            # === ДЕАКТИВАЦИЯ ЗАДАЧ ===
            DEACTIVATE_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deactivate_task_select_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), deactivate_task_select_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), deactivate_task_select_group),
                MessageHandler(filters.Regex("^🔙 К задачам$"), tasks_main)
            ],
            DEACTIVATE_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deactivate_task_select_task),
                MessageHandler(filters.Regex("^🗑️ .*"), deactivate_task_select_task),
                MessageHandler(filters.Regex("^🔙 Назад$"), deactivate_task_start)
            ],
            DEACTIVATE_TASK_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deactivate_task_confirm),
                MessageHandler(filters.Regex("^✅ Да, отменить задачу$"), deactivate_task_confirm),
                MessageHandler(filters.Regex("^❌ Нет, оставить активной$"), deactivate_task_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), deactivate_task_select_task)
            ],
            
            # === ТЕСТИРОВАНИЕ ===
            TEST_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, test_task_select_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), test_task_select_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), test_task_select_group),
                MessageHandler(filters.Regex("^🔙 К задачам$"), tasks_main)
            ],
            TEST_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, test_task_select_template),
                MessageHandler(filters.Regex("^📝 .*"), test_task_select_template),
                MessageHandler(filters.Regex("^🔙 Назад$"), test_task_start)
            ],
            TEST_TASK_CHAT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, test_task_select_chat),
                MessageHandler(filters.Regex("^🔙 Назад$"), test_task_select_template)
            ],
            TEST_TASK_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, test_task_confirm),
                MessageHandler(filters.Regex("^✅ Подтвердить$"), test_task_confirm),
                MessageHandler(filters.Regex("^✏️ Изменить$"), test_task_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), test_task_select_chat)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_task)]
    )