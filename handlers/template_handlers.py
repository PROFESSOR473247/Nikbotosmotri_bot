from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.template_keyboards import (
    get_templates_main_keyboard, get_groups_keyboard, get_subgroups_keyboard,
    get_back_keyboard, get_skip_keyboard, get_days_keyboard, 
    get_days_continue_keyboard, get_frequency_keyboard, get_confirmation_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from authorized_users import is_authorized
from template_manager import (
    get_user_accessible_groups, create_template, get_templates_by_group,
    save_image, format_template_info, DAYS_OF_WEEK, FREQUENCY_TYPES, load_groups,
    get_template_by_id, update_template_field, delete_template_by_id
)

# Состояния для ConversationHandler
(
    TEMPLATES_MAIN, TEMPLATE_LIST_GROUPS, TEMPLATE_LIST_SUBGROUPS, TEMPLATE_LIST_TEMPLATES,
    ADD_TEMPLATE_GROUP, ADD_TEMPLATE_SUBGROUP, ADD_TEMPLATE_NAME, ADD_TEMPLATE_TEXT,
    ADD_TEMPLATE_IMAGE, ADD_TEMPLATE_TIME, ADD_TEMPLATE_DAYS, ADD_TEMPLATE_FREQUENCY,
    ADD_TEMPLATE_SECOND_DAY, ADD_TEMPLATE_CONFIRM,
    # Добавленные состояния для редактирования и удаления
    EDIT_TEMPLATE_SELECT, EDIT_TEMPLATE_FIELD, EDIT_TEMPLATE_GROUP, EDIT_TEMPLATE_SUBGROUP,
    EDIT_TEMPLATE_NAME, EDIT_TEMPLATE_TEXT, EDIT_TEMPLATE_IMAGE, EDIT_TEMPLATE_TIME,
    EDIT_TEMPLATE_DAYS, EDIT_TEMPLATE_FREQUENCY, EDIT_TEMPLATE_CONFIRM,
    DELETE_TEMPLATE_SELECT, DELETE_TEMPLATE_CONFIRM
) = range(27)

# ===== ОСНОВНЫЕ ФУНКЦИИ ШАБЛОНОВ =====

async def templates_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню шаблонов"""
    await update.message.reply_text(
        "🎯 **Управление шаблонами**\n\n"
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
    
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе '{group_name}' пока нет шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    message_text = f"📋 **Шаблоны в {group_name}:**\n\n"
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
        'created_by': user_id
    }
    
    await update.message.reply_text(
        "➕ **Создание нового шаблона**\n\n"
        "Шаг 1 из 10: Выберите группу:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "add")
    )
    return ADD_TEMPLATE_GROUP

async def add_template_choose_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для нового шаблона"""
    group_name = update.message.text
    user_id = update.effective_user.id
    
    print(f"🔍 Пользователь {user_id} выбрал группу: {group_name}")
    
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
    
    print(f"✅ Найдена группа: {group_id}")
    
    context.user_data['new_template']['group'] = group_id
    context.user_data['current_group'] = group_id
    
    # Проверяем есть ли подгруппы
    groups_data = load_groups()
    group_data = groups_data['groups'].get(group_id, {})
    subgroups = group_data.get('subgroups', {})
    
    print(f"🔍 Подгруппы в группе {group_id}: {subgroups}")
    
    if subgroups:
        await update.message.reply_text(
            "Шаг 2 из 10: Выберите подгруппу:",
            reply_markup=get_subgroups_keyboard(group_id, "add")
        )
        return ADD_TEMPLATE_SUBGROUP
    else:
        context.user_data['new_template']['subgroup'] = None
        await update.message.reply_text(
            "Шаг 3 из 10: Введите название шаблона:",
            reply_markup=get_back_keyboard()
        )
        return ADD_TEMPLATE_NAME

async def add_template_choose_subgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор подгруппы для нового шаблона"""
    subgroup_text = update.message.text
    group_id = context.user_data.get('current_group')
    
    # Получаем данные группы
    groups_data = load_groups()
    group_data = groups_data['groups'].get(group_id, {})
    subgroups = group_data.get('subgroups', {})
    
    # Определяем ID подгруппы по тексту
    subgroup_id = None
    if subgroup_text == "📁 Без подгруппы":
        subgroup_id = None
    else:
        # Ищем подгруппу по отображаемому имени
        for sid, sname in subgroups.items():
            if sname == subgroup_text:
                subgroup_id = sid
                break
    
    # Сохраняем подгруппу
    context.user_data['new_template']['subgroup'] = subgroup_id
    
    await update.message.reply_text(
        "Шаг 3 из 10: Введите название шаблона:",
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
        "Шаг 4 из 10: Введите текст шаблона:",
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
        "Шаг 5 из 10: Пришлите изображение для шаблона или нажмите 'Пропустить':",
        reply_markup=get_skip_keyboard()
    )
    return ADD_TEMPLATE_IMAGE

async def add_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображения для шаблона"""
    if update.message.text == "⏭️ Пропустить":
        context.user_data['new_template']['image'] = None
        await update.message.reply_text(
            "Шаг 6 из 10: Введите время отправки в формате ЧЧ:ММ (МСК):",
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
                "Шаг 6 из 10: Введите время отправки в формате ЧЧ:ММ (МСК):",
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
    """Ввод времени отправки - Шаг 6"""
    time_str = update.message.text.strip()
    
    try:
        hours, minutes = map(int, time_str.split(':'))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            context.user_data['new_template']['time'] = time_str
            
            # Инициализируем список дней если его нет
            if 'days' not in context.user_data['new_template']:
                context.user_data['new_template']['days'] = []
            
            await update.message.reply_text(
                "📅 **Шаг 7: Выберите день отправки:**\n\n"
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
    """Обработка выбора дней - Шаги 7-8"""
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
    
    # Обработка кнопки "➕ Выбрать еще день" (из шага 8)
    if user_text == "➕ Выбрать еще день":
        await update.message.reply_text(
            "📅 **Выберите ДОПОЛНИТЕЛЬНЫЙ день отправки:**\n\n"
            f"Уже выбрано: {', '.join([DAYS_OF_WEEK[d] for d in selected_days])}",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(selected_days, is_additional=True)
        )
        return ADD_TEMPLATE_DAYS
    
    # Обработка кнопки "➡️ Перейти к следующему шагу" (из шага 8)
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
        # Первый день выбран - переходим к шагу 8
        await update.message.reply_text(
            f"✅ **Первый день выбран:** {selected_days_text[0]}\n\n"
            "📅 **Шаг 8: Хотите добавить еще дни?**\n\n"
            "Вы можете добавить дополнительные дни отправки или перейти к следующему шагу",
            parse_mode='Markdown',
            reply_markup=get_days_continue_keyboard(selected_days_text)
        )
        return ADD_TEMPLATE_DAYS
    else:
        # Уже есть выбранные дни - показываем обновленный список
        await update.message.reply_text(
            f"✅ **Выбраны дни:** {', '.join(selected_days_text)}\n\n"
            "📅 **Шаг 8: Хотите добавить еще дни?**\n\n"
            "Вы можете добавить дополнительные дни отправки или перейти к следующему шагу",
            parse_mode='Markdown',
            reply_markup=get_days_continue_keyboard(selected_days_text)
        )
        return ADD_TEMPLATE_DAYS

async def proceed_to_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к выбору периодичности - Шаг 9"""
    template_data = context.user_data['new_template']
    selected_days = template_data.get('days', [])
    selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
    
    await update.message.reply_text(
        f"📅 **Шаг 9: Выберите периодичность**\n\n"
        f"✅ Выбраны дни: {', '.join(selected_days_text)}",
        parse_mode='Markdown',
        reply_markup=get_frequency_keyboard()
    )
    return ADD_TEMPLATE_FREQUENCY

async def add_template_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор периодичности - Шаг 9"""
    frequency_text = update.message.text
    
    frequency_map = {
        "🔄 2 в неделю": "2_per_week",
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
    
    # Показываем подтверждение - Шаг 10
    template_data = context.user_data['new_template']
    info = format_template_info(template_data)
    
    await update.message.reply_text(
        f"✅ **Шаг 10: Подтверждение создания шаблона**\n\n{info}\n"
        "Всё верно? Подтверждаем создание шаблона?",
        parse_mode='Markdown',
        reply_markup=get_confirmation_keyboard()
    )
    return ADD_TEMPLATE_CONFIRM

async def add_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение создания шаблона - Шаг 10"""
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
        await update.message.reply_text(
            "⚠️ Функция редактирования в разработке\n\n"
            "Пока что вы можете отменить создание и начать заново",
            reply_markup=get_confirmation_keyboard()
        )
        return ADD_TEMPLATE_CONFIRM
    
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
    return EDIT_TEMPLATE_FIELD

async def edit_template_select_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона и поля для редактирования"""
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
    template_id = context.user_data['editing_template_id']
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
        await update.message.reply_text(
            "✅ Редактирование завершено!",
            reply_markup=get_templates_main_keyboard()
        )
        context.user_data.clear()
        return TEMPLATES_MAIN
    
    elif field_text in field_map:
        field = field_map[field_text]
        context.user_data['editing_field'] = field
        
        if field == "name":
            await update.message.reply_text(
                "✏️ Введите новое название шаблона:",
                reply_markup=get_back_keyboard()
            )
            return EDIT_TEMPLATE_NAME
            
        elif field == "text":
            await update.message.reply_text(
                "✏️ Введите новый текст шаблона:",
                reply_markup=get_back_keyboard()
            )
            return EDIT_TEMPLATE_TEXT
            
        elif field == "image":
            await update.message.reply_text(
                "✏️ Пришлите новое изображение или нажмите 'Пропустить':",
                reply_markup=get_skip_keyboard()
            )
            return EDIT_TEMPLATE_IMAGE
            
        elif field == "time":
            await update.message.reply_text(
                "✏️ Введите новое время отправки (ЧЧ:ММ МСК):",
                reply_markup=get_back_keyboard()
            )
            return EDIT_TEMPLATE_TIME
            
        elif field == "days":
            # Сбрасываем выбранные дни для нового выбора
            context.user_data['selected_days'] = []
            await update.message.reply_text(
                "📅 **Выберите дни отправки:**\n\n"
                "Выберите первый день из списка:",
                parse_mode='Markdown',
                reply_markup=get_days_keyboard()
            )
            return EDIT_TEMPLATE_DAYS
            
        elif field == "frequency":
            await update.message.reply_text(
                "🔄 Выберите новую периодичность:",
                reply_markup=get_frequency_keyboard()
            )
            return EDIT_TEMPLATE_FREQUENCY
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор поля",
            reply_markup=get_edit_fields_keyboard()
        )
        return EDIT_TEMPLATE_FIELD

# Функции редактирования конкретных полей

async def edit_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование названия"""
    new_name = update.message.text.strip()
    template_id = context.user_data['editing_template_id']
    
    if not new_name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_NAME
    
    success, message = update_template_field(template_id, "name", new_name)
    
    if success:
        await update.message.reply_text(
            f"✅ Название обновлено: {new_name}",
            reply_markup=get_edit_fields_keyboard()
        )
        # Обновляем данные в контексте
        context.user_data['editing_template']['name'] = new_name
    else:
        await update.message.reply_text(
            f"❌ Ошибка: {message}",
            reply_markup=get_edit_fields_keyboard()
        )
    
    return EDIT_TEMPLATE_FIELD

async def edit_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование текста"""
    new_text = update.message.text.strip()
    template_id = context.user_data['editing_template_id']
    
    if not new_text:
        await update.message.reply_text(
            "❌ Текст не может быть пустым. Введите текст:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_TEXT
    
    success, message = update_template_field(template_id, "text", new_text)
    
    if success:
        await update.message.reply_text(
            "✅ Текст шаблона обновлен",
            reply_markup=get_edit_fields_keyboard()
        )
        context.user_data['editing_template']['text'] = new_text
    else:
        await update.message.reply_text(
            f"❌ Ошибка: {message}",
            reply_markup=get_edit_fields_keyboard()
        )
    
    return EDIT_TEMPLATE_FIELD

async def edit_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование изображения"""
    template_id = context.user_data['editing_template_id']
    
    if update.message.text == "⏭️ Пропустить":
        success, message = update_template_field(template_id, "image", None)
        
        if success:
            await update.message.reply_text(
                "✅ Изображение удалено из шаблона",
                reply_markup=get_edit_fields_keyboard()
            )
            context.user_data['editing_template']['image'] = None
        else:
            await update.message.reply_text(
                f"❌ Ошибка: {message}",
                reply_markup=get_edit_fields_keyboard()
            )
        
        return EDIT_TEMPLATE_FIELD
    
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_content = await photo_file.download_as_bytearray()
        
        image_path = save_image(photo_content, f"template_edit_{template_id}.jpg")
        
        if image_path:
            success, message = update_template_field(template_id, "image", image_path)
            
            if success:
                await update.message.reply_text(
                    "✅ Изображение обновлено!",
                    reply_markup=get_edit_fields_keyboard()
                )
                context.user_data['editing_template']['image'] = image_path
            else:
                await update.message.reply_text(
                    f"❌ Ошибка: {message}",
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
    template_id = context.user_data['editing_template_id']
    
    try:
        hours, minutes = map(int, new_time.split(':'))
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            success, message = update_template_field(template_id, "time", new_time)
            
            if success:
                await update.message.reply_text(
                    f"✅ Время обновлено: {new_time}",
                    reply_markup=get_edit_fields_keyboard()
                )
                context.user_data['editing_template']['time'] = new_time
            else:
                await update.message.reply_text(
                    f"❌ Ошибка: {message}",
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
    template_id = context.user_data['editing_template_id']
    
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
        
        success, message = update_template_field(template_id, "days", selected_days)
        
        if success:
            selected_days_text = [DAYS_OF_WEEK[d] for d in selected_days]
            await update.message.reply_text(
                f"✅ Дни отправки обновлены: {', '.join(selected_days_text)}",
                reply_markup=get_edit_fields_keyboard()
            )
            context.user_data['editing_template']['days'] = selected_days
        else:
            await update.message.reply_text(
                f"❌ Ошибка: {message}",
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
    template_id = context.user_data['editing_template_id']
    
    frequency_map = {
        "🔄 2 в неделю": "2_per_week",
        "📅 1 в неделю": "weekly", 
        "🗓️ 2 в месяц": "2_per_month",
        "📆 1 в месяц": "monthly"
    }
    
    if frequency_text in frequency_map:
        new_frequency = frequency_map[frequency_text]
        success, message = update_template_field(template_id, "frequency", new_frequency)
        
        if success:
            await update.message.reply_text(
                f"✅ Периодичность обновлена: {frequency_text}",
                reply_markup=get_edit_fields_keyboard()
            )
            context.user_data['editing_template']['frequency'] = new_frequency
        else:
            await update.message.reply_text(
                f"❌ Ошибка: {message}",
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
    return DELETE_TEMPLATE_CONFIRM

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
        return DELETE_TEMPLATE_CONFIRM
    
    # Очищаем временные данные
    context.user_data.clear()
    return TEMPLATES_MAIN

# ===== ФУНКЦИЯ ОТМЕНЫ =====

async def cancel_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания шаблона"""
    # Очищаем временные данные
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Создание шаблона отменено",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# ===== CONVERSATION HANDLER =====

def get_template_conversation_handler():
    """Возвращает настроенный ConversationHandler для шаблонов"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Шаблоны$"), templates_main)],
        states={
            TEMPLATES_MAIN: [
                MessageHandler(filters.Regex("^📋 Список шаблонов$"), template_list_start),
                MessageHandler(filters.Regex("^➕ Добавить новый$"), add_template_start),
                MessageHandler(filters.Regex("^✏️ Редактировать$"), edit_template_start),
                MessageHandler(filters.Regex("^🗑️ Удалить$"), delete_template_start),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), lambda u, c: ConversationHandler.END)
            ],
            
            # === СПИСОК ШАБЛОНОВ ===
            TEMPLATE_LIST_GROUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_choose_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), template_list_choose_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), template_list_choose_group),
                MessageHandler(filters.Regex("^🔙 К шаблонам$"), templates_main)
            ],
            
            # === СОЗДАНИЕ ШАБЛОНОВ ===
            ADD_TEMPLATE_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_choose_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), add_template_choose_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), add_template_choose_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            ADD_TEMPLATE_SUBGROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_choose_subgroup),
                MessageHandler(filters.Regex("^🔍 Осмотры$"), add_template_choose_subgroup),
                MessageHandler(filters.Regex("^⏰ Напоминания$"), add_template_choose_subgroup),
                MessageHandler(filters.Regex("^💳 Оплаты$"), add_template_choose_subgroup),
                MessageHandler(filters.Regex("^🧼 Чистка$"), add_template_choose_subgroup),
                MessageHandler(filters.Regex("^📁 Без подгруппы$"), add_template_choose_subgroup),
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_days),
                MessageHandler(filters.Regex("^📅 Понедельник$"), add_template_days),
                MessageHandler(filters.Regex("^📅 Вторник$"), add_template_days),
                MessageHandler(filters.Regex("^📅 Среда$"), add_template_days),
                MessageHandler(filters.Regex("^📅 Четверг$"), add_template_days),
                MessageHandler(filters.Regex("^📅 Пятница$"), add_template_days),
                MessageHandler(filters.Regex("^📅 Суббота$"), add_template_days),
                MessageHandler(filters.Regex("^📅 Воскресенье$"), add_template_days),
                MessageHandler(filters.Regex("^➕ Выбрать еще день$"), add_template_days),
                MessageHandler(filters.Regex("^➡️ Перейти к следующему шагу$"), add_template_days),
                MessageHandler(filters.Regex("^✅ Завершить выбор дней$"), add_template_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_time)
            ],
            ADD_TEMPLATE_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_frequency),
                MessageHandler(filters.Regex("^🔄 2 в неделю$"), add_template_frequency),
                MessageHandler(filters.Regex("^📅 1 в неделю$"), add_template_frequency),
                MessageHandler(filters.Regex("^🗓️ 2 в месяц$"), add_template_frequency),
                MessageHandler(filters.Regex("^📆 1 в месяц$"), add_template_frequency),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_days)
            ],
            ADD_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_template_confirm),
                MessageHandler(filters.Regex("^✅ Подтвердить создание$"), add_template_confirm),
                MessageHandler(filters.Regex("^✏️ Внести изменения$"), add_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), add_template_frequency)
            ],
            
            # === РЕДАКТИРОВАНИЕ ШАБЛОНОВ ===
            EDIT_TEMPLATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_select_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), edit_template_select_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), edit_template_select_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            EDIT_TEMPLATE_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_choose_field),
                MessageHandler(filters.Regex("^🏷️ Название$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^📝 Текст$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^🖼️ Изображение$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^⏰ Время$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^📅 Дни отправки$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^🔄 Периодичность$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^✅ Завершить редактирование$"), edit_template_choose_field),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_start)
            ],
            EDIT_TEMPLATE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_name),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            EDIT_TEMPLATE_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_text),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            EDIT_TEMPLATE_IMAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_image),
                MessageHandler(filters.PHOTO, edit_template_image),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            EDIT_TEMPLATE_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_time),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            EDIT_TEMPLATE_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_days),
                MessageHandler(filters.Regex("^📅 Понедельник$"), edit_template_days),
                MessageHandler(filters.Regex("^📅 Вторник$"), edit_template_days),
                MessageHandler(filters.Regex("^📅 Среда$"), edit_template_days),
                MessageHandler(filters.Regex("^📅 Четверг$"), edit_template_days),
                MessageHandler(filters.Regex("^📅 Пятница$"), edit_template_days),
                MessageHandler(filters.Regex("^📅 Суббота$"), edit_template_days),
                MessageHandler(filters.Regex("^📅 Воскресенье$"), edit_template_days),
                MessageHandler(filters.Regex("^✅ Завершить выбор дней$"), edit_template_days),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            EDIT_TEMPLATE_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_frequency),
                MessageHandler(filters.Regex("^🔄 2 в неделю$"), edit_template_frequency),
                MessageHandler(filters.Regex("^📅 1 в неделю$"), edit_template_frequency),
                MessageHandler(filters.Regex("^🗓️ 2 в месяц$"), edit_template_frequency),
                MessageHandler(filters.Regex("^📆 1 в месяц$"), edit_template_frequency),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            
            # === УДАЛЕНИЕ ШАБЛОНОВ ===
DELETE_TEMPLATE_SELECT: [
    MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_select_group),
    MessageHandler(filters.Regex("^🚗 Hongqi$"), delete_template_select_group),
    MessageHandler(filters.Regex("^🚙 TurboMatiz$"), delete_template_select_group),
    MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
],
DELETE_TEMPLATE_CONFIRM: [
    MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_confirm),
    MessageHandler(filters.Regex("^🗑️ .* \\(ID: .*\\)$"), delete_template_confirm),
    MessageHandler(filters.Regex("^🔙 Назад$"), delete_template_start)
],
DELETE_TEMPLATE_FINAL: [  # ← ИЗМЕНИТЕ НАЗВАНИЕ НА FINAL
    MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_final),
    MessageHandler(filters.Regex("^✅ Да, удалить шаблон$"), delete_template_final),
    MessageHandler(filters.Regex("^❌ Нет, отменить удаление$"), delete_template_final),
    MessageHandler(filters.Regex("^🔙 Назад$"), delete_template_select_group)
],
        },
        fallbacks=[CommandHandler("cancel", cancel_template)]
    )
