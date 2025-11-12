from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from keyboards.main_keyboards import get_simple_keyboard
from config import REQUIRE_AUTHORIZATION
from authorized_users import is_admin

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для навигации по меню"""
    text = update.message.text
    user_id = update.effective_user.id

    print(f"🔤 Обработка текста: '{text}' от user_id: {user_id}")

    if text == "📋 Шаблоны":
        from handlers.template_handlers import templates_main
        return await templates_main(update, context)

    elif text == "📋 Задачи":  # Добавили обработку кнопки Задач
        from handlers.task_handlers import tasks_main
        return await tasks_main(update, context)

    elif text == "ℹ️ Помощь":
        from handlers.start_handlers import help_command
        await help_command(update, context)

    elif text == "🆔 Мой ID":
        from handlers.start_handlers import my_id
        await my_id(update, context)

    elif text == "🔙 Главное меню":
        await update.message.reply_text(
            "🔙 Возврат в главное меню",
            reply_markup=get_simple_keyboard()
        )
        return ConversationHandler.END

    elif text == "👥 Пользователи" and is_admin(user_id):
        from keyboards.user_management_keyboards import get_user_management_keyboard
        await update.message.reply_text(
            "👥 Управление пользователями\n\n"
            "Выберите действие:",
            reply_markup=get_user_management_keyboard()
        )

    elif text == "⚙️ Настройки" and is_admin(user_id):
        await update.message.reply_text(
            "⚙️ Настройки системы\n\n"
            "Административные функции:",
            reply_markup=get_simple_keyboard()
        )

    elif text == "🆔 Получить ID":
        from handlers.start_handlers import my_id
        await my_id(update, context)

    elif text == "📋 Справка":
        from handlers.start_handlers import help_command
        await help_command(update, context)

    else:
        await update.message.reply_text(
            "❌ Неизвестная команда\n"
            "Используйте кнопки меню или /help для справки",
            reply_markup=get_simple_keyboard()
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любого действия"""
    user_id = update.effective_user.id
    
    # Очищаем временные данные
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_simple_keyboard()
    )
    return ConversationHandler.END