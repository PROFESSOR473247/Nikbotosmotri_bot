from telegram import Update
from telegram.ext import ContextTypes
from keyboards.main_keyboards import get_main_keyboard, get_simple_keyboard
from auth_manager import auth_manager
import datetime
import pytz

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    # Гарантируем права администратора для суперадмина
    auth_manager.update_user_role_if_needed(user_id)
    
    # Проверяем тип чата
    from chat_context_manager import chat_context_manager
    if chat_context_manager.is_private_chat(update):
        chat_type = "💬 Личные сообщения"
        welcome_note = "✅ Вся настройка происходит здесь в личных сообщениях\n📢 Сообщения будут отправляться в выбранные Telegram чаты"
    else:
        chat_type = f"👥 Групповой чат: {update.effective_chat.title}"
        welcome_note = "⚠️ Для настройки бота перейдите в личные сообщения с ботом\n📢 Здесь будут приходить только сообщения из задач"

    welcome_text = (
        f'🤖 БОТ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n'
        f'Текущее время: {current_time} (МСК)\n'
        f'Тип чата: {chat_type}\n'
        f'Ваш ID: {user_id}\n\n'
        f'{welcome_note}\n\n'
        '🎹 Используйте кнопки меню для навигации:\n'
        '• 📋 Шаблоны - создание и управление рассылками\n'
        '• 📋 Задачи - создание и управление задачами\n'
        '• ℹ️ Помощь - справка по командам\n'
        '• 🆔 Мой ID - ваш идентификатор\n\n'
        '💡 Все данные сохраняются в базе и не теряются при перезапуске!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_simple_keyboard(user_id)
    )
    print(f"✅ Пользователь: {user_id} в чате {chat_id} ({chat_type})")
