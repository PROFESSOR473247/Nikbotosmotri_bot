import logging
from telegram import Update
from telegram.ext import ContextTypes
from chat_context_manager import chat_context_manager

logger = logging.getLogger(__name__)

async def check_chat_context(update: Update, context: ContextTypes.DEFAULT_TYPE, handler_func):
    """
    Middleware для проверки контекста чата
    Перенаправляет пользователей в личные сообщения для настройки
    """
    if not update or not update.message:
        return await handler_func(update, context)
    
    # Проверяем тип чата
    if chat_context_manager.is_group_chat(update):
        user_id = update.effective_user.id
        
        # Разрешаем только команды /start, /help, /my_id в группах
        allowed_commands = ['/start', '/help', '/my_id', '/now']
        
        if update.message.text and any(update.message.text.startswith(cmd) for cmd in allowed_commands):
            return await handler_func(update, context)
        else:
            # Перенаправляем в личные сообщения для настройки
            bot_username = context.bot.username
            await update.message.reply_text(
                "🤖 **Настройка бота**\n\n"
                "⚠️ Для настройки шаблонов и задач перейдите в личные сообщения с ботом:\n"
                f"👉 [Нажмите здесь](https://t.me/{bot_username})",
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            return
    
    # В личных сообщениях разрешаем все
    return await handler_func(update, context)
