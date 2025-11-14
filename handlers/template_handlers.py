from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.template_keyboards import (
    get_templates_main_keyboard, get_groups_keyboard,
    get_template_confirmation_keyboard, get_template_edit_keyboard,
    get_back_keyboard, get_days_keyboard, get_frequency_keyboard,
    get_template_list_menu_keyboard, get_delete_confirmation_keyboard,
    get_skip_keyboard, get_image_choice_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from template_manager import (
    get_user_accessible_groups, get_templates_by_group,
    get_template_by_id, format_template_info, create_template,
    save_image, delete_template_by_id, format_template_list_info,
    get_template_groups, update_template_field, format_template_preview,
    get_frequency_types, get_week_days, validate_template_data,
    delete_template_and_image, format_group_templates_info,
    get_all_templates, load_groups
)
from auth_manager import auth_manager

# === СОСТОЯНИЯ CONVERSATION HANDLER ===
(TEMPLATES_MAIN, TEMPLATE_LIST_MENU, TEMPLATE_LIST_ALL, 
 TEMPLATE_LIST_BY_GROUP, CREATE_TEMPLATE_GROUP, CREATE_TEMPLATE_NAME, 
 CREATE_TEMPLATE_TEXT, CREATE_TEMPLATE_IMAGE, CREATE_TEMPLATE_TIME,
 CREATE_TEMPLATE_DAYS, CREATE_TEMPLATE_FREQUENCY, CREATE_TEMPLATE_CONFIRM,
 EDIT_TEMPLATE_SELECT_GROUP, EDIT_TEMPLATE_SELECT, EDIT_TEMPLATE_FIELD,
 EDIT_TEMPLATE_NAME, EDIT_TEMPLATE_TEXT, EDIT_TEMPLATE_IMAGE,
 EDIT_TEMPLATE_TIME, EDIT_TEMPLATE_DAYS, EDIT_TEMPLATE_FREQUENCY,
 DELETE_TEMPLATE_SELECT_GROUP, DELETE_TEMPLATE_SELECT, DELETE_TEMPLATE_CONFIRM) = range(24)

# Дни недели для отображения
DAYS_OF_WEEK = {
    '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
    '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
}

# === ОСНОВНЫЕ ФУНКЦИИ ===

async def templates_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню шаблонов (уровень 2)"""
    user_id = update.effective_user.id
    auth_manager.update_user_role_if_needed(user_id)
    
    await update.message.reply_text(
        "📋 **Управление шаблонами**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# ===== СПИСОК ШАБЛОНОВ =====

async def template_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню списка шаблонов (уровень 3)"""
    await update.message.reply_text(
        "📋 **Список шаблонов**\n\n"
        "Выберите способ просмотра:",
        parse_mode='Markdown',
        reply_markup=get_template_list_menu_keyboard()
    )
    return TEMPLATE_LIST_MENU

async def template_list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все шаблоны пользователя"""
    user_id = update.effective_user.id
    
    # Получаем все доступные группы
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_template_list_menu_keyboard()
        )
        return TEMPLATE_LIST_MENU
    
    # Получаем все шаблоны
    all_templates = get_all_templates()
    
    # Фильтруем шаблоны по доступным группам
    user_templates = {}
    for template_id, template in all_templates.items():
        if template.get('group') in accessible_groups:
            user_templates[template_id] = template
    
    if not user_templates:
        await update.message.reply_text(
            "📭 У вас нет доступных шаблонов",
            reply_markup=get_template_list_menu_keyboard()
        )
        return TEMPLATE_LIST_MENU
    
    # Форматируем информацию о шаблонах
    message = format_template_list_info(user_templates)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_template_list_menu_keyboard()
    )
    return TEMPLATE_LIST_MENU

async def template_list_by_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало просмотра шаблонов по группам"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_template_list_menu_keyboard()
        )
        return TEMPLATE_LIST_MENU
    
    await update.message.reply_text(
        "🏷️ **Просмотр шаблонов по группам**\n\n"
        "Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "list")
    )
    return TEMPLATE_LIST_BY_GROUP

async def template_list_by_group_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает шаблоны выбранной группы"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await template_list_menu(update, context)
        return TEMPLATE_LIST_MENU
    
    # Извлекаем название группы из текста (убираем эмодзи)
    group_name = user_text.replace("🏷️ ", "").strip()
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
        return TEMPLATE_LIST_BY_GROUP
    
    # Получаем шаблоны группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе '{group_name}' нет шаблонов",
            reply_markup=get_groups_keyboard(user_id, "list")
        )
        return TEMPLATE_LIST_BY_GROUP
    
    # Форматируем информацию о шаблонах группы
    message = format_group_templates_info(group_id)
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "list")
    )
    return TEMPLATE_LIST_BY_GROUP

# ===== СОЗДАНИЕ ШАБЛОНА =====

async def create_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания шаблона"""
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Инициализируем данные нового шаблона
    context.user_data['new_template'] = {
        'created_by': user_id
    }
    
    await update.message.reply_text(
        "➕ **Создание нового шаблона**\n\n"
        "Шаг 1 из 8: Выберите группу для шаблона:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "create")
    )
    return CREATE_TEMPLATE_GROUP

async def create_template_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для нового шаблона"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATES_MAIN
    
    # Извлекаем название группы из текста
    group_name = user_text.replace("🏷️ ", "").strip()
    user_id = update.effective_user.id
    
    # Находим ID группы по имени
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    group_data = None
    
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            group_data = gdata
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа не найдена",
            reply_markup=get_groups_keyboard(user_id, "create")
        )
        return CREATE_TEMPLATE_GROUP
    
    # Сохраняем данные группы
    context.user_data['new_template']['group'] = group_id
    context.user_data['current_group'] = group_data
    
    await update.message.reply_text(
        "Шаг 2 из 8: Введите название шаблона:",
        reply_markup=get_back_keyboard()
    )
    return CREATE_TEMPLATE_NAME

async def create_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия шаблона"""
    name = update.message.text.strip()
    
    if name == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы:",
            reply_markup=get_groups_keyboard(user_id, "create")
        )
        return CREATE_TEMPLATE_GROUP
    
    if not name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_NAME
    
    context.user_data['new_template']['name'] = name
    
    await update.message.reply_text(
        "Шаг 3 из 8: Введите текст шаблона:",
        reply_markup=get_back_keyboard()
    )
    return CREATE_TEMPLATE_TEXT

async def create_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод текста шаблона"""
    text = update.message.text.strip()
    
    if text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к вводу названия:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_NAME
    
    if not text:
        await update.message.reply_text(
            "❌ Текст не может быть пустым. Введите текст:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_TEXT
    
    context.user_data['new_template']['text'] = text
    
    await update.message.reply_text(
        "Шаг 4 из 8: Пришлите изображение для шаблона или нажмите '⏭️ Пропустить':",
        reply_markup=get_skip_keyboard()
    )
    return CREATE_TEMPLATE_IMAGE

async def create_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображения для шаблона"""
    if update.message.text == "⏭️ Пропустить":
        context.user_data['new_template']['image'] = None
        await update.message.reply_text(
            "Шаг 5 из 8: Введите время отправки в формате ЧЧ:ММ (МСК):",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_TIME
    
    if update.message.photo:
        # Сохраняем изображение
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_content = await photo_file.download_as_bytearray()
        
        # Создаем временный ID для сохранения
        temp_id = f"temp_{update.effective_user.id}_{update.update_id}"
        image_path = save_image(photo_content, temp_id)
        
        if image_path:
            context.user_data['new_template']['image'] = image_path
            await update.message.reply_text(
                "✅ Изображение сохранено!\n\n"
                "Шаг 5 из 8: Введите время отправки в формате ЧЧ:ММ (МСК):",
                reply_markup=get_back_keyboard()
            )
            return CREATE_TEMPLATE_TIME
        else:
            await update.message.reply_text(
                "❌ Ошибка сохранения изображения. Попробуйте еще раз или пропустите:",
                reply_markup=get_skip_keyboard()
            )
            return CREATE_TEMPLATE_IMAGE
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, пришлите изображение или нажмите '⏭️ Пропустить':",
            reply_markup=get_skip_keyboard()
        )
        return CREATE_TEMPLATE_IMAGE

async def create_template_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени отправки"""
    time_str = update.message.text.strip()
    
    if time_str == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к добавлению изображения:",
            reply_markup=get_skip_keyboard()
        )
        return CREATE_TEMPLATE_IMAGE
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            context.user_data['new_template']['time'] = time_str
            
            # Инициализируем список дней
            context.user_data['new_template']['days'] = []
            
            await update.message.reply_text(
                "📅 **Шаг 6: Выберите дни отправки**\n\n"
                "Выберите первый день из списка:",
                parse_mode='Markdown',
                reply_markup=get_days_keyboard()
            )
            return CREATE_TEMPLATE_DAYS
        else:
            raise ValueError
    except:
        await update.message.reply_text(
            "❌ Неверный формат времени.\n"
            "Используйте формат ЧЧ:ММ (например, 14:30):",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_TIME

async def create_template_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора дней"""
    user_text = update.message.text
    template_data = context.user_data['new_template']
    selected_days = template_data.get('days', [])
    
    if user_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к вводу времени:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_TIME
    
    # Обработка завершения выбора дней
    if user_text == "✅ Завершить выбор дней":
        if not selected_days:
            await update.message.reply_text(
                "❌ Нужно выбрать хотя бы один день",
                reply_markup=get_days_keyboard(selected_days)
            )
            return CREATE_TEMPLATE_DAYS
        
        # Переходим к выбору периодичности
        return await proceed_to_frequency(update, context)
    
    # Обработка выбора дополнительного дня
    if user_text == "➕ Выбрать еще день":
        await update.message.reply_text(
            "📅 **Выберите ДОПОЛНИТЕЛЬНЫЙ день отправки:**",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(selected_days, is_additional=True)
        )
        return CREATE_TEMPLATE_DAYS
    
    # Обработка выбора конкретного дня
    day_number = None
    for num, text in DAYS_OF_WEEK.items():
        if text in user_text:  # Учитываем что может быть отметка ✅
            day_number = num
            break
    
    if day_number is None:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите день из списка",
            reply_markup=get_days_keyboard(selected_days)
        )
        return CREATE_TEMPLATE_DAYS
    
    # Добавляем или удаляем день
    if day_number in selected_days:
        selected_days.remove(day_number)
    else:
        selected_days.append(day_number)
    
    template_data['days'] = selected_days
    
    # Обновляем клавиатуру
    await update.message.reply_text(
        f"📅 Выбрано дней: {len(selected_days)}\n"
        "Продолжайте выбор или завершите:",
        reply_markup=get_days_keyboard(selected_days, is_additional=len(selected_days) > 0)
    )
    return CREATE_TEMPLATE_DAYS

async def proceed_to_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к выбору периодичности"""
    template_data = context.user_data['new_template']
    selected_days = template_data.get('days', [])
    selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
    
    await update.message.reply_text(
        f"🔄 **Шаг 7: Выберите периодичность**\n\n"
        f"✅ Выбраны дни: {', '.join(selected_days_text)}",
        parse_mode='Markdown',
        reply_markup=get_frequency_keyboard()
    )
    return CREATE_TEMPLATE_FREQUENCY

async def create_template_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор периодичности"""
    frequency_text = update.message.text
    
    if frequency_text == "🔙 Назад":
        template_data = context.user_data['new_template']
        selected_days = template_data.get('days', [])
        await update.message.reply_text(
            "🔄 Возврат к выбору дней:",
            reply_markup=get_days_keyboard(selected_days, is_additional=True)
        )
        return CREATE_TEMPLATE_DAYS
    
    frequency_map = {
        "📅 1 в неделю": "weekly",
        "🗓️ 2 в месяц": "2_per_month",
        "📆 1 в месяц": "monthly"
    }
    
    if frequency_text not in frequency_map:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите периодичность из списка",
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TEMPLATE_FREQUENCY
    
    context.user_data['new_template']['frequency'] = frequency_map[frequency_text]
    
    # Показываем подтверждение
    template_data = context.user_data['new_template']
    preview = format_template_preview(template_data)
    
    await update.message.reply_text(
        f"✅ **Подтверждение создания шаблона**\n\n{preview}\n\n"
        "Всё верно? Подтверждаем создание шаблона?",
        parse_mode='Markdown',
        reply_markup=get_template_confirmation_keyboard()
    )
    return CREATE_TEMPLATE_CONFIRM

async def create_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания шаблона"""
    choice = update.message.text
    
    if choice == "✅ Подтвердить":
        template_data = context.user_data['new_template']
        success, template_id = create_template(template_data)
        
        if success:
            await update.message.reply_text(
                f"✅ Шаблон успешно создан!\n\n"
                f"ID шаблона: `{template_id}`",
                parse_mode='Markdown',
                reply_markup=get_templates_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при создании шаблона",
                reply_markup=get_templates_main_keyboard()
            )
        
        # Очищаем временные данные
        context.user_data.clear()
        return TEMPLATES_MAIN
    
    elif choice == "✏️ Изменить":
        # TODO: Реализовать редактирование на этапе создания
        await update.message.reply_text(
            "⚠️ Редактирование на этапе создания будет реализовано позже\n\n"
            "Пожалуйста, подтвердите создание или начните заново",
            reply_markup=get_template_confirmation_keyboard()
        )
        return CREATE_TEMPLATE_CONFIRM
    
    elif choice == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору периодичности:",
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TEMPLATE_FREQUENCY
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_template_confirmation_keyboard()
        )
        return CREATE_TEMPLATE_CONFIRM

# ===== РЕДАКТИРОВАНИЕ ШАБЛОНОВ =====

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
    return EDIT_TEMPLATE_SELECT_GROUP

async def edit_template_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для редактирования"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATES_MAIN
    
    # TODO: Реализовать выбор шаблона для редактирования
    await update.message.reply_text(
        "✏️ **Редактирование шаблонов**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# ===== УДАЛЕНИЕ ШАБЛОНОВ =====

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
    return DELETE_TEMPLATE_SELECT_GROUP

async def delete_template_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для удаления"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATES_MAIN
    
    # TODO: Реализовать выбор шаблона для удаления
    await update.message.reply_text(
        "🗑️ **Удаление шаблонов**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# ===== ФУНКЦИЯ ОТМЕНЫ =====

async def cancel_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def get_template_conversation_handler():
    """Возвращает настроенный ConversationHandler для шаблонов"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Шаблоны$"), templates_main)],
        states={
            # Главное меню шаблонов
            TEMPLATES_MAIN: [
                MessageHandler(filters.Regex("^📋 Список шаблонов$"), template_list_menu),
                MessageHandler(filters.Regex("^➕ Добавить новый$"), create_template_start),
                MessageHandler(filters.Regex("^✏️ Редактировать$"), edit_template_start),
                MessageHandler(filters.Regex("^🗑️ Удалить$"), delete_template_start),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), cancel_template)
            ],
            
            # Меню списка шаблонов
            TEMPLATE_LIST_MENU: [
                MessageHandler(filters.Regex("^📋 Все шаблоны$"), template_list_all),
                MessageHandler(filters.Regex("^🏷️ По группам$"), template_list_by_group_start),
                MessageHandler(filters.Regex("^🔙 К шаблонам$"), templates_main)
            ],
            
            # Просмотр по группам
            TEMPLATE_LIST_BY_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_by_group_show),
                MessageHandler(filters.Regex("^🔙 Назад$"), template_list_menu)
            ],
            
            # Создание шаблона
            CREATE_TEMPLATE_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_choose_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            CREATE_TEMPLATE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_name),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_start)
            ],
            CREATE_TEMPLATE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_text),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_name)
            ],
            CREATE_TEMPLATE_IMAGE: [
                MessageHandler(filters.PHOTO, create_template_image),
                MessageHandler(filters.Regex("^⏭️ Пропустить$"), create_template_image),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_text)
            ],
            CREATE_TEMPLATE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_time),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_image)
            ],
            CREATE_TEMPLATE_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_time)
            ],
            CREATE_TEMPLATE_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_frequency),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_days)
            ],
            CREATE_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_frequency)
            ],
            
            # Редактирование шаблона
            EDIT_TEMPLATE_SELECT_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_select),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            
            # Удаление шаблона
            DELETE_TEMPLATE_SELECT_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_select),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_template)]
    )