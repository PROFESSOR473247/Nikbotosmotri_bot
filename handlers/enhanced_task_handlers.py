"""
Улучшенные обработчики задач с новой структурой расписания
"""

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.task_keyboards import (
    get_tasks_main_keyboard, get_groups_keyboard,
    get_task_confirmation_keyboard, get_back_keyboard,
    get_chat_selection_keyboard, get_deactivate_confirmation_keyboard,
    get_schedule_type_keyboard, get_week_days_keyboard, get_frequency_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from template_manager import (
    get_user_accessible_groups, get_templates_by_group,
    get_template_by_name_and_group
)
from task_manager import (
    create_task_from_template, get_active_tasks_by_group,
    deactivate_task, format_task_info, get_user_accessible_tasks,
    format_task_list_info, create_task_with_schedule
)
from task_models import TaskData
from task_validators import TaskValidator
from auth_manager import auth_manager
from chat_access_manager import chat_access_manager

# Состояния для ConversationHandler задач
(
    TASKS_MAIN, CREATE_TASK_GROUP, CREATE_TASK_SELECT, CREATE_TASK_CHAT_SELECT,
    CREATE_TASK_SCHEDULE_TYPE, CREATE_TASK_TIME, CREATE_TASK_WEEK_DAYS,
    CREATE_TASK_MONTH_DAYS, CREATE_TASK_FREQUENCY, CREATE_TASK_CONFIRM,
    DEACTIVATE_TASK_GROUP, DEACTIVATE_TASK_SELECT, DEACTIVATE_TASK_CONFIRM,
    TEST_TASK_GROUP, TEST_TASK_SELECT, TEST_TASK_CHAT_SELECT, TEST_TASK_CONFIRM
) = range(17)

# ===== ОСНОВНЫЕ ФУНКЦИИ ЗАДАЧ =====

async def enhanced_tasks_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ===== СОЗДАНИЕ ЗАДАЧИ С НОВОЙ СТРУКТУРОЙ РАСПИСАНИЯ =====

async def enhanced_create_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания задачи с новой структурой"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Проверяем доступные чаты
    accessible_chats = await chat_access_manager.get_user_accessible_chats_with_membership(user_id)
    if not accessible_chats:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одному Telegram чату\n\n"
            "Обратитесь к администратору для предоставления доступа к чатам",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Инициализируем данные для создания задачи
    context.user_data['task_creation'] = {
        'created_by': user_id,
        'is_test': False,
        'accessible_chats': accessible_chats,
        'schedule_data': {}
    }
    
    await update.message.reply_text(
        "➕ **Создание новой задачи**\n\n"
        "Шаг 1 из 7: Выберите группу шаблонов:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "task")
    )
    return CREATE_TASK_GROUP

async def enhanced_create_task_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы шаблонов для создания задачи"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 К задачам":
        await enhanced_tasks_main(update, context)
        return TASKS_MAIN
    
    # Извлекаем название группы из текста
    group_name = user_text.replace("🏷️ ", "").strip()
    
    # Находим ID группы по имени
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа шаблонов не найдена",
            reply_markup=get_groups_keyboard(user_id, "task")
        )
        return CREATE_TASK_GROUP
    
    # Сохраняем данные группы
    context.user_data['task_creation']['group'] = group_id
    context.user_data['task_creation']['group_name'] = group_name
    
    # Получаем шаблоны этой группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе шаблонов '{group_name}' нет шаблонов для создания задач",
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
        f"➕ **Шаг 2 из 7: Выберите шаблон для задачи:**\n\n"
        f"Группа шаблонов: {group_name}\n"
        f"Доступно шаблонов: {len(templates)}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return CREATE_TASK_SELECT

async def enhanced_create_task_select_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для задачи"""
    template_text = update.message.text
    user_id = update.effective_user.id
    
    # Если нажата кнопка "Назад"
    if template_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору группы шаблонов",
            reply_markup=get_groups_keyboard(user_id, "task")
        )
        return CREATE_TASK_GROUP
    
    # Извлекаем название шаблона из текста
    if template_text.startswith("📝 "):
        template_name = template_text[2:].strip()
    else:
        template_name = template_text
    
    # Получаем ID группы из контекста
    group_id = context.user_data['task_creation']['group']
    
    # Ищем шаблон по имени в этой группе
    template_id, template_data = get_template_by_name_and_group(template_name, group_id)
    
    if not template_data:
        await update.message.reply_text(
            "❌ Шаблон не найден",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Сохраняем данные шаблона
    context.user_data['task_creation']['template'] = template_data
    context.user_data['task_creation']['template_id'] = template_id
    context.user_data['task_creation']['template_name'] = template_name
    
    # Переходим к выбору чата
    accessible_chats = context.user_data['task_creation']['accessible_chats']
    
    await update.message.reply_text(
        f"💬 **Шаг 3 из 7: Выберите Telegram чат для отправки:**\n\n"
        f"Шаблон: {template_name}\n"
        f"Группа шаблонов: {context.user_data['task_creation']['group_name']}\n\n"
        f"Доступные чаты:",
        parse_mode='Markdown',
        reply_markup=get_chat_selection_keyboard(accessible_chats)
    )
    return CREATE_TASK_CHAT_SELECT

async def enhanced_create_task_select_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор чата для задачи"""
    user_text = update.message.text
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 Назад":
        # Возвращаемся к выбору шаблона
        group_id = context.user_data['task_creation']['group']
        templates = get_templates_by_group(group_id)
        
        keyboard = []
        for template_id, template in templates:
            keyboard.append([f"📝 {template['name']}"])
        keyboard.append(["🔙 Назад"])
        
        await update.message.reply_text(
            "🔄 **Выберите шаблон:**",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return CREATE_TASK_SELECT
    
    # Обрабатываем выбор чата по номеру
    try:
        chat_number = int(user_text.split('.')[0])
        accessible_chats = context.user_data['task_creation']['accessible_chats']
        
        if 1 <= chat_number <= len(accessible_chats):
            selected_chat = accessible_chats[chat_number - 1]
            
            # Сохраняем выбранный чат
            context.user_data['task_creation']['target_chat_id'] = selected_chat['chat_id']
            context.user_data['task_creation']['target_chat_name'] = selected_chat['chat_name']
            
            # Переходим к выбору типа расписания
            await update.message.reply_text(
                "📅 **Шаг 4 из 7: Выберите тип расписания:**\n\n"
                "Как вы хотите настроить отправку сообщений?",
                parse_mode='Markdown',
                reply_markup=get_schedule_type_keyboard()
            )
            return CREATE_TASK_SCHEDULE_TYPE
            
        else:
            raise ValueError("Неверный номер чата")
            
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Пожалуйста, выберите чат из списка по номеру:",
            reply_markup=get_chat_selection_keyboard(context.user_data['task_creation']['accessible_chats'])
        )
        return CREATE_TASK_CHAT_SELECT

async def enhanced_create_task_select_schedule_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор типа расписания"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        # Возвращаемся к выбору чата
        accessible_chats = context.user_data['task_creation']['accessible_chats']
        await update.message.reply_text(
            "🔄 Возврат к выбору чата:",
            reply_markup=get_chat_selection_keyboard(accessible_chats)
        )
        return CREATE_TASK_CHAT_SELECT
    
    schedule_type = None
    if user_text == "📅 По дням недели":
        schedule_type = 'week_days'
    elif user_text == "📆 По числам месяца":
        schedule_type = 'month_days'
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите тип расписания из списка:",
            reply_markup=get_schedule_type_keyboard()
        )
        return CREATE_TASK_SCHEDULE_TYPE
    
    # Сохраняем тип расписания
    context.user_data['task_creation']['schedule_data']['schedule_type'] = schedule_type
    
    # Переходим к вводу времени
    await update.message.reply_text(
        "⏰ **Шаг 5 из 7: Укажите время отправки:**\n\n"
        "Напишите время в формате ЧЧ:ММ через запятую.\n"
        "Например: 12:35, 15:20, 23:00\n\n"
        "Можно указать несколько вариантов времени.",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return CREATE_TASK_TIME

async def enhanced_create_task_input_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени отправки"""
    time_text = update.message.text
    
    if time_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору типа расписания:",
            reply_markup=get_schedule_type_keyboard()
        )
        return CREATE_TASK_SCHEDULE_TYPE
    
    # Валидируем ввод времени
    is_valid, result = TaskValidator.validate_time_input(time_text)
    
    if not is_valid:
        error_message = "\n".join(result) if isinstance(result, list) else result
        await update.message.reply_text(
            f"❌ Ошибка ввода времени:\n{error_message}\n\n"
            "Пожалуйста, введите время в правильном формате:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_TIME
    
    # Сохраняем время
    context.user_data['task_creation']['schedule_data']['times'] = result
    
    schedule_type = context.user_data['task_creation']['schedule_data']['schedule_type']
    
    if schedule_type == 'week_days':
        # Переходим к выбору дней недели
        await update.message.reply_text(
            "📅 **Шаг 6 из 7: Выберите дни недели для отправки:**\n\n"
            "Выберите один или несколько дней:",
            parse_mode='Markdown',
            reply_markup=get_week_days_keyboard()
        )
        return CREATE_TASK_WEEK_DAYS
    else:
        # Переходим к вводу чисел месяца
        await update.message.reply_text(
            "📆 **Шаг 6 из 7: Укажите числа месяца для отправки:**\n\n"
            "Напишите числа через запятую (от 1 до 31).\n"
            "Например: 1, 10, 15, 28\n\n"
            "Можно указать несколько чисел.",
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_MONTH_DAYS

async def enhanced_create_task_select_week_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор дней недели"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к вводу времени:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_TIME
    
    if user_text == "✅ Завершить выбор дней":
        selected_days = context.user_data['task_creation']['schedule_data'].get('week_days', [])
        if not selected_days:
            await update.message.reply_text(
                "❌ Нужно выбрать хотя бы один день недели",
                reply_markup=get_week_days_keyboard(selected_days)
            )
            return CREATE_TASK_WEEK_DAYS
        
        # Переходим к выбору периодичности
        await update.message.reply_text(
            "🔄 **Шаг 7 из 7: Выберите периодичность отправки:**",
            parse_mode='Markdown',
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TASK_FREQUENCY
    
    # Обрабатываем выбор дня
    day_map = {
        "Понедельник": 0, "Вторник": 1, "Среда": 2,
        "Четверг": 3, "Пятница": 4, "Суббота": 5, "Воскресенье": 6
    }
    
    day_number = None
    for day_name, day_num in day_map.items():
        if day_name in user_text:
            day_number = day_num
            break
    
    if day_number is not None:
        # Добавляем или удаляем день
        selected_days = context.user_data['task_creation']['schedule_data'].get('week_days', [])
        
        if day_number in selected_days:
            selected_days.remove(day_number)
        else:
            selected_days.append(day_number)
        
        context.user_data['task_creation']['schedule_data']['week_days'] = selected_days
        
        # Обновляем клавиатуру
        day_names = [list(day_map.keys())[day] for day in selected_days]
        await update.message.reply_text(
            f"✅ Выбраны дни: {', '.join(day_names) if day_names else 'нет'}\n\n"
            "Продолжайте выбор или завершите:",
            reply_markup=get_week_days_keyboard(selected_days)
        )
        return CREATE_TASK_WEEK_DAYS
    
    await update.message.reply_text(
        "❌ Пожалуйста, выберите день из списка:",
        reply_markup=get_week_days_keyboard(context.user_data['task_creation']['schedule_data'].get('week_days', []))
    )
    return CREATE_TASK_WEEK_DAYS

async def enhanced_create_task_input_month_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод чисел месяца"""
    days_text = update.message.text
    
    if days_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к вводу времени:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_TIME
    
    # Валидируем ввод чисел месяца
    is_valid, result = TaskValidator.validate_month_days_input(days_text)
    
    if not is_valid:
        error_message = "\n".join(result) if isinstance(result, list) else result
        await update.message.reply_text(
            f"❌ Ошибка ввода чисел:\n{error_message}\n\n"
            "Пожалуйста, введите числа в правильном формате:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_MONTH_DAYS
    
    # Сохраняем числа месяца
    context.user_data['task_creation']['schedule_data']['month_days'] = result
    
    # Переходим к выбору периодичности
    await update.message.reply_text(
        "🔄 **Шаг 7 из 7: Выберите периодичность отправки:**",
        parse_mode='Markdown',
        reply_markup=get_frequency_keyboard()
    )
    return CREATE_TASK_FREQUENCY

async def enhanced_create_task_select_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор периодичности"""
    frequency_text = update.message.text
    
    schedule_type = context.user_data['task_creation']['schedule_data']['schedule_type']
    
    if frequency_text == "🔙 Назад":
        if schedule_type == 'week_days':
            selected_days = context.user_data['task_creation']['schedule_data'].get('week_days', [])
            await update.message.reply_text(
                "🔄 Возврат к выбору дней недели:",
                reply_markup=get_week_days_keyboard(selected_days)
            )
            return CREATE_TASK_WEEK_DAYS
        else:
            await update.message.reply_text(
                "🔄 Возврат к вводу чисел месяца:",
                reply_markup=get_back_keyboard()
            )
            return CREATE_TASK_MONTH_DAYS
    
    frequency_map = {
        "📅 1 раз в неделю": "weekly",
        "🔄 1 раз в 2 недели": "biweekly", 
        "📆 1 раз в месяц": "monthly"
    }
    
    if frequency_text not in frequency_map:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите периодичность из списка:",
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TASK_FREQUENCY
    
    # Сохраняем периодичность
    context.user_data['task_creation']['schedule_data']['frequency'] = frequency_map[frequency_text]
    
    # Показываем подтверждение
    return await show_enhanced_task_confirmation(update, context)

async def show_enhanced_task_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подтверждение создания задачи с новой структурой"""
    task_data = context.user_data['task_creation']
    template = task_data['template']
    schedule_data = task_data['schedule_data']
    
    info = format_enhanced_task_confirmation(template, task_data['target_chat_name'], schedule_data)
    
    await update.message.reply_text(
        info,
        parse_mode='Markdown',
        reply_markup=get_task_confirmation_keyboard()
    )
    return CREATE_TASK_CONFIRM

def format_enhanced_task_confirmation(template, chat_name, schedule_data):
    """Форматирует подтверждение создания задачи с новой структурой"""
    try:
        info = "✅ **ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ЗАДАЧИ**\n\n"
        info += "Вы собираетесь создать задачу. Проверьте пожалуйста все данные:\n\n"
        info += f"📝 **Шаблон:** {template['name']}\n"
        info += f"💬 **Telegram чат:** {chat_name}\n"
        info += f"📄 **Текст:** {template['text'][:200]}...\n"
        info += f"🖼️ **Изображение:** {'✅ Есть' if template.get('image') else '❌ Нет'}\n"
        
        # Информация о расписании
        times_str = ", ".join(schedule_data['times'])
        info += f"⏰ **Время отправки:** {times_str} (МСК)\n"
        
        if schedule_data['schedule_type'] == 'week_days':
            days_map = {0: 'Понедельник', 1: 'Вторник', 2: 'Среда', 3: 'Четверг', 
                       4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'}
            days_names = [days_map[day] for day in schedule_data['week_days']]
            info += f"📅 **Дни недели:** {', '.join(days_names)}\n"
        else:
            days_str = ", ".join(map(str, schedule_data['month_days']))
            info += f"📆 **Числа месяца:** {days_str}\n"
        
        frequency_map = {
            'weekly': '1 раз в неделю',
            'biweekly': '1 раз в 2 недели',
            'monthly': '1 раз в месяц'
        }
        frequency_name = frequency_map.get(schedule_data['frequency'], schedule_data['frequency'])
        info += f"🔄 **Периодичность:** {frequency_name}\n\n"
        info += "**Всё верно?**"
        
        return info
    except Exception as e:
        print(f"❌ Ошибка форматирования подтверждения задачи: {e}")
        return "❌ Ошибка загрузки подтверждения задачи"

async def enhanced_create_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания задачи с новой структурой"""
    user_choice = update.message.text
    task_data = context.user_data['task_creation']
    template = task_data['template']
    schedule_data = task_data['schedule_data']
    
    if user_choice == "✅ Подтвердить":
        try:
            # Создаем задачу с указанием целевого чата и расписания
            success, task_id = create_task_with_schedule(
                template_data=template,
                created_by=task_data['created_by'],
                target_chat_id=task_data.get('target_chat_id'),
                schedule_data=schedule_data
            )
            
            if success:
                chat_name = task_data.get('target_chat_name', 'не указан')
                
                message_text = f"✅ Задача успешно создана!\n\n"
                message_text += f"📝 Шаблон: {task_data['template_name']}\n"
                message_text += f"💬 Чат: {chat_name}\n"
                message_text += f"🆔 ID задачи: `{task_id}`\n\n"
                message_text += "⏰ Задача запланирована по расписанию"
                
                await update.message.reply_text(
                    message_text,
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
            
        except Exception as e:
            print(f"💥 Ошибка при создании задачи: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при создании задачи: {str(e)}",
                reply_markup=get_tasks_main_keyboard()
            )
            return TASKS_MAIN
    
    elif user_choice == "✏️ Изменить":
        # Возвращаемся к выбору типа расписания
        await update.message.reply_text(
            "🔄 Возврат к выбору типа расписания:",
            reply_markup=get_schedule_type_keyboard()
        )
        return CREATE_TASK_SCHEDULE_TYPE
    
    elif user_choice == "🔙 Назад":
        # Возвращаемся к выбору периодичности
        await update.message.reply_text(
            "🔄 Возврат к выбору периодичности:",
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TASK_FREQUENCY
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_task_confirmation_keyboard()
        )
        return CREATE_TASK_CONFIRM

# ===== ОСТАЛЬНЫЕ ФУНКЦИИ =====

async def show_tasks_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус всех активных задач"""
    user_id = update.effective_user.id
    
    # Получаем доступные задачи пользователя
    accessible_tasks = get_user_accessible_tasks(user_id)
    
    if not accessible_tasks:
        await update.message.reply_text(
            "📊 **Статус задач**\n\n"
            "❌ Нет активных задач",
            parse_mode='Markdown',
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    message_text = format_task_list_info(accessible_tasks)
    
    await update.message.reply_text(
        message_text,
        parse_mode='Markdown',
        reply_markup=get_tasks_main_keyboard()
    )
    return TASKS_MAIN

# ===== ДЕАКТИВАЦИЯ ЗАДАЧ =====

async def enhanced_deactivate_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало деактивации задачи"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    await update.message.reply_text(
        "🗑️ **Отмена задачи**\n\n"
        "Выберите группу шаблонов:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "deactivate")
    )
    return DEACTIVATE_TASK_GROUP

async def enhanced_deactivate_task_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для деактивации задачи"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 К задачам":
        await enhanced_tasks_main(update, context)
        return TASKS_MAIN
    
    # Извлекаем название группы из текста
    group_name = user_text.replace("🏷️ ", "").strip()
    
    # Находим ID группы по имени
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа шаблонов не найдена",
            reply_markup=get_groups_keyboard(user_id, "deactivate")
        )
        return DEACTIVATE_TASK_GROUP
    
    # Сохраняем ID группы в контекст
    context.user_data['deactivate_group'] = group_id
    context.user_data['deactivate_group_name'] = group_name
    
    # Получаем активные задачи этой группы
    tasks = get_active_tasks_by_group(group_id)
    
    if not tasks:
        await update.message.reply_text(
            f"📭 В группе шаблонов '{group_name}' нет активных задач",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Создаем клавиатуру с задачами
    keyboard = []
    for task_id, task in tasks.items():
        keyboard.append([f"🗑️ {task.template_name}"])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"🗑️ **Выберите задачу для отмены:**\n\n"
        f"Группа шаблонов: {group_name}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DEACTIVATE_TASK_SELECT

async def enhanced_deactivate_task_select_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор задачи для деактивации"""
    task_text = update.message.text
    
    # Если нажата кнопка "Назад"
    if task_text == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы шаблонов",
            reply_markup=get_groups_keyboard(user_id, "deactivate")
        )
        return DEACTIVATE_TASK_GROUP
    
    # Извлекаем название шаблона из текста
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
    
    for tid, tdata in tasks.items():
        if tdata.template_name == template_name:
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

async def enhanced_deactivate_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение деактивации задачи"""
    user_choice = update.message.text
    task_id = context.user_data.get('deactivating_task_id')
    task = context.user_data.get('deactivating_task')
    
    if user_choice == "✅ Да, отменить задачу":
        if task_id and task:
            success, message = deactivate_task(task_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Задача '{task.template_name}' успешно отменена!",
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

# ===== ТЕСТИРОВАНИЕ С ВЫБОРОМ ЧАТА =====

async def enhanced_test_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало тестирования задачи с выбором чата"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    # Проверяем доступные чаты
    accessible_chats = await chat_access_manager.get_user_accessible_chats_with_membership(user_id)
    if not accessible_chats:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одному Telegram чату",
            reply_markup=get_tasks_main_keyboard()
        )
        return TASKS_MAIN
    
    context.user_data['task_creation'] = {
        'created_by': user_id,
        'is_test': True,
        'accessible_chats': accessible_chats
    }
    
    await update.message.reply_text(
        "🧪 **Тестирование задачи**\n\n"
        "Шаг 1 из 3: Выберите группу шаблонов:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "test")
    )
    return TEST_TASK_GROUP

async def enhanced_test_task_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для тестирования"""
    return await enhanced_create_task_select_group(update, context)

async def enhanced_test_task_select_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для тестирования"""
    return await enhanced_create_task_select_template(update, context)

async def enhanced_test_task_select_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор чата для тестирования"""
    user_text = update.message.text
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 Назад":
        # Возвращаемся к выбору шаблона
        group_id = context.user_data['task_creation']['group']
        templates = get_templates_by_group(group_id)
        
        keyboard = []
        for template_id, template in templates:
            keyboard.append([f"📝 {template['name']}"])
        keyboard.append(["🔙 Назад"])
        
        await update.message.reply_text(
            "🔄 **Выберите шаблон:**",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return TEST_TASK_SELECT
    
    # Обрабатываем выбор чата по номеру
    try:
        chat_number = int(user_text.split('.')[0])
        accessible_chats = context.user_data['task_creation']['accessible_chats']
        
        if 1 <= chat_number <= len(accessible_chats):
            selected_chat = accessible_chats[chat_number - 1]
            
            # Сохраняем выбранный чат
            context.user_data['task_creation']['target_chat_id'] = selected_chat['chat_id']
            context.user_data['task_creation']['target_chat_name'] = selected_chat['chat_name']
            
            # Показываем подтверждение для тестовой задачи
            task_data = context.user_data['task_creation']
            template = task_data['template']
            chat_name = task_data.get('target_chat_name', 'текущий чат')
            
            info = f"🧪 **ПОДТВЕРЖДЕНИЕ ТЕСТОВОЙ ЗАДАЧИ**\n\n"
            info += f"📝 **Шаблон:** {template['name']}\n"
            info += f"💬 **Telegram чат:** {chat_name}\n"
            info += f"📄 **Текст:** {template['text'][:200]}...\n"
            info += f"🖼️ **Изображение:** {'✅ Есть' if template.get('image') else '❌ Нет'}\n\n"
            info += "Сообщение будет отправлено немедленно!"
            
            await update.message.reply_text(
                info,
                parse_mode='Markdown',
                reply_markup=get_task_confirmation_keyboard()
            )
            return TEST_TASK_CONFIRM
            
        else:
            raise ValueError("Неверный номер чата")
            
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Пожалуйста, выберите чат из списка по номеру:",
            reply_markup=get_chat_selection_keyboard(context.user_data['task_creation']['accessible_chats'])
        )
        return TEST_TASK_CHAT_SELECT

async def enhanced_test_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение тестирования"""
    user_choice = update.message.text
    task_data = context.user_data['task_creation']
    template = task_data['template']
    
    if user_choice == "✅ Подтвердить":
        try:
            # Создаем тестовую задачу
            success, task_id = create_task_from_template(
                template_data=template,
                created_by=task_data['created_by'],
                target_chat_id=task_data.get('target_chat_id'),
                is_test=True
            )
            
            if success:
                chat_name = task_data.get('target_chat_name', 'текущий чат')
                
                await update.message.reply_text(
                    f"✅ Тестовая задача успешно создана!\n\n"
                    f"📝 Шаблон: {task_data['template_name']}\n"
                    f"💬 Чат: {chat_name}\n"
                    f"🆔 ID задачи: `{task_id}`\n\n"
                    f"⏰ Сообщение будет отправлено через 5 секунд...",
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
            
        except Exception as e:
            print(f"💥 Ошибка при создании тестовой задачи: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при создании тестовой задачи: {str(e)}",
                reply_markup=get_tasks_main_keyboard()
            )
            return TASKS_MAIN
    
    elif user_choice == "✏️ Изменить":
        accessible_chats = context.user_data['task_creation']['accessible_chats']
        await update.message.reply_text(
            "🔄 Возврат к выбору чата:",
            reply_markup=get_chat_selection_keyboard(accessible_chats)
        )
        return TEST_TASK_CHAT_SELECT
    
    elif user_choice == "🔙 Назад":
        accessible_chats = context.user_data['task_creation']['accessible_chats']
        await update.message.reply_text(
            "🔄 Возврат к выбору чата:",
            reply_markup=get_chat_selection_keyboard(accessible_chats)
        )
        return TEST_TASK_CHAT_SELECT
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_task_confirmation_keyboard()
        )
        return TEST_TASK_CONFIRM

# ===== ФУНКЦИЯ ОТМЕНЫ =====

async def enhanced_cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена и возврат в главное меню"""
    context.user_data.clear()
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🔙 Возврат в главное меню",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END

def get_enhanced_task_conversation_handler():
    """Возвращает улучшенный ConversationHandler для задач с новой структурой"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Задачи$"), enhanced_tasks_main)],
        states={
            TASKS_MAIN: [
                MessageHandler(filters.Regex("^➕ Создать задачу$"), enhanced_create_task_start),
                MessageHandler(filters.Regex("^🗑️ Отменить задачу$"), enhanced_deactivate_task_start),
                MessageHandler(filters.Regex("^🧪 Тестирование$"), enhanced_test_task_start),
                MessageHandler(filters.Regex("^📊 Статус задач$"), show_tasks_status),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), enhanced_cancel_task)
            ],
            
            # === СОЗДАНИЕ ЗАДАЧ С НОВОЙ СТРУКТУРОЙ ===
            CREATE_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_select_group),
                MessageHandler(filters.Regex("^🔙 К задачам$"), enhanced_tasks_main)
            ],
            CREATE_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_select_template),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_start)
            ],
            CREATE_TASK_CHAT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_select_chat),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_select_template)
            ],
            CREATE_TASK_SCHEDULE_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_select_schedule_type),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_select_chat)
            ],
            CREATE_TASK_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_input_time),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_select_schedule_type)
            ],
            CREATE_TASK_WEEK_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_select_week_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_input_time)
            ],
            CREATE_TASK_MONTH_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_input_month_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_input_time)
            ],
            CREATE_TASK_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_select_frequency),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_input_time)
            ],
            CREATE_TASK_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_create_task_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_create_task_select_frequency)
            ],
            
            # === ДЕАКТИВАЦИЯ ЗАДАЧ ===
            DEACTIVATE_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_deactivate_task_select_group),
                MessageHandler(filters.Regex("^🔙 К задачам$"), enhanced_tasks_main)
            ],
            DEACTIVATE_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_deactivate_task_select_task),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_deactivate_task_start)
            ],
            DEACTIVATE_TASK_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_deactivate_task_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_deactivate_task_select_task)
            ],
            
            # === ТЕСТИРОВАНИЕ С ВЫБОРОМ ЧАТА ===
            TEST_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_test_task_select_group),
                MessageHandler(filters.Regex("^🔙 К задачам$"), enhanced_tasks_main)
            ],
            TEST_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_test_task_select_template),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_test_task_start)
            ],
            TEST_TASK_CHAT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_test_task_select_chat),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_test_task_select_template)
            ],
            TEST_TASK_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enhanced_test_task_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), enhanced_test_task_select_chat)
            ],
        },
        fallbacks=[CommandHandler("cancel", enhanced_cancel_task)]
    )