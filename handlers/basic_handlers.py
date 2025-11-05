from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from keyboards.main_keyboards import get_main_keyboard, get_unauthorized_keyboard
from authorized_users import is_authorized, is_admin

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения для навигации по меню"""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "📋 Шаблоны":
        from handlers.template_handlers import templates_main
        return await templates_main(update, context)

    elif text == "🧪 Тестирование":
        from keyboards.testing_keyboards import get_testing_keyboard
        await update.message.reply_text(
            "🧪 ТЕСТИРОВАНИЕ ШАБЛОНОВ\n\n"
            "Тестовые отправки работают так же как основные,\n"
            "но отправляются через 10 секунд после активации\n"
            "и выполняются только один раз",
            reply_markup=get_testing_keyboard()
        )

    elif text == "⚙️ ЕЩЕ":
        from keyboards.more_keyboards import get_more_keyboard
        await update.message.reply_text(
            "⚙️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ",
            reply_markup=get_more_keyboard(user_id)
        )

    elif text == "🔙 Главное меню":
        await update.message.reply_text(
            "🔙 Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    elif text == "📊 Статус команд":
        await update.message.reply_text(
            "⚠️ Статус временно недоступен",
            reply_markup=get_main_keyboard()
        )

    elif text == "🕒 Текущее время":
        from handlers.start_handlers import now
        await now(update, context)

    elif text == "🆔 Мой ID":
        from handlers.start_handlers import my_id
        await my_id(update, context)

    elif text == "👥 Управление пользователями" and is_admin(user_id):
        from keyboards.user_management_keyboards import get_user_management_keyboard
        await update.message.reply_text(
            "👥 Управление пользователями\n\n"
            "Выберите действие:",
            reply_markup=get_user_management_keyboard()
        )

    elif text == "🔙 Назад к ЕЩЕ":
        from keyboards.more_keyboards import get_more_keyboard
        await update.message.reply_text(
            "🔙 Возврат к дополнительным функциям",
            reply_markup=get_more_keyboard(user_id)
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
            reply_markup=get_main_keyboard() if is_authorized(user_id) else get_unauthorized_keyboard()
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любого действия"""
    user_id = update.effective_user.id
    
    # Очищаем временные данные
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END
