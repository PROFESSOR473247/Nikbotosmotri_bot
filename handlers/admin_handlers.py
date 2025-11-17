from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from keyboards.admin_keyboards import (
    get_admin_main_keyboard, get_users_management_keyboard, get_chats_management_keyboard,
    get_user_edit_keyboard, get_chat_edit_keyboard, get_roles_keyboard,
    get_keep_name_keyboard, get_confirmation_keyboard, get_back_keyboard
)
from keyboards.main_keyboards import get_main_keyboard
from user_chat_manager import user_chat_manager
from template_manager import load_groups
from auth_manager import auth_manager
from authorized_users import is_admin

# Состояния для ConversationHandler администрирования
(
    ADMIN_MAIN, USERS_MANAGEMENT, CHATS_MANAGEMENT,
    ADD_USER_ID, ADD_USER_NAME, ADD_USER_ROLE, ADD_USER_CHATS, ADD_USER_GROUPS,
    EDIT_USER_SELECT, EDIT_USER_MAIN, EDIT_USER_ROLE, EDIT_USER_CHATS, EDIT_USER_GROUPS,
    DELETE_USER_SELECT, DELETE_USER_CONFIRM,
    ADD_CHAT_ID, ADD_CHAT_NAME, ADD_CHAT_USERS,
    EDIT_CHAT_SELECT, EDIT_CHAT_MAIN, EDIT_CHAT_ADD_USER, EDIT_CHAT_REMOVE_USER,
    DELETE_CHAT_SELECT, DELETE_CHAT_CONFIRM
) = range(24)

# ===== ОСНОВНЫЕ ФУНКЦИИ АДМИНИСТРИРОВАНИЯ =====

async def admin_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню администрирования"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ У вас нет прав доступа к администрированию",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "⚙️ **Администрирование системы**\n\n"
        "Выберите раздел для управления:",
        parse_mode='Markdown',
        reply_markup=get_admin_main_keyboard()
    )
    return ADMIN_MAIN

# ===== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ =====

async def users_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления пользователями"""
    await update.message.reply_text(
        "👥 **Управление пользователями**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_users_management_keyboard()
    )
    return USERS_MANAGEMENT

# --- ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ---

async def add_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления пользователя"""
    context.user_data['new_user'] = {}
    
    await update.message.reply_text(
        "👥 **Добавление нового пользователя**\n\n"
        "Шаг 1 из 5: Введите ID пользователя (только цифры):",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return ADD_USER_ID

async def add_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод ID пользователя"""
    user_id_text = update.message.text.strip()
    
    if user_id_text == "🔙 Назад":
        await users_management(update, context)
        return USERS_MANAGEMENT
    
    try:
        user_id = int(user_id_text)
        
        # Проверка дубликата
        from authorized_users import check_duplicate_user
        if check_duplicate_user(user_id):
            await update.message.reply_text(
                f"❌ Пользователь с ID {user_id} уже существует в системе!\n"
                f"Введите другой ID пользователя:",
                reply_markup=get_back_keyboard()
            )
            return ADD_USER_ID
        
        context.user_data['new_user']['user_id'] = user_id
        
        await update.message.reply_text(
            "Шаг 2 из 5: Введите имя нового пользователя:",
            reply_markup=get_back_keyboard()
        )
        return ADD_USER_NAME
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат ID. Введите только цифры:",
            reply_markup=get_back_keyboard()
        )
        return ADD_USER_ID

async def add_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод имени пользователя"""
    user_name = update.message.text.strip()
    
    if user_name == "🔙 Назад":
        await add_user_start(update, context)
        return ADD_USER_ID
    
    if not user_name:
        await update.message.reply_text(
            "❌ Имя не может быть пустым. Введите имя:",
            reply_markup=get_back_keyboard()
        )
        return ADD_USER_NAME
    
    context.user_data['new_user']['full_name'] = user_name
    
    await update.message.reply_text(
        "Шаг 3 из 5: Выберите уровень доступа (должность):",
        reply_markup=get_roles_keyboard()
    )
    return ADD_USER_ROLE

async def add_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор роли пользователя"""
    role_text = update.message.text
    
    if role_text == "🔙 Назад":
        await add_user_name(update, context)
        return ADD_USER_NAME
    
    role_map = {
        "👑 Руководитель": "manager",
        "🚗 Водитель": "driver", 
        "👥 Гость": "guest"
    }
    
    if role_text not in role_map:
        await update.message.reply_text(
            "❌ Выберите роль из предложенных:",
            reply_markup=get_roles_keyboard()
        )
        return ADD_USER_ROLE
    
    context.user_data['new_user']['role'] = role_map[role_text]
    
    # Показываем список Telegram чатов
    chats = user_chat_manager.get_all_chats()
    if not chats:
        await update.message.reply_text(
            "❌ В системе нет добавленных Telegram чатов.\n"
            "Сначала добавьте чаты в разделе 'Тг чаты'.",
            reply_markup=get_users_management_keyboard()
        )
        return USERS_MANAGEMENT
    
    chat_list = "💬 **К каким Telegram чатам будет доступ у нового пользователя:**\n\n"
    for i, chat in enumerate(chats, 1):
        chat_list += f"{i} - {chat['chat_name']}\n"
    
    chat_list += "\nУкажите ЧЕРЕЗ ЗАПЯТУЮ номера чатов для добавления (например: 1, 3):"
    
    context.user_data['available_chats'] = chats
    
    await update.message.reply_text(
        chat_list,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return ADD_USER_CHATS

async def add_user_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор Telegram чатов для пользователя"""
    chat_numbers_text = update.message.text.strip()
    
    if chat_numbers_text == "🔙 Назад":
        await add_user_role(update, context)
        return ADD_USER_ROLE
    
    chats = context.user_data['available_chats']
    
    try:
        # Парсим номера чатов
        chat_numbers = [int(num.strip()) for num in chat_numbers_text.split(',')]
        
        # Проверяем валидность номеров
        valid_numbers = []
        for num in chat_numbers:
            if 1 <= num <= len(chats):
                valid_numbers.append(num)
        
        if not valid_numbers:
            await update.message.reply_text(
                "❌ Неверные номера чатов. Укажите номера через запятую:",
                reply_markup=get_back_keyboard()
            )
            return ADD_USER_CHATS
        
        context.user_data['new_user']['selected_chats'] = valid_numbers
        
        # Показываем список групп шаблонов
        groups_data = load_groups()
        groups = []
        for group_id, group_data in groups_data['groups'].items():
            groups.append({'id': group_id, 'name': group_data['name']})
        
        if not groups:
            await update.message.reply_text(
                "❌ В системе нет групп шаблонов.",
                reply_markup=get_users_management_keyboard()
            )
            return USERS_MANAGEMENT
        
        group_list = "📋 **В какие группы шаблонов необходимо добавить нового пользователя:**\n\n"
        for i, group in enumerate(groups, 1):
            group_list += f"{i} - {group['name']}\n"
        
        group_list += "\nУкажите ЧЕРЕЗ ЗАПЯТУЮ номера групп для добавления (например: 1, 3):"
        
        context.user_data['available_groups'] = groups
        
        await update.message.reply_text(
            group_list,
            parse_mode='Markdown',
            reply_markup=get_back_keyboard()
        )
        return ADD_USER_GROUPS
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Укажите номера через запятую:",
            reply_markup=get_back_keyboard()
        )
        return ADD_USER_CHATS

async def add_user_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор групп шаблонов для пользователя"""
    group_numbers_text = update.message.text.strip()
    
    if group_numbers_text == "🔙 Назад":
        await add_user_chats(update, context)
        return ADD_USER_CHATS
    
    groups = context.user_data['available_groups']
    user_data = context.user_data['new_user']
    
    try:
        # Парсим номера групп
        group_numbers = [int(num.strip()) for num in group_numbers_text.split(',')]
        
        # Проверяем валидность номеров
        valid_numbers = []
        for num in group_numbers:
            if 1 <= num <= len(groups):
                valid_numbers.append(num)
        
        if not valid_numbers:
            await update.message.reply_text(
                "❌ Неверные номера групп. Укажите номера через запятую:",
                reply_markup=get_back_keyboard()
            )
            return ADD_USER_GROUPS
        
        # Сохраняем пользователя
        success, message = user_chat_manager.add_user(
            user_data['user_id'],
            "",  # username можно оставить пустым
            user_data['full_name'],
            user_data['role']
        )
        
        if not success:
            await update.message.reply_text(
                f"❌ Ошибка при добавлении пользователя: {message}",
                reply_markup=get_users_management_keyboard()
            )
            return USERS_MANAGEMENT
        
        # Предоставляем доступ к выбранным чатам
        chats = context.user_data['available_chats']
        for chat_num in user_data['selected_chats']:
            chat = chats[chat_num - 1]
            user_chat_manager.grant_chat_access(user_data['user_id'], chat['chat_id'])
        
        # Предоставляем доступ к выбранным группам
        for group_num in valid_numbers:
            group = groups[group_num - 1]
            user_chat_manager.grant_template_group_access(user_data['user_id'], group['id'])
        
        # Формируем отчет
        chat_names = [chats[num-1]['chat_name'] for num in user_data['selected_chats']]
        group_names = [groups[num-1]['name'] for num in valid_numbers]
        
        report = f"✅ **Пользователь успешно добавлен!**\n\n"
        report += f"👤 **Имя:** {user_data['full_name']}\n"
        report += f"🆔 **ID:** {user_data['user_id']}\n"
        report += f"👑 **Должность:** {user_data['role']}\n"
        report += f"💬 **Доступ к чатам:** {', '.join(chat_names)}\n"
        report += f"📋 **Доступ к группам:** {', '.join(group_names)}\n"
        
        await update.message.reply_text(
            report,
            parse_mode='Markdown',
            reply_markup=get_users_management_keyboard()
        )
        
        # Очищаем временные данные
        context.user_data.clear()
        return USERS_MANAGEMENT
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Укажите номера через запятую:",
            reply_markup=get_back_keyboard()
        )
        return ADD_USER_GROUPS

# --- СПИСОК ПОЛЬЗОВАТЕЛЕЙ ---

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех пользователей"""
    users = user_chat_manager.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "📭 В системе нет пользователей",
            reply_markup=get_users_management_keyboard()
        )
        return USERS_MANAGEMENT
    
    message = "👥 **Список пользователей:**\n\n"
    
    for i, user in enumerate(users, 1):
        # Получаем доступы пользователя
        user_chats = user_chat_manager.get_user_chat_access(user['user_id'])
        user_groups = user_chat_manager.get_user_template_group_access(user['user_id'])
        
        chat_names = [chat['chat_name'] for chat in user_chats]
        group_names = [group['name'] for group in user_groups]
        
        message += f"{i}. **{user['full_name']}** (ID: {user['user_id']})\n"
        message += f"   👑 Должность: {user['role']}\n"
        message += f"   💬 Чаты: {', '.join(chat_names) if chat_names else 'Нет доступа'}\n"
        message += f"   📋 Группы: {', '.join(group_names) if group_names else 'Нет доступа'}\n\n"
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_users_management_keyboard()
    )
    return USERS_MANAGEMENT

# --- УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ ---

async def delete_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления пользователя"""
    users = user_chat_manager.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "📭 В системе нет пользователей для удаления",
            reply_markup=get_users_management_keyboard()
        )
        return USERS_MANAGEMENT
    
    user_list = "🗑️ **Выберите пользователя для удаления:**\n\n"
    for i, user in enumerate(users, 1):
        user_list += f"{i}. {user['full_name']} (ID: {user['user_id']})\n"
    
    user_list += "\nВведите номер пользователя:"
    
    context.user_data['users_for_deletion'] = users
    
    await update.message.reply_text(
        user_list,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return DELETE_USER_SELECT

async def delete_user_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор пользователя для удаления"""
    user_number_text = update.message.text.strip()
    
    if user_number_text == "🔙 Назад":
        await users_management(update, context)
        return USERS_MANAGEMENT
    
    users = context.user_data['users_for_deletion']
    
    try:
        user_number = int(user_number_text)
        if 1 <= user_number <= len(users):
            user = users[user_number - 1]
            context.user_data['deleting_user'] = user
            
            await update.message.reply_text(
                f"⚠️ **ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ**\n\n"
                f"Вы действительно хотите удалить пользователя:\n"
                f"👤 **{user['full_name']}** (ID: {user['user_id']})\n\n"
                f"❌ Это действие нельзя отменить!",
                parse_mode='Markdown',
                reply_markup=get_confirmation_keyboard()
            )
            return DELETE_USER_CONFIRM
        else:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный номер пользователя. Введите номер из списка:",
            reply_markup=get_back_keyboard()
        )
        return DELETE_USER_SELECT

async def delete_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления пользователя"""
    choice = update.message.text
    user = context.user_data.get('deleting_user')
    
    if choice == "🔙 Назад":
        await delete_user_select(update, context)
        return DELETE_USER_SELECT
    
    if choice == "✅ Да":
        if user:
            success, message = user_chat_manager.delete_user(user['user_id'])
            
            if success:
                await update.message.reply_text(
                    f"✅ Пользователь {user['full_name']} успешно удален!",
                    reply_markup=get_users_management_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при удалении: {message}",
                    reply_markup=get_users_management_keyboard()
                )
        else:
            await update.message.reply_text(
                "❌ Ошибка: данные пользователя не найдены",
                reply_markup=get_users_management_keyboard()
            )
    
    elif choice == "❌ Нет":
        await update.message.reply_text(
            "✅ Удаление отменено",
            reply_markup=get_users_management_keyboard()
        )
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_confirmation_keyboard()
        )
        return DELETE_USER_CONFIRM
    
    # Очищаем временные данные
    context.user_data.clear()
    return USERS_MANAGEMENT

# ===== УПРАВЛЕНИЕ TELEGRAM ЧАТАМИ =====

async def chats_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления Telegram чатами"""
    await update.message.reply_text(
        "💬 **Управление Telegram чатами**\n\n"
        "Выберите действие:",
        parse_mode='Markdown',
        reply_markup=get_chats_management_keyboard()
    )
    return CHATS_MANAGEMENT

# --- ДОБАВЛЕНИЕ ЧАТА ---

async def add_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления чата"""
    context.user_data['new_chat'] = {}
    
    await update.message.reply_text(
        "💬 **Добавление нового Telegram чата**\n\n"
        "Шаг 1 из 3: Введите ID чата (только цифры, включая минус для групп):",
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return ADD_CHAT_ID

async def add_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод ID чата"""
    chat_id_text = update.message.text.strip()
    
    if chat_id_text == "🔙 Назад":
        await chats_management(update, context)
        return CHATS_MANAGEMENT
    
    try:
        chat_id = int(chat_id_text)
        context.user_data['new_chat']['chat_id'] = chat_id
        
        await update.message.reply_text(
            "Шаг 2 из 3: Введите название для чата или нажмите 'Оставить название', "
            "если хотите использовать название из Telegram:",
            reply_markup=get_keep_name_keyboard()
        )
        return ADD_CHAT_NAME
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат ID. Введите только цифры (для групп с минусом):",
            reply_markup=get_back_keyboard()
        )
        return ADD_CHAT_ID

async def add_chat_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод названия чата"""
    choice = update.message.text
    
    if choice == "🔙 Назад":
        await add_chat_id(update, context)
        return ADD_CHAT_ID
    
    if choice == "✅ Оставить название":
        # Используем ID как временное название
        chat_id = context.user_data['new_chat']['chat_id']
        chat_name = f"Чат {chat_id}"
        context.user_data['new_chat']['chat_name'] = chat_name
        context.user_data['new_chat']['original_name'] = chat_name
        
    elif choice == "✏️ Ввести новое":
        await update.message.reply_text(
            "Введите новое название для чата:",
            reply_markup=get_back_keyboard()
        )
        return ADD_CHAT_NAME
    
    else:
        # Пользователь ввел название вручную
        chat_name = choice.strip()
        if not chat_name:
            await update.message.reply_text(
                "❌ Название не может быть пустым. Введите название:",
                reply_markup=get_back_keyboard()
            )
            return ADD_CHAT_NAME
        
        context.user_data['new_chat']['chat_name'] = chat_name
        context.user_data['new_chat']['original_name'] = chat_name
    
    # Показываем список пользователей для выбора
    users = user_chat_manager.get_all_users()
    if not users:
        await update.message.reply_text(
            "❌ В системе нет пользователей.\n"
            "Сначала добавьте пользователей в разделе 'Пользователи'.",
            reply_markup=get_chats_management_keyboard()
        )
        return CHATS_MANAGEMENT
    
    user_list = "👥 **У кого из пользователей будет доступ к новому Telegram чату:**\n\n"
    for i, user in enumerate(users, 1):
        user_list += f"{i} - {user['full_name']} ({user['role']})\n"
    
    user_list += "\nУкажите ЧЕРЕЗ ЗАПЯТУЮ номера пользователей для добавления (например: 1, 3):"
    
    context.user_data['available_users'] = users
    
    await update.message.reply_text(
        user_list,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return ADD_CHAT_USERS

async def add_chat_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор пользователей для чата"""
    user_numbers_text = update.message.text.strip()
    
    if user_numbers_text == "🔙 Назад":
        await add_chat_name(update, context)
        return ADD_CHAT_NAME
    
    users = context.user_data['available_users']
    chat_data = context.user_data['new_chat']
    
    try:
        # Парсим номера пользователей
        user_numbers = [int(num.strip()) for num in user_numbers_text.split(',')]
        
        # Проверяем валидность номеров
        valid_numbers = []
        for num in user_numbers:
            if 1 <= num <= len(users):
                valid_numbers.append(num)
        
        if not valid_numbers:
            await update.message.reply_text(
                "❌ Неверные номера пользователей. Укажите номера через запятую:",
                reply_markup=get_back_keyboard()
            )
            return ADD_CHAT_USERS
        
        # Сохраняем чат
        success, message = user_chat_manager.add_telegram_chat(
            chat_data['chat_id'],
            chat_data['chat_name'],
            chat_data.get('original_name')
        )
        
        if not success:
            await update.message.reply_text(
                f"❌ Ошибка при добавлении чата: {message}",
                reply_markup=get_chats_management_keyboard()
            )
            return CHATS_MANAGEMENT
        
        # Предоставляем доступ выбранным пользователям
        for user_num in valid_numbers:
            user = users[user_num - 1]
            user_chat_manager.grant_chat_access(user['user_id'], chat_data['chat_id'])
        
        # Формируем отчет
        user_names = [users[num-1]['full_name'] for num in valid_numbers]
        
        report = f"✅ **Telegram чат успешно добавлен!**\n\n"
        report += f"💬 **Название:** {chat_data['chat_name']}\n"
        report += f"🆔 **ID:** {chat_data['chat_id']}\n"
        report += f"👥 **Доступ у пользователей:** {', '.join(user_names)}\n"
        
        await update.message.reply_text(
            report,
            parse_mode='Markdown',
            reply_markup=get_chats_management_keyboard()
        )
        
        # Очищаем временные данные
        context.user_data.clear()
        return CHATS_MANAGEMENT
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Укажите номера через запятую:",
            reply_markup=get_back_keyboard()
        )
        return ADD_CHAT_USERS

# --- СПИСОК ЧАТОВ ---

async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех Telegram чатов"""
    chats = user_chat_manager.get_all_chats()
    
    if not chats:
        await update.message.reply_text(
            "📭 В системе нет Telegram чатов",
            reply_markup=get_chats_management_keyboard()
        )
        return CHATS_MANAGEMENT
    
    message = "💬 **Список Telegram чатов:**\n\n"
    
    for i, chat in enumerate(chats, 1):
        # Получаем пользователей, имеющих доступ к чату
        chat_users = user_chat_manager.get_chat_users(chat['chat_id'])
        user_names = [user['full_name'] for user in chat_users]
        
        message += f"{i}. **{chat['chat_name']}** (ID: {chat['chat_id']})\n"
        message += f"   👥 Пользователи: {', '.join(user_names) if user_names else 'Нет доступа'}\n\n"
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_chats_management_keyboard()
    )
    return CHATS_MANAGEMENT

# --- УДАЛЕНИЕ ЧАТА ---

async def delete_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления чата"""
    chats = user_chat_manager.get_all_chats()
    
    if not chats:
        await update.message.reply_text(
            "📭 В системе нет чатов для удаления",
            reply_markup=get_chats_management_keyboard()
        )
        return CHATS_MANAGEMENT
    
    chat_list = "🗑️ **Выберите чат для удаления:**\n\n"
    for i, chat in enumerate(chats, 1):
        chat_list += f"{i}. {chat['chat_name']} (ID: {chat['chat_id']})\n"
    
    chat_list += "\nВведите номер чата:"
    
    context.user_data['chats_for_deletion'] = chats
    
    await update.message.reply_text(
        chat_list,
        parse_mode='Markdown',
        reply_markup=get_back_keyboard()
    )
    return DELETE_CHAT_SELECT

async def delete_chat_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор чата для удаления"""
    chat_number_text = update.message.text.strip()
    
    if chat_number_text == "🔙 Назад":
        await chats_management(update, context)
        return CHATS_MANAGEMENT
    
    chats = context.user_data['chats_for_deletion']
    
    try:
        chat_number = int(chat_number_text)
        if 1 <= chat_number <= len(chats):
            chat = chats[chat_number - 1]
            context.user_data['deleting_chat'] = chat
            
            await update.message.reply_text(
                f"⚠️ **ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ**\n\n"
                f"Вы действительно хотите удалить чат:\n"
                f"💬 **{chat['chat_name']}** (ID: {chat['chat_id']})\n\n"
                f"❌ Это действие нельзя отменить!",
                parse_mode='Markdown',
                reply_markup=get_confirmation_keyboard()
            )
            return DELETE_CHAT_CONFIRM
        else:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный номер чата. Введите номер из списка:",
            reply_markup=get_back_keyboard()
        )
        return DELETE_CHAT_SELECT

async def delete_chat_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления чата"""
    choice = update.message.text
    chat = context.user_data.get('deleting_chat')
    
    if choice == "🔙 Назад":
        await delete_chat_select(update, context)
        return DELETE_CHAT_SELECT
    
    if choice == "✅ Да":
        if chat:
            success, message = user_chat_manager.delete_chat(chat['chat_id'])
            
            if success:
                await update.message.reply_text(
                    f"✅ Чат {chat['chat_name']} успешно удален!",
                    reply_markup=get_chats_management_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ Ошибка при удалении: {message}",
                    reply_markup=get_chats_management_keyboard()
                )
        else:
            await update.message.reply_text(
                "❌ Ошибка: данные чата не найдены",
                reply_markup=get_chats_management_keyboard()
            )
    
    elif choice == "❌ Нет":
        await update.message.reply_text(
            "✅ Удаление отменено",
            reply_markup=get_chats_management_keyboard()
        )
    
    else:
        await update.message.reply_text(
            "❌ Неверный выбор",
            reply_markup=get_confirmation_keyboard()
        )
        return DELETE_CHAT_CONFIRM
    
    # Очищаем временные данные
    context.user_data.clear()
    return CHATS_MANAGEMENT

# ===== ТЕСТ ПРАВ =====

async def test_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестирование прав доступа"""
    await update.message.reply_text(
        "🔧 **Тест прав доступа**\n\n"
        "Эта функция находится в разработке.\n"
        "В будущем здесь можно будет тестировать права доступа пользователей.",
        parse_mode='Markdown',
        reply_markup=get_admin_main_keyboard()
    )
    return ADMIN_MAIN

# ===== СПРАВКА АДМИНИСТРАТОРА =====

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка для администратора"""
    help_text = """
⚙️ СПРАВКА ДЛЯ АДМИНИСТРАТОРА

👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ:
• Добавить - создание нового пользователя
• Изменить доступ - редактирование прав пользователя  
• Список пользователей - просмотр всех пользователей
• Удалить - удаление пользователя

💬 УПРАВЛЕНИЕ TELEGRAM ЧАТАМИ:
• Добавить - добавление нового чата/канала/группы
• Изменить доступ - управление доступом пользователей к чатам
• Список чатов - просмотр всех чатов
• Удалить - удаление чата из системы

🔧 ТЕСТ ПРАВ:
• Проверка прав доступа пользователей (в разработке)

🛠 ДЕБАГ КОМАНДЫ:
• /admin_stats - статистика системы
• /check_access user_id - проверка прав пользователя
• /reload_config - перезагрузка конфигурации

📋 ПРОЦЕСС ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯ:
1. Ввод ID пользователя (только цифры)
2. Ввод имени пользователя
3. Выбор должности (руководитель/водитель/гость)
4. Выбор Telegram чатов для доступа
5. Выбор групп шаблонов для доступа

📋 ПРОЦЕСС ДОБАВЛЕНИЯ ЧАТА:
1. Ввод ID чата (цифры, с минусом для групп)
2. Ввод названия чата
3. Выбор пользователей с доступом к чату

💡 ПОЛУЧЕНИЕ ID:
Пользователь может получить свой ID командой /my_id
Для получения ID чата добавьте бота в чат и используйте /my_id
"""

    await update.message.reply_text(
        help_text,
        parse_mode=None,
        reply_markup=get_admin_main_keyboard()
    )
    return ADMIN_MAIN

# ===== ДЕБАГ КОМАНДЫ =====

async def debug_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная функция для проверки работы админ-меню"""
    user_id = update.effective_user.id
    text = update.message.text
    
    print(f"🔧 DEBUG ADMIN: user_id={user_id}, text='{text}'")
    
    # Проверяем права
    if not is_admin(user_id):
        await update.message.reply_text("❌ Нет прав доступа")
        return ConversationHandler.END
    
    # В зависимости от нажатой кнопки переходим в нужное состояние
    if text == "👥 Пользователи":
        await update.message.reply_text(
            "👥 **Управление пользователями**\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=get_users_management_keyboard()
        )
        return USERS_MANAGEMENT
        
    elif text == "💬 Тг чаты":
        await update.message.reply_text(
            "💬 **Управление Telegram чатами**\n\nВыберите действие:",
            parse_mode='Markdown', 
            reply_markup=get_chats_management_keyboard()
        )
        return CHATS_MANAGEMENT
        
    elif text == "🔧 Тест прав":
        await update.message.reply_text(
            "🔧 **Тест прав доступа**\n\nЭта функция находится в разработке.",
            parse_mode='Markdown',
            reply_markup=get_admin_main_keyboard()
        )
        return ADMIN_MAIN
        
    elif text == "📋 Справка":
        await admin_help(update, context)
        return ADMIN_MAIN
    
    await update.message.reply_text(
        f"🔧 Отладка: вы нажали '{text}'\nUser ID: {user_id}",
        reply_markup=get_admin_main_keyboard()
    )
    return ADMIN_MAIN

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику системы"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав доступа к этой команде")
        return
    
    # Получаем статистику
    users = user_chat_manager.get_all_users()
    chats = user_chat_manager.get_all_chats()
    groups_data = load_groups()
    groups = list(groups_data['groups'].values())
    
    # Статистика по ролям
    roles_count = {}
    for user in users:
        role = user['role']
        roles_count[role] = roles_count.get(role, 0) + 1
    
    stats_text = "📊 **СТАТИСТИКА СИСТЕМЫ**\n\n"
    stats_text += f"👥 **Пользователи:** {len(users)}\n"
    stats_text += f"💬 **Telegram чаты:** {len(chats)}\n"
    stats_text += f"📋 **Группы шаблонов:** {len(groups)}\n\n"
    
    stats_text += "👑 **Распределение по ролям:**\n"
    for role, count in roles_count.items():
        stats_text += f"• {role}: {count}\n"
    
    # Активность чатов
    active_chats = [chat for chat in chats if user_chat_manager.get_chat_users(chat['chat_id'])]
    stats_text += f"\n💬 **Активные чаты (с пользователями):** {len(active_chats)}"
    
    await update.message.reply_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=get_admin_main_keyboard()
    )

async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет права доступа пользователя"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав доступа к этой команде")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: /check_access user_id")
        return
    
    try:
        target_user_id = int(context.args[0])
        
        # Получаем информацию о пользователе
        users = user_chat_manager.get_all_users()
        target_user = None
        for user in users:
            if user['user_id'] == target_user_id:
                target_user = user
                break
        
        if not target_user:
            await update.message.reply_text(f"❌ Пользователь с ID {target_user_id} не найден")
            return
        
        # Получаем доступы пользователя
        user_chats = user_chat_manager.get_user_chat_access(target_user_id)
        user_groups = user_chat_manager.get_user_template_group_access(target_user_id)
        
        access_text = f"🔍 **ПРАВА ДОСТУПА ПОЛЬЗОВАТЕЛЯ**\n\n"
        access_text += f"👤 **Пользователь:** {target_user['full_name']}\n"
        access_text += f"🆔 **ID:** {target_user_id}\n"
        access_text += f"👑 **Должность:** {target_user['role']}\n\n"
        
        access_text += "💬 **Доступ к Telegram чатам:**\n"
        if user_chats:
            for chat in user_chats:
                access_text += f"• {chat['chat_name']} (ID: {chat['chat_id']})\n"
        else:
            access_text += "❌ Нет доступа\n"
        
        access_text += "\n📋 **Доступ к группам шаблонов:**\n"
        if user_groups:
            for group in user_groups:
                access_text += f"• {group['name']} (ID: {group['id']})\n"
        else:
            access_text += "❌ Нет доступа\n"
        
        await update.message.reply_text(
            access_text,
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат ID пользователя")

# ===== ФУНКЦИЯ ОТМЕНЫ =====

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def get_admin_conversation_handler():
    """Возвращает настроенный ConversationHandler для администрирования"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ Администрирование$"), admin_main)],
        states={
            ADMIN_MAIN: [
                MessageHandler(filters.Regex("^👥 Пользователи$"), users_management),
                MessageHandler(filters.Regex("^💬 Тг чаты$"), chats_management),
                MessageHandler(filters.Regex("^🔧 Тест прав$"), test_permissions),
                MessageHandler(filters.Regex("^📋 Справка$"), admin_help),
                MessageHandler(filters.Regex("^🔙 Главное меню$"), cancel_admin)
            ],
            
            # === УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ===
            USERS_MANAGEMENT: [
                MessageHandler(filters.Regex("^➕ Добавить пользователя$"), add_user_start),
                MessageHandler(filters.Regex("^📋 Список пользователей$"), list_users),
                MessageHandler(filters.Regex("^🗑️ Удалить пользователя$"), delete_user_start),
                MessageHandler(filters.Regex("^🔙 К администрированию$"), admin_main)
            ],
            
            # ДОБАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
            ADD_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_id),
            ],
            ADD_USER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_name),
            ],
            ADD_USER_ROLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_role),
            ],
            ADD_USER_CHATS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_chats),
            ],
            ADD_USER_GROUPS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_user_groups),
            ],
            
            # УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
            DELETE_USER_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_user_select),
            ],
            DELETE_USER_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_user_confirm),
            ],
            
            # === УПРАВЛЕНИЕ TELEGRAM ЧАТАМИ ===
            CHATS_MANAGEMENT: [
                MessageHandler(filters.Regex("^➕ Добавить чат$"), add_chat_start),
                MessageHandler(filters.Regex("^📋 Список чатов$"), list_chats),
                MessageHandler(filters.Regex("^🗑️ Удалить чат$"), delete_chat_start),
                MessageHandler(filters.Regex("^🔙 К администрированию$"), admin_main)
            ],
            
            # ДОБАВЛЕНИЕ ЧАТА
            ADD_CHAT_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_chat_id),
            ],
            ADD_CHAT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_chat_name),
            ],
            ADD_CHAT_USERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_chat_users),
            ],
            
            # УДАЛЕНИЕ ЧАТА
            DELETE_CHAT_SELECT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_chat_select),
            ],
            DELETE_CHAT_CONFIRM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_chat_confirm),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        
        # ВАЖНО: Добавьте эти параметры
        allow_reentry=True,
        per_chat=False,
        per_user=True,
        per_message=False
    )