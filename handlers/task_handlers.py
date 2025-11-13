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

# Обновленные состояния для ConversationHandler задач
(
    TASKS_MAIN, CREATE_TASK_GROUP, CREATE_TASK_SELECT, CREATE_TASK_CHAT_SELECT, CREATE_TASK_CONFIRM,
    CREATE_TASK_EDIT, DEACTIVATE_TASK_GROUP, DEACTIVATE_TASK_SELECT, DEACTIVATE_TASK_CONFIRM,
    TEST_TASK_GROUP, TEST_TASK_SELECT, TEST_TASK_CHAT_SELECT, TEST_TASK_CONFIRM
) = range(13)  # Добавили состояния для выбора чата

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
    
    print(f"🔍 Пользователь выбрал: {user_text}")
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 Назад":
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
    
    # ПЕРЕХОДИМ К ВЫБОРУ ЧАТА - НОВЫЙ КОД
    from chat_context_manager import chat_context_manager
    accessible_chats, message = chat_context_manager.format_chats_for_selection(user_id)

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
        reply_markup=get_back_keyboard()
    )
    return CREATE_TASK_CHAT_SELECT

# НОВАЯ ФУНКЦИЯ: Выбор чата для задачи
async def create_task_select_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор чата для отправки задачи"""
    user_id = update.effective_user.id
    user_text = update.message.text
    
    # Если нажата кнопка "Назад"
    if user_text == "🔙 Назад":
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
    
    try:
        chat_number = int(user_text)
        accessible_chats = context.user_data['accessible_chats']
        
        if 1 <= chat_number <= len(accessible_chats):
            selected_chat = accessible_chats[chat_number - 1]
            context.user_data['task_creation']['target_chat_id'] = selected_chat['chat_id']
            context.user_data['task_creation']['target_chat_name'] = selected_chat['chat_name']
            
            # Переходим к подтверждению
            task_data = context.user_data['task_creation']
            template = task_data['template']
            info = format_task_confirmation(template, selected_chat['chat_name'])
            
            await update.message.reply_text(
                info,
                parse_mode='Markdown',
                reply_markup=get_task_confirmation_keyboard()
            )
            return CREATE_TASK_CONFIRM
        else:
            raise ValueError
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный номер чата. Введите номер из списка:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_CHAT_SELECT

def format_task_confirmation(template, chat_name=None):
    """Форматирует подтверждение создания задачи"""
    days_names = []
    if template.get('days'):
        from template_manager import DAYS_OF_WEEK
        days_names = [DAYS_OF_WEEK[day] for day in template['days']]
    
    frequency_map = {
        "weekly": "1 в неделю",
        "2_per_month": "2 в месяц", 
        "monthly": "1 в месяц"
    }
    frequency = frequency_map.get(template.get('frequency'), template.get('frequency', 'Не указана'))
    
    info = "✅ **ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ЗАДАЧИ**\n\n"
    info += "Вы собираетесь создать задачу. Проверьте пожалуйста все данные:\n\n"
    info += f"📝 **Шаблон:** {template['name']}\n"
    
    if chat_name:
        info += f"💬 **Чат для отправки:** {chat_name}\n"
    
    info += f"📄 **Текст:** {template.get('text', '')[:200]}...\n"
    info += f"🖼️ **Изображение:** {'✅ Есть' if template.get('image') else '❌ Нет'}\n"
    info += f"⏰ **Время отправки:** {template.get('time', 'Не указано')} (МСК)\n"
    info += f"📅 **Дни отправки:** {', '.join(days_names) if days_names else 'Не указаны'}\n"
    info += f"🔄 **Периодичность:** {frequency}\n\n"
    info += "**Всё верно?**"
    
    return info

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
            target_chat_id=target_chat_id  # Передаем ID чата
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
        accessible_chats = context.user_data['accessible_chats']
        message = "💬 **Выберите Telegram чат для отправки:**\n\n"
        for i, chat in enumerate(accessible_chats, 1):
            message += f"{i}. {chat['chat_name']} (ID: {chat['chat_id']})\n"
        message += "\nВведите номер чата:"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        return CREATE_TASK_CHAT_SELECT
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_task_confirmation_keyboard()
        )
        return CREATE_TASK_CONFIRM

# Остальные функции остаются без изменений (deactivate_task_start, test_task_start и т.д.)
# ... [остальной код из предыдущей версии] ...

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
                MessageHandler(filters.Regex("^🔙 Назад$"), tasks_main)
            ],
            CREATE_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_select_template),
                MessageHandler(filters.Regex("^📝 .*"), create_task_select_template),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_task_start)
            ],
            CREATE_TASK_CHAT_SELECT: [  # НОВОЕ СОСТОЯНИЕ
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
            
            # ... остальные состояния без изменений ...
            
            # === ТЕСТИРОВАНИЕ ===
            TEST_TASK_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, test_task_select_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), test_task_select_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), test_task_select_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), tasks_main)
            ],
            TEST_TASK_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, test_task_select_template),
                MessageHandler(filters.Regex("^📝 .*"), test_task_select_template),
                MessageHandler(filters.Regex("^🔙 Назад$"), test_task_start)
            ],
            TEST_TASK_CHAT_SELECT: [  # НОВОЕ СОСТОЯНИЕ
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_select_chat),  # Та же функция
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