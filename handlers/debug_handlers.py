"""
Обработчики для отладки
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from template_debug import debug_list_all_templates, debug_delete_template

logger = logging.getLogger(__name__)

async def debug_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для отладки шаблонов"""
    user_id = update.effective_user.id
    if user_id != 812934047:  # Ваш ID суперадмина
        await update.message.reply_text("❌ Нет доступа")
        return
    
    debug_list_all_templates()
    await update.message.reply_text("✅ Информация о шаблонах выведена в логи")

async def debug_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для тестирования удаления шаблона"""
    user_id = update.effective_user.id
    if user_id != 812934047:
        await update.message.reply_text("❌ Нет доступа")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажите ID шаблона: /debug_delete <template_id>")
        return
    
    template_id = context.args[0]
    logger.info(f"🧪 Тестирование удаления шаблона {template_id}")
    
    success = debug_delete_template(template_id)
    
    if success:
        await update.message.reply_text(f"✅ Тестовое удаление шаблона {template_id} прошло успешно")
    else:
        await update.message.reply_text(f"❌ Тестовое удаление шаблона {template_id} не удалось")

def get_debug_handlers():
    """Возвращает обработчики для отладки"""
    return [
        CommandHandler("debug_templates", debug_templates),
        CommandHandler("debug_delete", debug_delete)
    ]