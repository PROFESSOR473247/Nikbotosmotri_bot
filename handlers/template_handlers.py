from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.template_keyboards import (
    get_templates_main_keyboard, get_groups_keyboard,
    get_template_confirmation_keyboard, get_template_edit_keyboard,
    get_back_keyboard, get_days_keyboard, get_frequency_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from template_manager import (
    get_user_accessible_groups, get_templates_by_group,
    get_template_by_id, format_template_info, create_template,
    save_image, delete_template_by_id, format_template_list_info,
    get_template_groups, update_template_field, format_template_preview,
    get_frequency_types, get_week_days, validate_template_data,
    delete_template_and_image, format_group_templates_info
)
from auth_manager import auth_manager

# === ЗАЩИТНЫЕ ФУНКЦИИ ===

def safe_format_template_days(template):
    """Безопасно форматирует дни шаблона"""
    try:
        days = template.get('days', [])
        if not days:
            return []
        
        DAYS_OF_WEEK = {
            '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
            '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
        }
        
        return [DAYS_OF_WEEK.get(str(day), f"День {day}") for day in days]
    except Exception as e:
        print(f"⚠️ Ошибка форматирования дней шаблона: {e}")
        return []

# === СОСТОЯНИЯ CONVERSATION HANDLER ===
# ИСПРАВЛЕНО: правильные названия состояний
(TEMPLATES_MAIN, CREATE_TEMPLATE_GROUP, CREATE_TEMPLATE_NAME, 
 CREATE_TEMPLATE_TEXT, CREATE_TEMPLATE_IMAGE, CREATE_TEMPLATE_TIME,
 CREATE_TEMPLATE_DAYS, CREATE_TEMPLATE_FREQUENCY, CREATE_TEMPLATE_CONFIRM,
 TEMPLATE_LIST, TEMPLATE_LIST_CHOOSE_GROUP, TEMPLATE_DETAILS,
 DELETE_TEMPLATE_SELECT, DELETE_TEMPLATE_CONFIRM, EDIT_TEMPLATE_SELECT,
 EDIT_TEMPLATE_FIELD, EDIT_TEMPLATE_NAME, EDIT_TEMPLATE_TEXT,
 EDIT_TEMPLATE_IMAGE, EDIT_TEMPLATE_TIME, EDIT_TEMPLATE_DAYS,
 EDIT_TEMPLATE_FREQUENCY, DELETE_TEMPLATE_FINAL) = range(23)

# Дни недели для отображения
DAYS_OF_WEEK = {
    '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
    '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
}

# === ОСНОВНЫЕ ФУНКЦИИ ===
async def templates_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню шаблонов"""
    user_id = update.effective_user.id
    auth_manager.update_user_role_if_needed(user_id)
    
    await update.message.reply_text(
        "📋 **Управление шаблонов**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

# ===== СПИСОК ШАБЛОНОВ =====

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

async def template_list_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает шаблоны выбранной группы"""
    try:
        group_id = context.user_data['selected_group']
        templates = get_templates_by_group(group_id)
        
        if not templates:
            await update.message.reply_text(
                "📭 В этой группе нет шаблонов",
                reply_markup=get_template_list_keyboard()
            )
            return TEMPLATE_LIST
        
        message = format_group_templates_info(group_id)
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=get_template_list_keyboard()
        )
        return TEMPLATE_LIST
    except Exception as e:
        print(f"❌ Ошибка в template_list_choose_group: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при загрузке шаблонов",
            reply_markup=get_template_list_keyboard()
        )
        return TEMPLATE_LIST

# ===== СОЗДАНИЕ ШАБЛОНА =====

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
        'created_by': user_id,
        'subgroup': None  # Подгруппы больше не используются
    }
    
    await update.message.reply_text(
        "➕ **Создание нового шаблона**\n\n"
        "Шаг 1 из 8: Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "add")
    )
    return ADD_TEMPLATE_GROUP

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
    
    # Пропускаем выбор подгруппы - сразу переходим к названию
    await update.message.reply_text(
        "Шаг 2 из 8: Введите название шаблона:",
        reply_markup=get_back_keyboard()
    )
    return ADD_TEMPLATE_NAME

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
        "Шаг 3 из 8: Введите текст шаблона:",
        reply_markup=get_back_keyboard()
    )
    return ADD_TEMPLATE_TEXT

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
        "Шаг 4 из 8: Пришлите изображение для шаблона или нажмите 'Пропустить':",
        reply_markup=get_skip_keyboard()
    )
    return ADD_TEMPLATE_IMAGE

async def add_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображения для шаблона"""
    if update.message.text == "⏭️ Пропустить":
        context.user_data['new_template']['image'] = None
        await update.message.reply_text(
            "Шаг 5 из 8: Введите время отправки в формате ЧЧ:ММ (МСК):",
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
                "Шаг 5 из 8: Введите время отправки в формате ЧЧ:ММ (МСК):",
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

async def add_template_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени отправки"""
    time_str = update.message.text.strip()
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            context.user_data['new_template']['time'] = time_str
            
            # Инициализируем список дней если его нет
            if 'days' not in context.user_data['new_template']:
                context.user_data['new_template']['days'] = []
            
            await update.message.reply_text(
                "📅 **Шаг 6: Выберите день отправки:**\n\n"
                "Выберите первый день из списка:",
                parse_mode='Markdown',
                reply_markup=get_days_keyboard()
            )
            return ADD_TEMPLATE_DAYS
    except:
        pass
    
    await update.message.reply_text(
        "❌ Неверный формат времени.\n"
        "Используйте формат ЧЧ:ММ (например, 14:30):",
        reply_markup=get_back_keyboard()
    )
    return ADD_TEMPLATE_TIME

async def add_template_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора дней"""
    user_text = update.message.text
    template_data = context.user_data['new_template']
    selected_days = template_data.get('days', [])
    
    # Обработка кнопки "Завершить выбор дней"
    if user_text == "✅ Завершить выбор дней":
        if not selected_days:
            await update.message.reply_text(
                "❌ Нужно выбрать хотя бы один день",
                reply_markup=get_days_keyboard(selected_days)
            )
            return ADD_TEMPLATE_DAYS
        
        # Переходим к выбору периодичности
        return await proceed_to_frequency(update, context)
    
    # Обработка кнопки "➕ Выбрать еще день"
    if user_text == "➕ Выбрать еще день":
        await update.message.reply_text(
            "📅 **Выберите ДОПОЛНИТЕЛЬНЫЙ день отправки:**\n\n"
            f"Уже выбрано: {', '.join([DAYS_OF_WEEK[d] for d in selected_days])}",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(selected_days, is_additional=True)
        )
        return ADD_TEMPLATE_DAYS
    
    # Обработка кнопки "➡️ Перейти к следующему шагу"
    if user_text == "➡️ Перейти к следующему шагу":
        return await proceed_to_frequency(update, context)
    
    # Обработка выбора конкретного дня
    day_number = None
    for num, text in DAYS_OF_WEEK.items():
        if text == user_text:
            day_number = num
            break
    
    if day_number is None:
        await update.message.reply_text(
            "❌ Пожалуйста, выберите день из списка",
            reply_markup=get_days_keyboard(selected_days)
        )
        return ADD_TEMPLATE_DAYS
    
    # Добавляем день если его еще нет
    if day_number not in selected_days:
        selected_days.append(day_number)
        template_data['days'] = selected_days
    
    # Формируем текст выбранных дней
    selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
    
    # Определяем на каком мы шаге
    if len(selected_days) == 1:
        # Первый день выбран
        await update.message.reply_text(
            f"✅ **Первый день выбран:** {selected_days_text[0]}\n\n"
            "📅 **Шаг 7: Хотите добавить еще дни?**\n\n"
            "Вы можете добавить дополнительные дни отправки или перейти к следующему шагу",
            parse_mode='Markdown',
            reply_markup=get_days_continue_keyboard(selected_days_text)
        )
        return ADD_TEMPLATE_DAYS
    else:
        # Уже есть выбранные дни
        await update.message.reply_text(
            f"✅ **Выбраны дни:** {', '.join(selected_days_text)}\n\n"
            "📅 **Шаг 7: Хотите добавить еще дни?**\n\n"
            "Вы можете добавить дополнительные дни отправки или перейти к следующему шагу",
            parse_mode='Markdown',
            reply_markup=get_days_continue_keyboard(selected_days_text)
        )
        return ADD_TEMPLATE_DAYS

async def proceed_to_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к выбору периодичности"""
    template_data = context.user_data['new_template']
    selected_days = template_data.get('days', [])
    selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
    
    await update.message.reply_text(
        f"🔄 **Шаг 8: Выберите периодичность**\n\n"
        f"✅ Выбраны дни: {', '.join(selected_days_text)}",
        parse_mode='Markdown',
        reply_markup=get_frequency_keyboard()
    )
    return ADD_TEMPLATE_FREQUENCY

async def add_template_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор периодичности"""
    frequency_text = update.message.text
    
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
        return ADD_TEMPLATE_FREQUENCY
    
    context.user_data['new_template']['frequency'] = frequency_map[frequency_text]
    
    # Показываем подтверждение
    template_data = context.user_data['new_template']
    info = format_template_info(template_data)
    
    await update.message.reply_text(
        f"✅ **Подтверждение создания шаблона**\n\n{info}\n"
        "Всё верно? Подтверждаем создание шаблона?",
        parse_mode='Markdown',
        reply_markup=get_confirmation_keyboard()
    )
    return ADD_TEMPLATE_CONFIRM

async def add_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания шаблона"""
    if update.message.text == "✅ Подтвердить создание":
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
    
    elif update.message.text == "✏️ Внести изменения":
        # Сохраняем данные шаблона для редактирования
        context.user_data['editing_template'] = context.user_data['new_template']
        context.user_data['editing_template_id'] = None  # Пока нет ID, так как шаблон еще не создан
        
        # Показываем меню редактирования полей
        info = format_template_info(context.user_data['editing_template'])
        
        await update.message.reply_text(
            f"✏️ **Редактирование шаблона**\n\n{info}\n"
            "**Выберите поле для редактирования:**",
            parse_mode='Markdown',
            reply_markup=get_edit_fields_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_confirmation_keyboard()
        )
        return ADD_TEMPLATE_CONFIRM

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
    return EDIT_TEMPLATE_SELECT

async def edit_template_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для редактирования"""
    user_text = update.message.text
    
    # Если пользователь выбрал шаблон (начинается с 📝)
    if user_text.startswith("📝"):
        return await edit_template_select_template(update, context)
    
    # Иначе это выбор группы
    group_name = user_text
    user_id = update.effective_user.id
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа не найдена",
            reply_markup=get_groups_keyboard(user_id, "edit")
        )
        return EDIT_TEMPLATE_SELECT
    
    context.user_data['edit_group'] = group_id
    context.user_data['edit_group_name'] = group_name
    
    # Получаем шаблоны этой группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе '{group_name}' нет шаблонов для редактирования",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Создаем клавиатуру с шаблонами
    keyboard = []
    for template_id, template in templates:
        keyboard.append([f"📝 {template['name']} (ID: {template_id})"])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"✏️ **Выберите шаблон для редактирования:**\n\n"
        f"Группа: {group_name}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return EDIT_TEMPLATE_SELECT

async def edit_template_select_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для редактирования"""
    template_text = update.message.text
    
    # Извлекаем ID шаблона из текста
    if "(ID:" in template_text:
        try:
            template_id = template_text.split("(ID:")[1].split(")")[0].strip()
        except:
            await update.message.reply_text(
                "❌ Ошибка при выборе шаблона",
                reply_markup=get_templates_main_keyboard()
            )
            return TEMPLATES_MAIN
    else:
        await update.message.reply_text(
            "❌ Ошибка при выборе шаблона",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Получаем данные шаблона
    template = get_template_by_id(template_id)
    if not template:
        await update.message.reply_text(
            "❌ Шаблон не найден",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Сохраняем данные для редактирования
    context.user_data['editing_template_id'] = template_id
    context.user_data['editing_template'] = template
    
    # Показываем информацию о шаблоне и кнопки выбора поля
    info = format_template_info(template)
    
    await update.message.reply_text(
        f"✏️ **Редактирование шаблона**\n\n{info}\n"
        "**Выберите поле для редактирования:**",
        parse_mode='Markdown',
        reply_markup=get_edit_fields_keyboard()
    )
    return EDIT_TEMPLATE_FIELD

def get_edit_fields_keyboard():
    """Клавиатура выбора поля для редактирования"""
    keyboard = [
        ["🏷️ Название", "📝 Текст"],
        ["🖼️ Изображение", "⏰ Время"],
        ["📅 Дни отправки", "🔄 Периодичность"],
        ["✅ Завершить редактирование", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def edit_template_choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора поля для редактирования"""
    field_text = update.message.text
    
    # Проверяем, что данные шаблона загружены
    if 'editing_template' not in context.user_data:
        await update.message.reply_text(
            "❌ Ошибка: данные шаблона не найдены. Начните редактирование заново.",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    template = context.user_data['editing_template']
    
    field_map = {
        "🏷️ Название": "name",
        "📝 Текст": "text",
        "🖼️ Изображение": "image",
        "⏰ Время": "time",
        "📅 Дни отправки": "days",
        "🔄 Периодичность": "frequency"
    }
    
    if field_text == "✅ Завершить редактирование":
        return await save_edited_template(update, context)
    
    elif field_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATES_MAIN
    
    elif field_text in field_map:
        field = field_map[field_text]
        context.user_data['editing_field'] = field
        
        if field == "name":
            await update.message.reply_text(
                f"✏️ Введите новое название шаблона:\n\nТекущее: {template.get('name', 'Не указано')}",
                reply_markup=get_back_keyboard()
            )
            return EDIT_TEMPLATE_NAME
            
        elif field == "text":
            await update.message.reply_text(
                f"✏️ Введите новый текст шаблона:\n\nТекущий: {template.get('text', 'Не указан')[:100]}...",
                reply_markup=get_back_keyboard()
            )
            return EDIT_TEMPLATE_TEXT
            
        elif field == "image":
            await update.message.reply_text(
                "✏️ Пришлите новое изображение или нажмите 'Пропустить' для удаления текущего:",
                reply_markup=get_skip_keyboard()
            )
            return EDIT_TEMPLATE_IMAGE
            
        elif field == "time":
            await update.message.reply_text(
                f"✏️ Введите новое время отправки (ЧЧ:ММ МСК):\n\nТекущее: {template.get('time', 'Не указано')}",
                reply_markup=get_back_keyboard()
            )
            return EDIT_TEMPLATE_TIME
            
        elif field == "days":
            # Сбрасываем выбранные дни для нового выбора
            context.user_data['selected_days'] = template.get('days', [])
            selected_days_text = [DAYS_OF_WEEK[d] for d in context.user_data['selected_days']]
            await update.message.reply_text(
                f"📅 **Выберите дни отправки:**\n\n"
                f"Текущие дни: {', '.join(selected_days_text) if selected_days_text else 'Не указаны'}\n\n"
                "Выберите дни из списка:",
                parse_mode='Markdown',
                reply_markup=get_days_keyboard(context.user_data['selected_days'])
            )
            return EDIT_TEMPLATE_DAYS
            
        elif field == "frequency":
            current_freq = template.get('frequency', 'weekly')
            freq_text = "📅 1 в неделю" if current_freq == "weekly" else "🗓️ 2 в месяц" if current_freq == "2_per_month" else "📆 1 в месяц"
            await update.message.reply_text(
                f"🔄 Выберите новую периодичность:\n\nТекущая: {freq_text}",
                reply_markup=get_frequency_keyboard()
            )
            return EDIT_TEMPLATE_FREQUENCY
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор поля",
            reply_markup=get_edit_fields_keyboard()
        )
        return EDIT_TEMPLATE_FIELD

async def save_edited_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение отредактированного шаблона"""
    template_id = context.user_data.get('editing_template_id')
    template_data = context.user_data['editing_template']
    
    if template_id:
        # Обновляем существующий шаблон
        success, message = update_template(template_id, template_data)
        
        if success:
            await update.message.reply_text(
                f"✅ Шаблон успешно обновлен!\n\n"
                f"ID шаблона: `{template_id}`",
                parse_mode='Markdown',
                reply_markup=get_templates_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Ошибка при обновлении шаблона: {message}",
                reply_markup=get_templates_main_keyboard()
            )
    else:
        # Создаем новый шаблон с отредактированными данными
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

async def edit_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование названия"""
    new_name = update.message.text.strip()
    
    if not new_name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_NAME
    
    # Обновляем данные в контексте
    context.user_data['editing_template']['name'] = new_name
    
    await update.message.reply_text(
        f"✅ Название обновлено: {new_name}",
        reply_markup=get_edit_fields_keyboard()
    )
    return EDIT_TEMPLATE_FIELD

async def edit_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование текста"""
    new_text = update.message.text.strip()
    
    if not new_text:
        await update.message.reply_text(
            "❌ Текст не может быть пустым. Введите текст:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_TEXT
    
    # Обновляем данные в контексте
    context.user_data['editing_template']['text'] = new_text
    
    await update.message.reply_text(
        "✅ Текст шаблона обновлен",
        reply_markup=get_edit_fields_keyboard()
    )
    return EDIT_TEMPLATE_FIELD

async def edit_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование изображения"""
    
    if update.message.text == "⏭️ Пропустить":
        # Удаляем изображение из шаблона
        context.user_data['editing_template']['image'] = None
        
        await update.message.reply_text(
            "✅ Изображение удалено из шаблона",
            reply_markup=get_edit_fields_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_content = await photo_file.download_as_bytearray()
        
        template_id = context.user_data.get('editing_template_id', 'new')
        image_path = save_image(photo_content, f"template_edit_{template_id}.jpg")
        
        if image_path:
            # Обновляем данные в контексте
            context.user_data['editing_template']['image'] = image_path
            
            await update.message.reply_text(
                "✅ Изображение обновлено!",
                reply_markup=get_edit_fields_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка сохранения изображения",
                reply_markup=get_edit_fields_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ Пришлите изображение или нажмите 'Пропустить':",
            reply_markup=get_skip_keyboard()
        )
        return EDIT_TEMPLATE_IMAGE
    
    return EDIT_TEMPLATE_FIELD

async def edit_template_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование времени"""
    new_time = update.message.text.strip()
    
    try:
        hours, minutes = map(int, new_time.split(':'))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            # Обновляем данные в контексте
            context.user_data['editing_template']['time'] = new_time
            
            await update.message.reply_text(
                f"✅ Время обновлено: {new_time}",
                reply_markup=get_edit_fields_keyboard()
            )
        else:
            raise ValueError
    except:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используйте ЧЧ:ММ:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_TIME
    
    return EDIT_TEMPLATE_FIELD

async def edit_template_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование дней отправки"""
    user_text = update.message.text
    
    if 'selected_days' not in context.user_data:
        context.user_data['selected_days'] = []
    
    selected_days = context.user_data['selected_days']
    
    # Обработка завершения выбора дней
    if user_text == "✅ Завершить выбор дней":
        if not selected_days:
            await update.message.reply_text(
                "❌ Нужно выбрать хотя бы один день",
                reply_markup=get_days_keyboard(selected_days)
            )
            return EDIT_TEMPLATE_DAYS
        
        # Обновляем данные в контексте
        context.user_data['editing_template']['days'] = selected_days
        
        selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
        await update.message.reply_text(
            f"✅ Дни отправки обновлены: {', '.join(selected_days_text)}",
            reply_markup=get_edit_fields_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
    # Обработка выбора дня
    day_number = None
    for num, text in DAYS_OF_WEEK.items():
        if text == user_text:
            day_number = num
            break
    
    if day_number is not None:
        if day_number not in selected_days:
            selected_days.append(day_number)
        
        selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
        await update.message.reply_text(
            f"✅ Выбраны дни: {', '.join(selected_days_text)}\n\n"
            "Выберите еще дни или завершите выбор:",
            reply_markup=get_days_keyboard(selected_days, is_additional=True)
        )
        return EDIT_TEMPLATE_DAYS
    
    await update.message.reply_text(
        "❌ Выберите день из списка:",
        reply_markup=get_days_keyboard(selected_days)
    )
    return EDIT_TEMPLATE_DAYS

async def edit_template_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование периодичности"""
    frequency_text = update.message.text
    
    frequency_map = {
        "📅 1 в неделю": "weekly",
        "🗓️ 2 в месяц": "2_per_month",
        "📆 1 в месяц": "monthly"
    }
    
    if frequency_text in frequency_map:
        new_frequency = frequency_map[frequency_text]
        # Обновляем данные в контексте
        context.user_data['editing_template']['frequency'] = new_frequency
        
        await update.message.reply_text(
            f"✅ Периодичность обновлена: {frequency_text}",
            reply_markup=get_edit_fields_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Выберите периодичность из списка:",
            reply_markup=get_frequency_keyboard()
        )
        return EDIT_TEMPLATE_FREQUENCY
    
    return EDIT_TEMPLATE_FIELD

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
    return DELETE_TEMPLATE_SELECT

async def delete_template_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для удаления"""
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
            reply_markup=get_groups_keyboard(user_id, "delete")
        )
        return DELETE_TEMPLATE_SELECT
    
    context.user_data['delete_group'] = group_id
    context.user_data['delete_group_name'] = group_name
    
    # Получаем шаблоны этой группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе '{group_name}' нет шаблонов для удаления",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Создаем клавиатуру с шаблонами
    keyboard = []
    for template_id, template in templates:
        keyboard.append([f"🗑️ {template['name']} (ID: {template_id})"])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"🗑️ **Выберите шаблон для удаления:**\n\n"
        f"Группа: {group_name}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DELETE_TEMPLATE_CONFIRM

async def delete_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления шаблона"""
    template_text = update.message.text
    
    if template_text == "🔙 Назад":
        await update.message.reply_text(
            "🔙 Возврат к выбору группы",
            reply_markup=get_groups_keyboard(update.effective_user.id, "delete")
        )
        return DELETE_TEMPLATE_SELECT
    
    # Извлекаем ID шаблона из текста
    if "(ID:" in template_text:
        try:
            template_id = template_text.split("(ID:")[1].split(")")[0].strip()
        except:
            await update.message.reply_text(
                "❌ Ошибка при выборе шаблона",
                reply_markup=get_templates_main_keyboard()
            )
            return TEMPLATES_MAIN
    else:
        await update.message.reply_text(
            "❌ Ошибка при выборе шаблона",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Получаем данные шаблона
    template = get_template_by_id(template_id)
    if not template:
        await update.message.reply_text(
            "❌ Шаблон не найден",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Сохраняем ID для удаления
    context.user_data['deleting_template_id'] = template_id
    context.user_data['deleting_template'] = template
    
    # Показываем подтверждение
    info = format_template_info(template)
    
    await update.message.reply_text(
        f"⚠️ **ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ**\n\n{info}\n"
        "❌ **ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ДАННЫЙ ШАБЛОН?**\n\n"
        "Это действие нельзя отменить!",
        parse_mode='Markdown',
        reply_markup=get_delete_confirmation_keyboard()
    )
    return DELETE_TEMPLATE_FINAL

def get_delete_confirmation_keyboard():
    """Клавиатура подтверждения удаления"""
    keyboard = [
        ["✅ Да, удалить шаблон"],
        ["❌ Нет, отменить удаление"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def delete_template_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальное подтверждение удаления"""
    user_choice = update.message.text
    template_id = context.user_data.get('deleting_template_id')
    template = context.user_data.get('deleting_template')
    
    if user_choice == "✅ Да, удалить шаблон":
        if template_id and template:
            success, message = delete_template_by_id(template_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Шаблон '{template['name']}' успешно удален!",
                    reply_markup=get_templates_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при удалении: {message}",
                    reply_markup=get_templates_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "❌ Ошибка: данные шаблона не найдены",
                reply_markup=get_templates_main_keyboard()
            )
    
    elif user_choice == "❌ Нет, отменить удаление":
        await update.message.reply_text(
            "✅ Удаление отменено",
            reply_markup=get_templates_main_keyboard()
        )
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_delete_confirmation_keyboard()
        )
        return DELETE_TEMPLATE_FINAL
    
    # Очищаем временные данные
    context.user_data.clear()
    return TEMPLATES_MAIN

# ===== ФУНКЦИЯ ОТМЕНЫ =====

async def cancel_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена и возврат в главное меню"""
    # Очищаем временные данные
    context.user_data.clear()
    
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🔙 Возврат в главное меню",
        reply_markup=get_main_keyboard(user_id)  # Добавили user_id
    )
    return ConversationHandler.END

# ===== БАЗОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ШАБЛОНАМИ =====

async def create_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания шаблона"""
    user_id = update.effective_user.id
    auth_manager.update_user_role_if_needed(user_id)
    
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе для создания шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATE_MAIN
    
    await update.message.reply_text(
        "➕ **Создание нового шаблона**\n\n"
        "Выберите группу для шаблона:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "create")
    )
    return CREATE_TEMPLATE_GROUP

async def create_template_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для шаблона"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    if user_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATE_MAIN
    
    # Определяем выбранную группу
    accessible_groups = get_user_accessible_groups(user_id)
    selected_group_id = None
    selected_group_name = None
    
    for group_id, group_data in accessible_groups.items():
        if group_data['name'] == user_text:
            selected_group_id = group_id
            selected_group_name = group_data['name']
            break
    
    if not selected_group_id:
        await update.message.reply_text(
            "❌ Группа не найдена. Выберите группу из списка:",
            reply_markup=get_groups_keyboard(user_id, "create")
        )
        return CREATE_TEMPLATE_GROUP
    
    context.user_data['template_creation'] = {
        'group': selected_group_id,
        'group_name': selected_group_name,
        'created_by': user_id
    }
    
    await update.message.reply_text(
        "🏷️ **Введите название для шаблона:**",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return CREATE_TEMPLATE_NAME

async def create_template_enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия шаблона"""
    template_name = update.message.text.strip()
    
    if template_name == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы:",
            reply_markup=get_groups_keyboard(user_id, "create")
        )
        return CREATE_TEMPLATE_GROUP
    
    if not template_name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название шаблона:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_NAME
    
    context.user_data['template_creation']['name'] = template_name
    
    await update.message.reply_text(
        "📝 **Введите текст шаблона:**\n\n"
        "Этот текст будет отправляться как сообщение.",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return CREATE_TEMPLATE_TEXT

async def create_template_enter_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод текста шаблона"""
    template_text = update.message.text
    
    if template_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к вводу названия:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_NAME
    
    if not template_text.strip():
        await update.message.reply_text(
            "❌ Текст шаблона не может быть пустым. Введите текст:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_TEXT
    
    context.user_data['template_creation']['text'] = template_text
    
    await update.message.reply_text(
        "🖼️ **Хотите добавить изображение к шаблону?**\n\n"
        "Отправьте фото или выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_image_choice_keyboard()
    )
    return CREATE_TEMPLATE_IMAGE

async def create_template_handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображения шаблона"""
    if update.message.photo:
        # Сохраняем изображение
        photo_file = await update.message.photo[-1].get_file()
        image_data = await photo_file.download_as_bytearray()
        
        # Создаем временный ID для сохранения изображения
        temp_template_id = "temp_" + str(update.effective_user.id)
        image_path = save_image(type('obj', (object,), {
            'filename': 'image.jpg',
            'getvalue': lambda: image_data
        })(), temp_template_id)
        
        if image_path:
            context.user_data['template_creation']['image'] = image_path
            await update.message.reply_text(
                "✅ Изображение добавлено!",
                reply_markup=get_back_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при сохранении изображения",
                reply_markup=get_back_keyboard()
            )
    
    await update.message.reply_text(
        "⏰ **Введите время отправки (формат: ЧЧ:ММ, например 14:30):**\n\n"
        "Или нажмите '⏭️ Пропустить' чтобы не указывать время",
        parse_mode='Markdown',
        reply_markup=get_time_input_keyboard()
    )
    return CREATE_TEMPLATE_TIME

async def create_template_skip_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск добавления изображения"""
    context.user_data['template_creation']['image'] = None
    
    await update.message.reply_text(
        "⏰ **Введите время отправки (формат: ЧЧ:ММ, например 14:30):**\n\n"
        "Или нажмите '⏭️ Пропустить' чтобы не указывать время",
        parse_mode='Markdown',
        reply_markup=get_time_input_keyboard()
    )
    return CREATE_TEMPLATE_TIME

async def create_template_enter_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод времени отправки"""
    time_text = update.message.text
    
    if time_text == "⏭️ Пропустить":
        context.user_data['template_creation']['time'] = None
    elif time_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к добавлению изображения:",
            reply_markup=get_image_choice_keyboard()
        )
        return CREATE_TEMPLATE_IMAGE
    else:
        # Проверяем формат времени
        try:
            hour, minute = map(int, time_text.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            context.user_data['template_creation']['time'] = time_text
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат времени. Используйте ЧЧ:ММ (например 14:30):",
                reply_markup=get_time_input_keyboard()
            )
            return CREATE_TEMPLATE_TIME
    
    context.user_data['template_creation']['days'] = []
    
    await update.message.reply_text(
        "📅 **Выберите дни отправки:**\n\n"
        "Нажимайте на дни недели для выбора/отмены выбора.\n"
        "Когда закончите, нажмите '✅ Завершить выбор'",
        parse_mode='Markdown',
        reply_markup=get_days_keyboard()
    )
    return CREATE_TEMPLATE_DAYS

async def create_template_choose_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор дней отправки"""
    day_text = update.message.text
    days_mapping = {
        'Понедельник': '0',
        'Вторник': '1', 
        'Среда': '2',
        'Четверг': '3',
        'Пятница': '4',
        'Суббота': '5',
        'Воскресенье': '6'
    }
    
    if day_text in days_mapping:
        day_code = days_mapping[day_text]
        current_days = context.user_data['template_creation'].get('days', [])
        
        if day_code in current_days:
            current_days.remove(day_code)
            await update.message.reply_text(f"❌ {day_text} удален из выбора")
        else:
            current_days.append(day_code)
            await update.message.reply_text(f"✅ {day_text} добавлен")
        
        context.user_data['template_creation']['days'] = current_days
        
        # Показываем текущий выбор
        selected_days = [day for day, code in days_mapping.items() if code in current_days]
        if selected_days:
            await update.message.reply_text(
                f"📅 Выбрано: {', '.join(selected_days)}",
                reply_markup=get_days_keyboard()
            )
        else:
            await update.message.reply_text(
                "📅 Дни не выбраны",
                reply_markup=get_days_keyboard()
            )
        
        return CREATE_TEMPLATE_DAYS
    
    await update.message.reply_text(
        "❌ Выберите день из списка:",
        reply_markup=get_days_keyboard()
    )
    return CREATE_TEMPLATE_DAYS

async def create_template_finish_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение выбора дней"""
    await update.message.reply_text(
        "🔄 **Выберите периодичность отправки:**",
        parse_mode='Markdown',
        reply_markup=get_frequency_keyboard()
    )
    return CREATE_TEMPLATE_FREQUENCY

async def create_template_choose_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор периодичности"""
    frequency_text = update.message.text
    
    frequency_mapping = {
        "1 в неделю": "weekly",
        "2 в месяц": "2_per_month", 
        "1 в месяц": "monthly"
    }
    
    if frequency_text in frequency_mapping:
        context.user_data['template_creation']['frequency'] = frequency_mapping[frequency_text]
    elif frequency_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору дней:",
            reply_markup=get_days_keyboard()
        )
        return CREATE_TEMPLATE_DAYS
    else:
        await update.message.reply_text(
            "❌ Выберите периодичность из списка:",
            reply_markup=get_frequency_keyboard()
        )
        return CREATE_TEMPLATE_FREQUENCY
    
    # Показываем подтверждение
    template_data = context.user_data['template_creation']
    preview = format_template_preview(template_data)
    
    await update.message.reply_text(
        f"✅ **ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ШАБЛОНА**\n\n{preview}\n\n"
        "Всё верно?",
        parse_mode='Markdown',
        reply_markup=get_template_confirmation_keyboard()
    )
    return CREATE_TEMPLATE_CONFIRM

async def create_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания шаблона"""
    choice = update.message.text
    
    if choice == "✅ Подтвердить":
        template_data = context.user_data['template_creation']
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
        
        context.user_data.clear()
        return TEMPLATE_MAIN
    
    elif choice == "✏️ Изменить":
        await update.message.reply_text(
            "🔧 **Что вы хотите изменить?**",
            reply_markup=get_template_edit_keyboard()
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

async def create_template_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор редактирования шаблона"""
    choice = update.message.text
    
    if choice == "🔙 Назад":
        template_data = context.user_data['template_creation']
        preview = format_template_preview(template_data)
        
        await update.message.reply_text(
            f"✅ **ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ШАБЛОНА**\n\n{preview}\n\n"
            "Всё верно?",
            parse_mode='Markdown',
            reply_markup=get_template_confirmation_keyboard()
        )
        return CREATE_TEMPLATE_CONFIRM
    
    # Здесь можно добавить логику для разных типов редактирования
    await update.message.reply_text(
        "⚠️ Редактирование на этапе создания пока не реализовано\n\n"
        "Вернитесь к подтверждению или начните заново",
        reply_markup=get_template_edit_keyboard()
    )
    return CREATE_TEMPLATE_CONFIRM

async def template_list_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало просмотра списка шаблонов"""
    await update.message.reply_text(
        "📋 **Просмотр шаблонов**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_template_list_keyboard()
    )
    return TEMPLATE_LIST

async def delete_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления шаблона"""
    await update.message.reply_text(
        "🗑️ **Удаление шаблона**\n\n"
        "Эта функция находится в разработке",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATE_MAIN

async def cancel_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена работы с шаблонами"""
    context.user_data.clear()
    user_id = update.effective_user.id
    await update.message.reply_text(
        "🔙 Возврат в главное меню",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END

# Добавьте заглушки для остальных функций, которые могут потребоваться
async def template_list_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик списка шаблонов"""
    await update.message.reply_text(
        "📋 **Список шаблонов**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_template_list_keyboard()
    )
    return TEMPLATE_LIST

async def template_list_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для просмотра шаблонов"""
    await update.message.reply_text(
        "🏷️ **Выбор группы**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_template_list_keyboard()
    )
    return TEMPLATE_LIST_CHOOSE_GROUP

async def template_details_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик деталей шаблона"""
    await update.message.reply_text(
        "📝 **Детали шаблона**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_template_details_keyboard()
    )
    return TEMPLATE_DETAILS

async def delete_template_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для удаления"""
    await update.message.reply_text(
        "🗑️ **Выбор шаблона для удаления**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_back_keyboard()
    )
    return DELETE_TEMPLATE_SELECT

async def delete_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления шаблона"""
    await update.message.reply_text(
        "✅ **Подтверждение удаления**\n\n"
        "Эта функция находится в разработке",
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATE_MAIN

async def edit_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования шаблона"""
    await update.message.reply_text(
        "✏️ **Редактирование шаблона**\n\n"
        "Эта функция находится в разработке",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATE_MAIN

async def create_template_ask_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрос изображения"""
    await update.message.reply_text(
        "🖼️ **Отправьте изображение для шаблона:**",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return CREATE_TEMPLATE_IMAGE

async def create_template_skip_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск ввода времени"""
    context.user_data['template_creation']['time'] = None
    context.user_data['template_creation']['days'] = []
    
    await update.message.reply_text(
        "📅 **Выберите дни отправки:**\n\n"
        "Нажимайте на дни недели для выбора/отмены выбора.\n"
        "Когда закончите, нажмите '✅ Завершить выбор'",
        parse_mode='Markdown',
        reply_markup=get_days_keyboard()
    )
    return CREATE_TEMPLATE_DAYS
    
# ===== CONVERSATION HANDLER =====

def get_template_conversation_handler():
    """Возвращает настроенный ConversationHandler для шаблонов"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Шаблоны$"), templates_main)],
        states={
            TEMPLATES_MAIN: [  # ИСПРАВЛЕНО: было TEMPLATES_MAIN
                MessageHandler(filters.Regex("^➕ Создать шаблон$"), create_template_start),
                MessageHandler(filters.Regex("^📋 Список шаблонов$"), template_list_start),
                MessageHandler(filters.Regex("^✏️ Редактировать шаблон$"), edit_template_start),
                MessageHandler(filters.Regex("^🗑️ Удалить шаблон$"), delete_template_start),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), cancel_template)
            ],
            
            CREATE_TEMPLATE_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_choose_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            
            CREATE_TEMPLATE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_enter_name),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_start)
            ],
            
            CREATE_TEMPLATE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_enter_text),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_enter_name)
            ],
            
            CREATE_TEMPLATE_IMAGE: [
                MessageHandler(filters.PHOTO, create_template_handle_image),
                MessageHandler(filters.Regex("^🖼️ Добавить изображение$"), create_template_ask_image),
                MessageHandler(filters.Regex("^⏭️ Пропустить$"), create_template_skip_image),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_enter_text)
            ],
            
            CREATE_TEMPLATE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_enter_time),
                MessageHandler(filters.Regex("^⏭️ Пропустить$"), create_template_skip_time),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_handle_image)
            ],
            
            CREATE_TEMPLATE_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_choose_days),
                MessageHandler(filters.Regex("^✅ Завершить выбор$"), create_template_finish_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_enter_time)
            ],
            
            CREATE_TEMPLATE_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_choose_frequency),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_finish_days)
            ],
            
            CREATE_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_confirm),
                MessageHandler(filters.Regex("^✅ Подтвердить$"), create_template_confirm),
                MessageHandler(filters.Regex("^✏️ Изменить$"), create_template_edit_choice),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_choose_frequency)
            ],
            
            TEMPLATE_LIST: [  # ИСПРАВЛЕНО: было TEMPLATES_LIST если есть
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_handle),
                MessageHandler(filters.Regex("^🔙 К шаблонам$"), templates_main)
            ],
            
            TEMPLATE_LIST_CHOOSE_GROUP: [  # ИСПРАВЛЕНО: было TEMPLATES_LIST_CHOOSE_GROUP если есть
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_choose_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), template_list_start)
            ],
            
            TEMPLATE_DETAILS: [  # ИСПРАВЛЕНО: было TEMPLATES_DETAILS если есть
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_details_handle),
                MessageHandler(filters.Regex("^🔙 К списку$"), template_list_start)
            ],
            
            DELETE_TEMPLATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_select),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            
            DELETE_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_confirm),
                MessageHandler(filters.Regex("^✅ Да, удалить$"), delete_template_confirm),
                MessageHandler(filters.Regex("^❌ Нет, отменить$"), delete_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), delete_template_select)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_template)]
    )