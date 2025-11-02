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
from authorized_users import is_authorized, is_admin, get_user_role
from database import init_database, load_tasks, save_tasks, get_user_accessible_groups
from task_manager import TaskManager
from menu_manager import get_main_menu, get_guest_keyboard
import datetime
import pytz

print("🔄 Инициализация системы...")
init_database()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный менеджер задач
task_manager = TaskManager()

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
            f'Ваш ID: `{user_id}`\n'
            f'Текущее время: {current_time} (Москва)\n\n'
            f'❌ НЕДОСТАТОЧНО ПРАВ\n\n'
            f'Для доступа нажмите "🆔 Получить ID" и сообщите его @ProfeSSor471'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_guest_keyboard(),
            parse_mode='Markdown'
        )
        return

    user_role = get_user_role(user_id)
    welcome_text = (
        f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n'
        f'Текущее время: {current_time} (Москва)\n'
        f'Ваш ID: {user_id}\n'
        f'Роль: {user_role}\n\n'
        f'Используйте меню для навигации!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(user_id)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Пропускаем обработку в группах
    if update.effective_chat.type in ["group", "supergroup"]:
        return
    
    # Обработка кнопок главного меню
    if text == "📋 Задачи":
        await task_manager.show_tasks_menu(update, context)
    elif text == "📁 Шаблоны":
        await task_manager.show_templates_menu(update, context)
    elif text == "👥 Пользователи":
        await show_users_menu(update, context)
    elif text == "🏘️ Группы":
        await show_groups_menu(update, context)
    elif text == "ℹ️ Еще":
        await show_more_menu(update, context)
    elif text == "🔙 Назад в главное меню":
        await update.message.reply_text("Главное меню", reply_markup=get_main_menu(user_id))
    elif text == "🆔 Получить ID":
        await my_id(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "Неизвестная команда",
            reply_markup=get_main_menu(user_id) if is_authorized(user_id) else get_guest_keyboard()
        )

@authorization_required
async def show_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню пользователей"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Только для администратора")
        return
    
    from menu_manager import get_users_menu
    await update.message.reply_text("👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ", reply_markup=get_users_menu())

@authorization_required
async def show_groups_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню групп"""
    user_id = update.effective_user.id
    from menu_manager import get_groups_menu
    await update.message.reply_text("🏘️ УПРАВЛЕНИЕ ГРУППАМИ", reply_markup=get_groups_menu(user_id))

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
        additional_text = f"Ваша роль: {user_role}"
    else:
        reply_markup = get_guest_keyboard()
        additional_text = "Вы не авторизованы. Сообщите ID администратору"

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

ДОСТУПНО ВСЕМ:
/start - перезапуск бота
/my_id - показать ваш ID
/help - эта справка

Для доступа свяжитесь с администратором @ProfeSSor471
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
        await task_manager.handle_button(update, context)
    # Обработка кнопок групп
    elif data.startswith('group_'):
        await task_manager.handle_button(update, context)

def setup_handlers(application):
    """Настройка обработчиков"""
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))

    # Обработчики кнопок главного меню
    application.add_handler(MessageHandler(filters.Regex("^📋 Задачи$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📁 Шаблоны$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^👥 Пользователи$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🏘️ Группы$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ Еще$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Назад в главное меню$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Получить ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), handle_text))

    # Обработчик inline-кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    # Обработчик всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

async def main():
    """Основная асинхронная функция запуска"""
    print("🚀 Запуск бота...")
    
    # Создаем приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Настраиваем обработчики
    setup_handlers(application)

    # Восстанавливаем активные задачи
    await task_manager.restore_tasks(application)

    print("✅ Бот запущен и готов к работе!")
    print("🤖 Бот работает в режиме polling...")
    
    # Запускаем polling
    await application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    asyncio.run(main())
