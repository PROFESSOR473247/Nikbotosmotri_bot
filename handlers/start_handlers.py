from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_keyboards import get_main_keyboard, get_simple_keyboard
from config import REQUIRE_AUTHORIZATION
from authorized_users import is_authorized, is_admin
import datetime
import pytz

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    # Все пользователи получают полный доступ
    welcome_text = (
        f'🤖 БОТ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n'
        f'Текущее время: {current_time} (МСК)\n'
        f'ID чата: {chat_id}\n'
        f'Ваш ID: {user_id}\n\n'
        '🎉 ДОБРО ПОЖАЛОВАТЬ!\n\n'
        '🎹 Используйте кнопки меню для навигации:\n'
        '• 📋 Шаблоны - создание и управление рассылками\n'
        '• 📋 Задачи - создание и управление задачами\n'
        '• ℹ️ Помощь - справка по командам\n'
        '• 🆔 Мой ID - ваш идентификатор\n\n'
        '💡 Все данные сохраняются в базе и не теряются при перезапуске!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_simple_keyboard()
    )
    print(f"✅ Новый пользователь: {user_id} в чате {chat_id}")

async def update_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительно обновляет меню"""
    from telegram import ReplyKeyboardRemove
    import asyncio
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    print(f"🔄 Обновление меню для user_id: {user_id}")

    await update.message.reply_text(
        "🔄 Обновляю меню...",
        reply_markup=ReplyKeyboardRemove()
    )

    await asyncio.sleep(1)

    await update.message.reply_text(
        "✅ Меню обновлено!\n\n"
        "Теперь у вас есть доступ ко всем функциям бота:",
        reply_markup=get_simple_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам"""
    help_text = """
🤖 СПРАВКА ПО КОМАНДАМ БОТА:

🎹 ОСНОВНЫЕ ФУНКЦИИ:
/start - перезапустить бота
📋 Шаблоны - управление отложенными сообщениями
📋 Задачи - управление активными задачами
🆔 Мой ID - показать ваш идентификатор

📋 РАБОТА С ШАБЛОНАМИ:
• Создание шаблонов с текстом и изображениями
• Настройка времени и дней отправки
• Выбор периодичности (еженедельно, 2 в месяц, ежемесячно)
• Все шаблоны сохраняются в базе данных

📋 РАБОТА С ЗАДАЧАМИ:
• Создание задач на основе шаблонов
• Автоматическая отправка сообщений по расписанию
• Тестирование шаблонов перед созданием задач
• Просмотр статуса активных задач

💾 СОХРАНЕНИЕ ДАННЫХ:
Все созданные шаблоны и задачи сохраняются в PostgreSQL
и не теряются при перезапуске бота!

🔧 ТЕХНИЧЕСКИЕ КОМАНДЫ:
/help - эта справка
/now - текущее время
/update_menu - обновить меню

📞 Поддержка: обратитесь к администратору
"""

    await update.message.reply_text(help_text, reply_markup=get_simple_keyboard())

async def now(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает текущее время"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    await update.message.reply_text(
        f'🕒 Текущее время: {current_time} (МСК)',
        reply_markup=get_simple_keyboard()
    )

async def my_id(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Показывает user_id пользователя"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        f'🆔 Ваш ID: `{user_id}`\n'
        f'💬 ID чата: `{chat_id}`\n\n'
        f'✅ Вы имеете доступ ко всем функциям бота!\n'
        f'📋 Созданные шаблоны и задачи сохраняются в базе данных.',
        parse_mode='Markdown',
        reply_markup=get_simple_keyboard()
    )
    print(f"📋 Показан ID для user_id: {user_id}")