"""
Обработчики для отладки
"""

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from template_debug import debug_list_all_templates

async def debug_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для отладки шаблонов"""
    user_id = update.effective_user.id
    if user_id != 812934047:  # Ваш ID суперадмина
        await update.message.reply_text("❌ Нет доступа")
        return
    
    debug_list_all_templates()
    await update.message.reply_text("✅ Информация о шаблонах выведена в логи")

def get_debug_handlers():
    """Возвращает обработчики для отладки"""
    return [
        CommandHandler("debug_templates", debug_templates)
    ]
