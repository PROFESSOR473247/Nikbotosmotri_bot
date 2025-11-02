# -*- coding: utf-8 -*-
import logging
import asyncio
import os
import json
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler
)
from telegram.error import BadRequest
from config import BOT_TOKEN
from database import is_authorized, is_admin, get_user_role, get_user_accessible_groups, ensure_admin_user
from task_manager import task_manager
from menu_manager import get_main_menu, get_guest_keyboard
from template_manager import template_manager
from user_manager import user_manager
from group_manager import group_manager
import datetime
import pytz

print("🔄 Инициализация системы...")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def authorization_required(func):
    """Декоратор для проверки авторизации"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ Недостаточно прав для этого действия", show_alert=True)
            else:
                await update.message.reply_text(
                    "❌ НЕДОСТАТОЧНО ПРАВ\n\nДля доступа к боту свяжитесь с администратором @ProfeSSor471",
                    reply_markup=get_guest_keyboard()
                )
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

def admin_required(func):
    """Декоратор для проверки прав администратора"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ Только для администратора", show_alert=True)
            else:
                await update.message.reply_text("❌ Только для администратора")
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Если бот в группе - просто игнорируем
    if update.effective_chat.type in ["group", "supergroup"]:
        return
    
    # Личный чат
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n\n'
            f'👋 Добрый день! Данный бот предназначен для создания отложенных сообщений в Telegram-группах и каналах.\n\n'
            f'🆔 Ваш ID: `{user_id}`\n'
            f'🕒 Текущее время: {current_time} (Москва)\n\n'
            f'📋 Для начала работы с ботом нажмите кнопку «🆔 Получить ID» и сообщите его @ProfeSSor471.\n'
            f'👨‍💼 Он внесёт Вас в список пользователей и объяснит дальнейшую работу с ботом.\n\n'
            f'✨ Приятного пользования!'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_guest_keyboard(),
            parse_mode='Markdown'
        )
        return

    user_role = get_user_role(user_id)
    welcome_text = (
        f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n\n'
        f'🕒 Текущее время: {current_time} (Москва)\n'
        f'🆔 Ваш ID: `{user_id}`\n'
        f'👤 Роль: {user_role}\n\n'
        f'📝 Используйте меню для навигации!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(user_id),
        parse_mode='Markdown'
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Пропускаем обработку в группах
    if update.effective_chat.type in ["group", "supergroup"]:
        return
    
    # Если пользователь тестирует другую роль
    if context.user_data.get('testing_role'):
        if text == "👑 Назад к админ":
            context.user_data.pop('testing_role', None)
            await update.message.reply_text(
                "✅ Возврат к роли администратора",
                reply_markup=get_main_menu(user_id)
            )
            return
        # Обработка для тестовой роли
        await handle_testing_role_text(update, context)
        return
    
    # Обработка кнопок главного меню
    if text == "📋 Задачи":
        await task_manager.show_tasks_menu(update, context)
    elif text == "📁 Шаблоны":
        await template_manager.show_templates_menu(update, context)
    elif text == "👥 Пользователи":
        await user_manager.show_users_menu(update, context)
    elif text == "🏘️ Группы":
        await group_manager.show_groups_menu(update, context)
    elif text == "ℹ️ Еще":
        await show_more_menu(update, context)
    elif text == "🔙 Назад в главное меню":
        await update.message.reply_text("📋 Главное меню", reply_markup=get_main_menu(user_id))
    elif text == "🆔 Получить ID":
        await my_id(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "❓ Неизвестная команда",
            reply_markup=get_main_menu(user_id) if is_authorized(user_id) else get_guest_keyboard()
        )

async def handle_testing_role_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста при тестировании роли"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Обработка для тестовой роли (ограниченный функционал)
    if text == "📋 Задачи":
        await task_manager.show_tasks_menu(update, context)
    elif text == "📁 Шаблоны":
        await template_manager.show_templates_menu(update, context)
    elif text == "🏘️ Группы":
        await group_manager.show_groups_menu(update, context)
    elif text == "ℹ️ Еще":
        await show_more_menu(update, context)
    elif text == "🔙 Назад в главное меню":
        await update.message.reply_text("📋 Главное меню", reply_markup=get_main_menu(user_id))
    elif text == "🆔 Получить ID":
        await my_id(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "❓ Неизвестная команда",
            reply_markup=get_main_menu(user_id)
        )

@authorization_required
async def show_more_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню Еще"""
    user_id = update.effective_user.id
    from menu_manager import get_more_menu
    await update.message.reply_text("ℹ️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ", reply_markup=get_more_menu(user_id))

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать ID пользователя"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_authorized(user_id):
        user_role = get_user_role(user_id)
        reply_markup = get_main_menu(user_id)
        additional_text = f"👤 Ваша роль: {user_role}"
    else:
        reply_markup = get_guest_keyboard()
        additional_text = "❌ Вы не авторизованы. Сообщите ID администратору"

    await update.message.reply_text(
        f'🆔 Ваш ID: `{user_id}`\n'
        f'💬 ID чата: `{chat_id}`\n\n'
        f'{additional_text}',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    user_id = update.effective_user.id

    help_text = """
🤖 СПРАВКА ПО КОМАНДАМ:

📋 ДОСТУПНО ВСЕМ:
/start - перезапуск бота
/my_id - показать ваш ID
/help - эта справка

🔐 Для доступа к полному функционалу свяжитесь с администратором @ProfeSSor471
"""

    await update.message.reply_text(
        help_text,
        reply_markup=get_main_menu(user_id) if is_authorized(user_id) else get_guest_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if not is_authorized(user_id):
        await query.edit_message_text("❌ Недостаточно прав")
        return
    
    # Обработка кнопок задач
    if data.startswith('task_'):
        await task_manager.handle_button(update, context)
    # Обработка кнопок шаблонов
    elif data.startswith('template_'):
        await template_manager.handle_button(update, context)
    # Обработка кнопок пользователей
    elif data.startswith('user_'):
        await user_manager.handle_button(update, context)
    # Обработка кнопок групп
    elif data.startswith('group_'):
        await group_manager.handle_button(update, context)
    # Обработка тестирования ролей
    elif data.startswith('test_role_'):
        await handle_test_role(update, context)

async def handle_test_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка тестирования ролей"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("❌ Только для администратора", show_alert=True)
        return
    
    role_key = data.replace('test_role_', '')
    
    # Сохраняем тестовую роль
    context.user_data['testing_role'] = role_key
    context.user_data['original_role'] = get_user_role(user_id)
    
    await query.edit_message_text(
        f"🎭 Теперь вы тестируете роль: {role_key}\n\n"
        f"📋 Доступны только функции этой роли.\n"
        f"👑 Для возврата к роли администратора используйте кнопку в главном меню.",
        reply_markup=get_main_menu(user_id)
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена любого диалога"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "❌ Операция отменена",
        reply_markup=get_main_menu(user_id)
    )
    return ConversationHandler.END

def setup_handlers(application):
    """Настройка обработчиков"""
    from conversation_states import *
    from template_manager import template_manager
    from user_manager import user_manager
    from group_manager import group_manager
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("cancel", cancel))

    # Обработчики кнопок главного меню
    application.add_handler(MessageHandler(filters.Regex("^📋 Задачи$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📁 Шаблоны$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^👥 Пользователи$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🏘️ Группы$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ Еще$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Назад в главное меню$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Получить ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^👑 Назад к админ$"), handle_text))

    # Добавляем ConversationHandler из менеджеров
    application.add_handler(template_manager.get_conversation_handler())
    application.add_handler(user_manager.get_conversation_handler())
    application.add_handler(group_manager.get_conversation_handler())
    application.add_handler(task_manager.get_conversation_handler())

    # Обработчик inline-кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обработчик всех текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

async def post_init(application):
    """Функция инициализации после запуска бота"""
    print("🔄 Восстановление активных задач...")
    await task_manager.restore_tasks(application)
    
    # Гарантируем наличие администратора
    ensure_admin_user()

def main():
    """Основная функция запуска бота"""
    print("🚀 Запуск бота...")
    
    # Создаем приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Настраиваем обработчики
    setup_handlers(application)

    print("✅ Бот запущен и готов к работе!")
    print("🤖 Бот работает в режиме polling...")
    
    # Запускаем polling с обработкой ошибок для Render
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False  # Важно для Render
        )
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        import time
        time.sleep(10)
        # Рекурсивный перезапуск
        main()

if __name__ == '__main__':
    # Запускаем бота
    main()
