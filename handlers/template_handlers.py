from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.template_keyboards import (
    get_templates_main_keyboard, get_groups_keyboard, get_subgroups_keyboard,
    get_back_keyboard, get_skip_keyboard, get_days_keyboard, 
    get_days_continue_keyboard, get_frequency_keyboard, get_confirmation_keyboard
)
from authorized_users import is_authorized
from template_manager import (
    get_user_accessible_groups, create_template, get_templates_by_group,
    save_image, format_template_info, DAYS_OF_WEEK, FREQUENCY_TYPES, load_groups
)

# Состояния для ConversationHandler
(
    TEMPLATES_MAIN, TEMPLATE_LIST_GROUPS, TEMPLATE_LIST_SUBGROUPS, TEMPLATE_LIST_TEMPLATES,
    ADD_TEMPLATE_GROUP, ADD_TEMPLATE_SUBGROUP, ADD_TEMPLATE_NAME, ADD_TEMPLATE_TEXT,
    ADD_TEMPLATE_IMAGE, ADD_TEMPLATE_TIME, ADD_TEMPLATE_DAYS, ADD_TEMPLATE_FREQUENCY,
    ADD_TEMPLATE_SECOND_DAY, ADD_TEMPLATE_CONFIRM
) = range(14)

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
    from handlers.basic_handlers import cancel
    
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

# Заглушки для нереализованных функций
async def edit_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования шаблона"""
    await update.message.reply_text(
        "⚠️ **Редактирование шаблонов**\n\n"
        "Функция редактирования в разработке.\n"
        "Используйте создание нового шаблона или удаление + создание заново.",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

async def delete_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления шаблона"""
    await update.message.reply_text(
        "⚠️ **Удаление шаблонов**\n\n"
        "Функция удаления в разработке.\n"
        "Пока что шаблоны можно только просматривать и создавать новые.",
        parse_mode='Markdown',
        reply_markup=get_templates_main_keyboard()
    )
    return TEMPLATES_MAIN

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
            TEMPLATE_LIST_GROUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, template_list_choose_group),
                MessageHandler(filters.Regex("^🚗 Hongqi$"), template_list_choose_group),
                MessageHandler(filters.Regex("^🚙 TurboMatiz$"), template_list_choose_group),
                MessageHandler(filters.Regex("^🔙 К шаблонам$"), templates_main)
            ],
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
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
