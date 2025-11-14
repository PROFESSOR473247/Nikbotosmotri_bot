from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from keyboards.main_keyboards import get_main_keyboard, get_simple_keyboard
from auth_manager import auth_manager

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для навигации по меню"""
    text = update.message.text
    user_id = update.effective_user.id

    print(f"🔤 Обработка текста: '{text}' от user_id: {user_id}")

    # Гарантируем права администратора для суперадмина при каждом действии
    auth_manager.update_user_role_if_needed(user_id)

    if text == "📋 Шаблоны":
        from handlers.template_handlers import templates_main
        return await templates_main(update, context)

    elif text == "📋 Задачи":
        from handlers.task_handlers import tasks_main
        return await tasks_main(update, context)

    elif text == "⚙️ Администрирование":
        from handlers.admin_handlers import admin_main
        return await admin_main(update, context)

    elif text == "ℹ️ Помощь":
        from handlers.start_handlers import help_command
        await help_command(update, context)
        return ConversationHandler.END

    elif text == "🆔 Мой ID":
        from handlers.start_handlers import my_id
        await my_id(update, context)
        return ConversationHandler.END

    elif text == "🔙 Главное меню":
        # Очищаем временные данные
        context.user_data.clear()
        
        await update.message.reply_text(
            "🔙 Возврат в главное меню",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "❌ Неизвестная команда\n"
            "Используйте кнопки меню или /help для справки",
            reply_markup=get_main_keyboard(user_id)
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любого действия"""
    user_id = update.effective_user.id
    
    # Гарантируем права администратора для суперадмина
    auth_manager.update_user_role_if_needed(user_id)
    
    # Очищаем временные данные
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard(user_id)
    )
    return ConversationHandler.END