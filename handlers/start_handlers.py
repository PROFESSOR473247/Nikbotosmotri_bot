from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_keyboards import get_main_keyboard, get_unauthorized_keyboard
from authorized_users import is_authorized, is_admin
import datetime
import pytz

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 БОТ С МНОГОУРОВНЕВЫМ МЕНЮ\n'
            f'Текущее время: {current_time} (МСК)\n'
            f'ID чата: {chat_id}\n'
            f'Ваш ID: {user_id}\n\n'
            '❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n'
            'Для доступа к функциям бота обратитесь к администратору\n\n'
            '🎹 Доступные функции:\n'
            '• 🆔 Получить ID - узнать ваш идентификатор\n'
            '• /help - справка по командам'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_unauthorized_keyboard()
        )
        print(f"🚫 Неавторизованный доступ от user_id: {user_id}")
        return

    welcome_text = (
        f'🤖 БОТ С МНОГОУРОВНЕВЫМ МЕНЮ\n'
        f'Текущее время: {current_time} (МСК)\n'
        f'ID чата: {chat_id}\n'
        f'Ваш ID: {user_id}\n\n'
        '🎹 Используйте кнопки меню для навигации!\n\n'
        '💡 Также доступны текстовые команды:\n'
        '/help - справка по командам\n'
        '/update_menu - обновить меню\n'
        '/my_id - показать ваш ID'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )
    print(f"✅ Отправлено главное меню в чат {chat_id} для user_id: {user_id}")

async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно обновляет меню"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    print(f"🔄 Принудительное обновление на новое меню для чата {chat_id}, user_id: {user_id}")

    await update.message.reply_text(
        "🔄 Удаляю старое меню...",
        reply_markup=ReplyKeyboardRemove()
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "✅ Новое меню загружено!\n\n"
        "🎹 Теперь у вас:\n"
        "• 📋 Шаблоны - управление рассылками\n"
        "• 🧪 Тестирование - тестовые отправки\n"
        "• ⚙️ ЕЩЕ - дополнительные функции",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам"""
    user_id = update.effective_user.id

    help_text = """
🤖 СПРАВКА ПО КОМАНДАМ:

🎹 ДОСТУПНЫЕ ВСЕМ:
/start - перезапустить бота
/my_id - показать ваш ID (для получения доступа)
/help - эта справка

🎹 ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ:
📋 Шаблоны - управление основными рассылками
🧪 Тестирование - тестовые отправки
⚙️ ЕЩЕ - дополнительные функции
/update_menu - обновить меню
/status - статус шаблонов
/now - текущее время

🔐 Для получения доступа обратитесь к администратору
"""

    if is_authorized(user_id):
        await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(help_text, reply_markup=get_unauthorized_keyboard())

async def now(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает текущее время"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    await update.message.reply_text(
        f'🕒 Текущее время: {current_time} (МСК)',
        reply_markup=get_main_keyboard()
    )

async def my_id(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает user_id пользователя"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_authorized(user_id):
        reply_markup = get_main_keyboard()
        additional_text = "✅ Вы авторизованы и имеете доступ ко всем функциям бота"
    else:
        reply_markup = get_unauthorized_keyboard()
        additional_text = "❌ Вы не авторизованы. Обратитесь к администратору для получения доступа"

    await update.message.reply_text(
        f'🆔 Ваш ID: `{user_id}`\n'
        f'💬 ID чата: `{chat_id}`\n\n'
        f'{additional_text}',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    print(f"📋 Показан ID для user_id: {user_id}")
