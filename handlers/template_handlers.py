from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.template_keyboards import (
    get_templates_main_keyboard, get_groups_keyboard,
    get_template_confirmation_keyboard, get_template_edit_keyboard,
    get_back_keyboard, get_template_list_menu_keyboard, 
    get_delete_confirmation_keyboard, get_skip_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from template_manager_simplified import simplified_template_manager
from auth_manager import auth_manager

# === СОСТОЯНИЯ CONVERSATION HANDLER ===
(
    TEMPLATES_MAIN, TEMPLATE_LIST_MENU, TEMPLATE_LIST_ALL, 
    TEMPLATE_LIST_BY_GROUP, CREATE_TEMPLATE_GROUP, CREATE_TEMPLATE_NAME, 
    CREATE_TEMPLATE_TEXT, CREATE_TEMPLATE_IMAGE, CREATE_TEMPLATE_CONFIRM,
    EDIT_TEMPLATE_SELECT_GROUP, EDIT_TEMPLATE_SELECT, EDIT_TEMPLATE_FIELD,
    EDIT_TEMPLATE_NAME, EDIT_TEMPLATE_TEXT, EDIT_TEMPLATE_IMAGE,
    DELETE_TEMPLATE_SELECT_GROUP, DELETE_TEMPLATE_SELECT, DELETE_TEMPLATE_CONFIRM
) = range(18)

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
    from template_manager import get_user_accessible_groups
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_template_list_menu_keyboard()
        )
        return TEMPLATE_LIST_MENU
    
    # Получаем все шаблоны
    all_templates = simplified_template_manager.load_templates()
    
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
    message = "📋 **Все ваши шаблоны:**\n\n"
    
    for i, (template_id, template) in enumerate(user_templates.items(), 1):
        has_image = "🖼️" if template.get('image') else "❌"
        template_name = template.get('name', 'Без названия')
        template_group = template.get('group', 'Не указана')
        template_text = template.get('text', '')
        
        message += f"{i}. **{template_name}** {has_image}\n"
        message += f"   🏷️ Группа: {template_group}\n"
        message += f"   📄 Текст: {template_text[:50]}...\n\n"
    
    message += f"**Всего:** {len(user_templates)} шаблонов"
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_template_list_menu_keyboard()
    )
    return TEMPLATE_LIST_MENU

async def template_list_by_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало просмотра шаблонов по группам"""
    user_id = update.effective_user.id
    from template_manager import get_user_accessible_groups
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_template_list_menu_keyboard()
        )
        return TEMPLATE_LIST_MENU
    
    await update.message.reply_text(
        "🏷️ **Просмотр шаблонов по группам**\n\n"
        "Выберите группу шаблонов:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "list")
    )
    return TEMPLATE_LIST_BY_GROUP

async def template_list_by_group_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает шаблоны выбранной группы"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору способа просмотра:",
            reply_markup=get_template_list_menu_keyboard()
        )
        return TEMPLATE_LIST_MENU
    
    # Извлекаем название группы из текста (убираем эмодзи)
    group_name = user_text.replace("🏷️ ", "").strip()
    user_id = update.effective_user.id
    
    # Находим ID группы по имени
    from template_manager import get_user_accessible_groups, get_templates_by_group
    accessible_groups = get_user_accessible_groups(user_id)
    group_id = None
    for gid, gdata in accessible_groups.items():
        if gdata['name'] == group_name:
            group_id = gid
            break
    
    if not group_id:
        await update.message.reply_text(
            "❌ Группа шаблонов не найдена",
            reply_markup=get_groups_keyboard(user_id, "list")
        )
        return TEMPLATE_LIST_BY_GROUP
    
    # Получаем шаблоны группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе шаблонов '{group_name}' нет шаблонов",
            reply_markup=get_groups_keyboard(user_id, "list")
        )
        return TEMPLATE_LIST_BY_GROUP
    
    # Форматируем информацию о шаблонах группы
    message = f"📋 **Шаблоны группы '{group_name}':**\n\n"
    
    for i, (template_id, template) in enumerate(templates, 1):
        has_image = "🖼️" if template.get('image') else "❌"
        template_name = template.get('name', 'Без названия')
        template_text = template.get('text', '')
        
        message += f"{i}. **{template_name}** {has_image}\n"
        message += f"   📄 {template_text[:60]}...\n\n"
    
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
    from template_manager import get_user_accessible_groups
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
        "Шаг 1 из 5: Выберите группу шаблонов:",
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
    from template_manager import get_user_accessible_groups
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
            "❌ Группа шаблонов не найдена",
            reply_markup=get_groups_keyboard(user_id, "create")
        )
        return CREATE_TEMPLATE_GROUP
    
    # Сохраняем данные группы
    context.user_data['new_template']['group'] = group_id
    context.user_data['current_group'] = group_data
    
    await update.message.reply_text(
        "Шаг 2 из 5: Введите название шаблона:",
        reply_markup=get_back_keyboard()
    )
    return CREATE_TEMPLATE_NAME

async def create_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия шаблона"""
    name = update.message.text.strip()
    
    if name == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы шаблонов:",
            reply_markup=get_groups_keyboard(user_id, "create")
        )
        return CREATE_TEMPLATE_GROUP
    
    if not name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_NAME
    
    # Проверяем, нет ли уже шаблона с таким именем в группе
    group_id = context.user_data['new_template']['group']
    from template_manager import template_exists
    if template_exists(name, group_id):
        await update.message.reply_text(
            "❌ Шаблон с таким названием уже существует в этой группе.\n"
            "Пожалуйста, введите другое название:",
            reply_markup=get_back_keyboard()
        )
        return CREATE_TEMPLATE_NAME
    
    context.user_data['new_template']['name'] = name
    
    await update.message.reply_text(
        "Шаг 3 из 5: Введите текст шаблона:",
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
        "Шаг 4 из 5: Пришлите изображение для шаблона или нажмите '⏭️ Пропустить':",
        reply_markup=get_skip_keyboard()
    )
    return CREATE_TEMPLATE_IMAGE

async def create_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображения для шаблона"""
    if update.message.text == "⏭️ Пропустить":
        context.user_data['new_template']['image'] = None
        
        # Переходим к подтверждению
        return await show_template_confirmation(update, context)
    
    if update.message.photo:
        try:
            # Сохраняем изображение
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            
            # Создаем временный ID для сохранения
            temp_id = f"temp_{update.effective_user.id}_{update.update_id}"
            
            # Скачиваем изображение как bytes
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Сохраняем изображение
            image_path = simplified_template_manager.save_image(photo_bytes, temp_id)
            
            if image_path:
                context.user_data['new_template']['image'] = image_path
                await update.message.reply_text(
                    "✅ Изображение сохранено!\n\n"
                    "Переходим к подтверждению...",
                    reply_markup=get_back_keyboard()
                )
                return await show_template_confirmation(update, context)
            else:
                await update.message.reply_text(
                    "❌ Ошибка сохранения изображения. Попробуйте еще раз или пропустите:",
                    reply_markup=get_skip_keyboard()
                )
                return CREATE_TEMPLATE_IMAGE
        except Exception as e:
            print(f"❌ Ошибка обработки изображения: {e}")
            await update.message.reply_text(
                "❌ Ошибка обработки изображения. Попробуйте еще раз или пропустите:",
                reply_markup=get_skip_keyboard()
            )
            return CREATE_TEMPLATE_IMAGE
    else:
        await update.message.reply_text(
            "❌ Пожалуйста, пришлите изображение или нажмите '⏭️ Пропустить':",
            reply_markup=get_skip_keyboard()
        )
        return CREATE_TEMPLATE_IMAGE

async def show_template_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает подтверждение создания шаблона"""
    template_data = context.user_data['new_template']
    preview = simplified_template_manager.format_template_preview(template_data)
    
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
        
        # Если есть временное изображение, сохраняем его с правильным ID
        if template_data.get('image') and 'temp_' in template_data['image']:
            # Создаем шаблон сначала без изображения
            temp_image = template_data.pop('image')
            success, template_id = simplified_template_manager.create_template(template_data)
            
            if success:
                # Сохраняем изображение с правильным ID
                with open(temp_image, 'rb') as f:
                    image_bytes = f.read()
                final_image_path = simplified_template_manager.save_image(image_bytes, template_id)
                
                if final_image_path:
                    # Обновляем шаблон с правильным путем к изображению
                    template_data['image'] = final_image_path
                    simplified_template_manager.save_template(template_data)
                
                # Удаляем временный файл
                import os
                if os.path.exists(temp_image):
                    os.remove(temp_image)
            else:
                await update.message.reply_text(
                    "❌ Ошибка при создании шаблона",
                    reply_markup=get_templates_main_keyboard()
                )
                return TEMPLATES_MAIN
        else:
            success, template_id = simplified_template_manager.create_template(template_data)
        
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
        await update.message.reply_text(
            "🔧 **Что вы хотите изменить?**\n\n"
            "Выберите действие:",
            reply_markup=ReplyKeyboardMarkup([
                ["🏷️ Изменить группу", "📝 Изменить название"],
                ["📄 Изменить текст", "🖼️ Изменить изображение"],
                ["🔙 Назад"]
            ], resize_keyboard=True)
        )
        return CREATE_TEMPLATE_CONFIRM
    
    elif choice == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к добавлению изображения:",
            reply_markup=get_skip_keyboard()
        )
        return CREATE_TEMPLATE_IMAGE
    
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
    from template_manager import get_user_accessible_groups
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    await update.message.reply_text(
        "✏️ **Редактирование шаблона**\n\n"
        "Выберите группу шаблонов:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "edit")
    )
    return EDIT_TEMPLATE_SELECT_GROUP

async def edit_template_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для редактирования"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATES_MAIN
    
    # Извлекаем название группы из текста
    group_name = user_text.replace("🏷️ ", "").strip()
    user_id = update.effective_user.id
    
    # Находим ID группы по имени
    from template_manager import get_user_accessible_groups, get_templates_by_group
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
            "❌ Группа шаблонов не найдена",
            reply_markup=get_groups_keyboard(user_id, "edit")
        )
        return EDIT_TEMPLATE_SELECT_GROUP
    
    # Получаем шаблоны этой группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе шаблонов '{group_name}' нет шаблонов для редактирования",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Сохраняем данные группы
    context.user_data['edit_group_id'] = group_id
    context.user_data['edit_group_name'] = group_name
    
    # Создаем клавиатуру с шаблонами
    keyboard = []
    for template_id, template in templates:
        keyboard.append([f"📝 {template['name']}"])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"✏️ **Выберите шаблон для редактирования:**\n\n"
        f"Группа шаблонов: {group_name}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return EDIT_TEMPLATE_SELECT

async def edit_template_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для редактирования"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы шаблонов:",
            reply_markup=get_groups_keyboard(user_id, "edit")
        )
        return EDIT_TEMPLATE_SELECT_GROUP
    
    # Извлекаем название шаблона из текста
    template_name = user_text.replace("📝 ", "").strip()
    group_id = context.user_data.get('edit_group_id')
    
    if not group_id:
        await update.message.reply_text(
            "❌ Ошибка: данные группы не найдены",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Находим шаблон по имени и группе
    from template_manager import get_template_by_name_and_group
    template_id, template = get_template_by_name_and_group(template_name, group_id)
    
    if not template_id or not template:
        await update.message.reply_text(
            f"❌ Шаблон '{template_name}' не найден в группе",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Сохраняем данные для редактирования
    context.user_data['editing_template_id'] = template_id
    context.user_data['editing_template'] = template
    
    # Показываем информацию о шаблоне и кнопки выбора поля
    info = simplified_template_manager.format_template_info(template)
    
    await update.message.reply_text(
        f"✏️ **Редактирование шаблона**\n\n{info}\n"
        "**Выберите поле для редактирования:**",
        parse_mode='Markdown',
        reply_markup=get_template_edit_keyboard()
    )
    return EDIT_TEMPLATE_FIELD

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
    
    if field_text == "✅ Завершить редактирование":
        return await save_edited_template(update, context)
    
    elif field_text == "🔙 Назад":
        # Возвращаемся к выбору шаблона в группе
        group_name = context.user_data.get('edit_group_name', 'группы')
        keyboard = []
        from template_manager import get_templates_by_group
        templates = get_templates_by_group(context.user_data['edit_group_id'])
        for template_id, template_data in templates:
            keyboard.append([f"📝 {template_data['name']}"])
        keyboard.append(["🔙 Назад"])
        
        await update.message.reply_text(
            f"✏️ **Выберите шаблон для редактирования:**\n\nГруппа шаблонов: {group_name}",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return EDIT_TEMPLATE_SELECT
    
    elif field_text == "🏷️ Название":
        context.user_data['editing_field'] = 'name'
        await update.message.reply_text(
            f"✏️ Введите новое название шаблона:\n\nТекущее: {template.get('name', 'Не указано')}",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_NAME
        
    elif field_text == "📝 Текст":
        context.user_data['editing_field'] = 'text'
        await update.message.reply_text(
            f"✏️ Введите новый текст шаблона:\n\nТекущий: {template.get('text', 'Не указан')[:100]}...",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_TEXT
        
    elif field_text == "🖼️ Изображение":
        context.user_data['editing_field'] = 'image'
        await update.message.reply_text(
            "✏️ Пришлите новое изображение или нажмите '⏭️ Пропустить' для удаления текущего:",
            reply_markup=get_skip_keyboard()
        )
        return EDIT_TEMPLATE_IMAGE
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор поля",
            reply_markup=get_template_edit_keyboard()
        )
        return EDIT_TEMPLATE_FIELD

async def edit_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование названия"""
    new_name = update.message.text.strip()
    
    if new_name == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору поля:",
            reply_markup=get_template_edit_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
    if not new_name:
        await update.message.reply_text(
            "❌ Название не может быть пустым. Введите название:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_NAME
    
    # Проверяем, нет ли уже шаблона с таким именем в группе
    group_id = context.user_data['editing_template']['group']
    from template_manager import template_exists
    if template_exists(new_name, group_id) and new_name != context.user_data['editing_template']['name']:
        await update.message.reply_text(
            "❌ Шаблон с таким названием уже существует в этой группе.\n"
            "Пожалуйста, введите другое название:",
            reply_markup=get_back_keyboard()
        )
        return EDIT_TEMPLATE_NAME
    
    # Обновляем данные в контексте
    context.user_data['editing_template']['name'] = new_name
    
    await update.message.reply_text(
        f"✅ Название обновлено: {new_name}",
        reply_markup=get_template_edit_keyboard()
    )
    return EDIT_TEMPLATE_FIELD

async def edit_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование текста"""
    new_text = update.message.text.strip()
    
    if new_text == "🔙 Назад":
        await update.message.reply_text(
            "🔄 Возврат к выбору поля:",
            reply_markup=get_template_edit_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
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
        reply_markup=get_template_edit_keyboard()
    )
    return EDIT_TEMPLATE_FIELD

async def edit_template_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование изображения"""
    
    if update.message.text == "⏭️ Пропустить":
        # Удаляем изображение из шаблона
        old_image = context.user_data['editing_template'].get('image')
        if old_image:
            simplified_template_manager.delete_image(old_image)
        context.user_data['editing_template']['image'] = None
        
        await update.message.reply_text(
            "✅ Изображение удалено из шаблона",
            reply_markup=get_template_edit_keyboard()
        )
        return EDIT_TEMPLATE_FIELD
    
    if update.message.photo:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        photo_content = await photo_file.download_as_bytearray()
        
        template_id = context.user_data.get('editing_template_id')
        image_path = simplified_template_manager.save_image(photo_content, template_id)
        
        if image_path:
            # Удаляем старое изображение если было
            old_image = context.user_data['editing_template'].get('image')
            if old_image:
                simplified_template_manager.delete_image(old_image)
            
            # Обновляем данные в контексте
            context.user_data['editing_template']['image'] = image_path
            
            await update.message.reply_text(
                "✅ Изображение обновлено!",
                reply_markup=get_template_edit_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка сохранения изображения",
                reply_markup=get_template_edit_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ Пришлите изображение или нажмите '⏭️ Пропустить':",
            reply_markup=get_skip_keyboard()
        )
        return EDIT_TEMPLATE_IMAGE
    
    return EDIT_TEMPLATE_FIELD

async def save_edited_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение отредактированного шаблона"""
    template_id = context.user_data.get('editing_template_id')
    template_data = context.user_data['editing_template']
    
    if template_id:
        # Обновляем существующий шаблон
        success = simplified_template_manager.save_template(template_data)
        
        if success:
            await update.message.reply_text(
                f"✅ Шаблон успешно обновлен!\n\n"
                f"ID шаблона: `{template_id}`",
                parse_mode='Markdown',
                reply_markup=get_templates_main_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ Ошибка при обновлении шаблона",
                reply_markup=get_templates_main_keyboard()
            )
    else:
        await update.message.reply_text(
            "❌ Ошибка: ID шаблона не найден",
            reply_markup=get_templates_main_keyboard()
        )
    
    # Очищаем временные данные
    context.user_data.clear()
    return TEMPLATES_MAIN

# ===== УДАЛЕНИЕ ШАБЛОНОВ =====

async def delete_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления шаблона"""
    user_id = update.effective_user.id
    from template_manager import get_user_accessible_groups
    accessible_groups = get_user_accessible_groups(user_id)
    
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе шаблонов",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    await update.message.reply_text(
        "🗑️ **Удаление шаблона**\n\n"
        "Выберите группу шаблонов:",
        parse_mode='Markdown',
        reply_markup=get_groups_keyboard(user_id, "delete")
    )
    return DELETE_TEMPLATE_SELECT_GROUP

async def delete_template_select_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор группы для удаления"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        await templates_main(update, context)
        return TEMPLATES_MAIN
    
    # Извлекаем название группы из текста
    group_name = user_text.replace("🏷️ ", "").strip()
    user_id = update.effective_user.id
    
    # Находим ID группы по имени
    from template_manager import get_user_accessible_groups, get_templates_by_group
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
            "❌ Группа шаблонов не найдена",
            reply_markup=get_groups_keyboard(user_id, "delete")
        )
        return DELETE_TEMPLATE_SELECT_GROUP
    
    # Получаем шаблоны этой группы
    templates = get_templates_by_group(group_id)
    
    if not templates:
        await update.message.reply_text(
            f"📭 В группе шаблонов '{group_name}' нет шаблонов для удаления",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Сохраняем данные группы
    context.user_data['delete_group_id'] = group_id
    context.user_data['delete_group_name'] = group_name
    
    # Создаем клавиатуру с шаблонами
    keyboard = []
    for template_id, template in templates:
        keyboard.append([f"🗑️ {template['name']}"])
    
    keyboard.append(["🔙 Назад"])
    
    await update.message.reply_text(
        f"🗑️ **Выберите шаблон для удаления:**\n\n"
        f"Группа шаблонов: {group_name}",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return DELETE_TEMPLATE_SELECT

async def delete_template_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор шаблона для удаления"""
    user_text = update.message.text
    
    if user_text == "🔙 Назад":
        user_id = update.effective_user.id
        await update.message.reply_text(
            "🔄 Возврат к выбору группы шаблонов:",
            reply_markup=get_groups_keyboard(user_id, "delete")
        )
        return DELETE_TEMPLATE_SELECT_GROUP
    
    # Извлекаем название шаблона из текста
    template_name = user_text.replace("🗑️ ", "").strip()
    group_id = context.user_data.get('delete_group_id')
    
    if not group_id:
        await update.message.reply_text(
            "❌ Ошибка: данные группы не найдены",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Находим шаблон по имени и группе
    from template_manager import get_template_by_name_and_group
    template_id, template = get_template_by_name_and_group(template_name, group_id)
    
    if not template_id or not template:
        await update.message.reply_text(
            f"❌ Шаблон '{template_name}' не найден в группе",
            reply_markup=get_templates_main_keyboard()
        )
        return TEMPLATES_MAIN
    
    # Сохраняем данные для удаления
    context.user_data['deleting_template_id'] = template_id
    context.user_data['deleting_template'] = template
    
    # Показываем подтверждение
    info = simplified_template_manager.format_template_info(template)
    
    await update.message.reply_text(
        f"⚠️ **ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ**\n\n{info}\n"
        "❌ **ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ДАННЫЙ ШАБЛОН?**\n\n"
        "Это действие нельзя отменить!",
        parse_mode='Markdown',
        reply_markup=get_delete_confirmation_keyboard()
    )
    return DELETE_TEMPLATE_CONFIRM

async def delete_template_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления шаблона"""
    user_choice = update.message.text
    template_id = context.user_data.get('deleting_template_id')
    template = context.user_data.get('deleting_template')
    
    if user_choice == "✅ Да, удалить":
        if template_id and template:
            # Удаляем изображение если есть
            if template.get('image'):
                simplified_template_manager.delete_image(template['image'])
            
            # Удаляем шаблон из базы данных
            from template_manager import delete_template
            success = delete_template(template_id)
            
            if success:
                await update.message.reply_text(
                    f"✅ Шаблон '{template['name']}' успешно удален!",
                    reply_markup=get_templates_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при удалении шаблона",
                    reply_markup=get_templates_main_keyboard()
                )
        else:
            await update.message.reply_text(
                "❌ Ошибка: данные шаблона не найдены",
                reply_markup=get_templates_main_keyboard()
            )
    
    elif user_choice == "❌ Нет, отменить":
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
    """Возвращает настроенный ConversationHandler для упрощенных шаблонов"""
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
            
            # Создание шаблона (упрощенное)
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
            CREATE_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), create_template_image)
            ],
            
            # Редактирование шаблона
            EDIT_TEMPLATE_SELECT_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_select_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            EDIT_TEMPLATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_select),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_start)
            ],
            EDIT_TEMPLATE_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_template_choose_field),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_select)
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
                MessageHandler(filters.PHOTO, edit_template_image),
                MessageHandler(filters.Regex("^⏭️ Пропустить$"), edit_template_image),
                MessageHandler(filters.Regex("^🔙 Назад$"), edit_template_choose_field)
            ],
            
            # Удаление шаблона
            DELETE_TEMPLATE_SELECT_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_select_group),
                MessageHandler(filters.Regex("^🔙 Назад$"), templates_main)
            ],
            DELETE_TEMPLATE_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_select),
                MessageHandler(filters.Regex("^🔙 Назад$"), delete_template_start)
            ],
            DELETE_TEMPLATE_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_template_confirm),
                MessageHandler(filters.Regex("^🔙 Назад$"), delete_template_select)
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_template)]
    )