from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_keyboards import get_main_keyboard
from auth_manager import auth_manager

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    print(f"🚀 Пользователь {user_id} запустил бота")
    
    # Гарантируем права администратора для суперадмина
    auth_manager.update_user_role_if_needed(user_id)
    
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Я бот для автоматизации отправки сообщений по расписанию.\n\n"
        "📋 Что я умею:\n"
        "• Создавать шаблоны сообщений\n"
        "• Настраивать автоматическую отправку\n"
        "• Управлять задачами и расписанием\n"
        "• Работать с несколькими Telegram чатами\n\n"
        "💡 Как начать:\n"
        "1. Создайте шаблон сообщения\n"
        "2. Настройте задачу с расписанием\n"
        "3. Выберите чат для отправки\n"
        "4. Бот будет отправлять сообщения автоматически!\n\n"
        "👇 Используйте кнопки ниже для навигации:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode=None
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user_id = update.effective_user.id
    
    help_text = (
        "ℹ️ СПРАВКА ПО БОТУ\n\n"
        "📋 ОСНОВНЫЕ РАЗДЕЛЫ:\n"
        "• Шаблоны - создание и управление шаблонами сообщений\n"
        "• Задачи - настройка автоматической отправки сообщений\n"
        "• Администрирование - управление пользователями и чатами\n\n"
        "⏰ РАБОТА С ЗАДАЧАМИ:\n"
        "1. Создайте шаблон с текстом и настройками\n"
        "2. Создайте задачу на основе шаблона\n"
        "3. Выберите Telegram чат для отправки\n"
        "4. Настройте время и периодичность\n"
        "5. Бот будет отправлять сообщения автоматически!\n\n"
        "🔧 КОМАНДЫ:\n"
        "• /start - перезапустить бота\n"
        "• /help - показать эту справку\n"
        "• /my_id - показать ваш ID\n"
        "• /now - показать текущее время\n"
        "• /cancel - отменить текущее действие\n\n"
        "💬 ПОДДЕРЖКА:\n"
        "Если возникли проблемы, обратитесь к администратору."
    )
    
    await update.message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode=None
    )

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ID пользователя и информацию о чате"""
    user = update.effective_user
    chat = update.effective_chat
    user_id = user.id
    chat_id = chat.id
    
    # Получаем информацию о правах доступа
    from auth_manager import auth_manager
    user_role = auth_manager.get_user_role(user_id)
    
    # Получаем доступные группы и чаты
    from authorized_users import get_user_access_groups, get_user_accessible_chats
    accessible_groups = get_user_access_groups(user_id)
    accessible_chats = get_user_accessible_chats(user_id)
    
    # Определяем тип чата
    chat_type = "личные сообщения"
    if chat.type == "group":
        chat_type = "группа"
    elif chat.type == "supergroup":
        chat_type = "супергруппа"
    elif chat.type == "channel":
        chat_type = "канал"
    
    message = "🆔 **ИНФОРМАЦИЯ ОБ ИДЕНТИФИКАТОРАХ**\n\n"
    
    message += "👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:**\n"
    message += f"• Ваш ID: `{user_id}`\n"
    message += f"• Username: @{user.username or 'не установлен'}\n"
    message += f"• Имя: {user.full_name}\n"
    message += f"• Должность: {user_role}\n\n"
    
    message += "💬 **ИНФОРМАЦИЯ О ЧАТЕ:**\n"
    message += f"• ID чата: `{chat_id}`\n"
    message += f"• Тип чата: {chat_type}\n"
    message += f"• Название: {chat.title or 'личные сообщения'}\n\n"
    
    message += "🔐 **ВАШИ ПРАВА ДОСТУПА:**\n"
    message += f"• Доступ к группам: {len(accessible_groups)}\n"
    message += f"• Доступ к чатам: {len(accessible_chats)}"
    
    # Добавляем список доступных чатов, если их немного
    if accessible_chats and len(accessible_chats) <= 10:
        message += "\n\n📋 **ВАШИ ДОСТУПНЫЕ ЧАТЫ:**\n"
        from user_chat_manager import user_chat_manager
        user_chats = user_chat_manager.get_user_chat_access(user_id)
        for i, chat_info in enumerate(user_chats, 1):
            message += f"{i}. {chat_info['chat_name']} (ID: `{chat_info['chat_id']}`)\n"
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(user_id)
    )

async def now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущее время"""
    from datetime import datetime
    import pytz
    
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_time = datetime.now(moscow_tz)
    
    await update.message.reply_text(
        f"⏰ Текущее время (МСК):\n"
        f"📅 {current_time.strftime('%d.%m.%Y')}\n"
        f"🕒 {current_time.strftime('%H:%M:%S')}",
        parse_mode=None,
        reply_markup=get_main_keyboard(update.effective_user.id)
    )

async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет главное меню"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "🔄 Меню обновлено",
        reply_markup=get_main_keyboard(user_id)
    )