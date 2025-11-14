from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_keyboards import get_main_keyboard, get_simple_keyboard
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
        "📋 **Что я умею:**\n"
        "• Создавать шаблоны сообщений\n"
        "• Настраивать автоматическую отправку\n"
        "• Управлять задачами и расписанием\n"
        "• Работать с несколькими Telegram чатами\n\n"
        "💡 **Как начать:**\n"
        "1. Создайте шаблон сообщения\n"
        "2. Настройте задачу с расписанием\n"
        "3. Выберите чат для отправки\n"
        "4. Бот будет отправлять сообщения автоматически!\n\n"
        "👇 Используйте кнопки ниже для навигации:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user_id = update.effective_user.id
    
    help_text = (
        "ℹ️ **Справка по боту**\n\n"
        "📋 **Основные разделы:**\n"
        "• *Шаблоны* - создание и управление шаблонами сообщений\n"
        "• *Задачи* - настройка автоматической отправки сообщений\n"
        "• *Администрирование* - управление пользователями и чатами\n\n"
        "⏰ **Работа с задачами:**\n"
        "1. Создайте шаблон с текстом и настройками\n"
        "2. Создайте задачу на основе шаблона\n"
        "3. Выберите Telegram чат для отправки\n"
        "4. Настройте время и периодичность\n"
        "5. Бот будет отправлять сообщения автоматически!\n\n"
        "🔧 **Команды:**\n"
        "• /start - перезапустить бота\n"
        "• /help - показать эту справку\n"
        "• /my_id - показать ваш ID\n"
        "• /now - показать текущее время\n"
        "• /cancel - отменить текущее действие\n\n"
        "💬 **Поддержка:**\n"
        "Если возникли проблемы, обратитесь к администратору."
    )
    
    await update.message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ID пользователя"""
    user = update.effective_user
    user_id = user.id
    
    await update.message.reply_text(
        f"🆔 **Ваш ID:** `{user_id}`\n"
        f"👤 **Username:** @{user.username or 'не установлен'}\n"
        f"📛 **Имя:** {user.full_name}",
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
        f"⏰ **Текущее время (МСК):**\n"
        f"📅 {current_time.strftime('%d.%m.%Y')}\n"
        f"🕒 {current_time.strftime('%H:%M:%S')}",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard(update.effective_user.id)
    )

async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновляет главное меню"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "🔄 Меню обновлено",
        reply_markup=get_main_key
