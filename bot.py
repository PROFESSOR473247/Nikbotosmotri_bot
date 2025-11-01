# -*- coding: utf-8 -*-
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    JobQueue
)
from config import BOT_TOKEN
from authorized_users import is_authorized, is_admin, get_user_role, get_user_access_level
from database import init_database, get_user_accessible_groups, load_groups, load_templates
from task_manager import task_manager
from group_manager import group_manager
from menu_manager import *
from conversation_handlers import add_user_conversation, create_template_conversation
import datetime
import pytz
from datetime import timedelta
import sys
import os
import requests
import threading
import time

# Initialize database on startup
init_database()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Authorization decorator
def authorization_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            await update.message.reply_text(
                "❌ НЕДОСТАТОЧНО ПРАВ\n\n"
                "Свяжитесь с администратором для доступа к боту",
                reply_markup=get_unauthorized_keyboard()
            )
            print(f"Unauthorized access from user_id: {user_id} to function: {func.__name__}")
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

# Role-based access decorator
def role_required(required_role):
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            user_role = get_user_role(user_id)
            role_levels = {
                "admin": 4,
                "руководитель": 3,
                "водитель": 2,
                "гость": 1
            }
            user_level = role_levels.get(user_role, 1)
            required_level = role_levels.get(required_role, 1)
            
            if user_level < required_level:
                await update.message.reply_text(
                    f"❌ НЕДОСТАТОЧНО ПРАВ\n\n"
                    f"Эта функция доступна только для {required_role} и выше",
                    reply_markup=get_main_menu(user_id)
                )
                return None
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # If bot is in group - update group information
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        await group_manager.update_group_info(update, context)
        return
    
    # Personal chat
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n\n'
            f'Привет! Этот бот предназначен для создания отложенных сообщений в Telegram группах и каналах.\n\n'
            f'Ваш ID: `{user_id}`\n'
            f'Текущее время: {current_time} (Москва)\n\n'
            f'❌ НЕДОСТАТОЧНО ПРАВ\n\n'
            f'Для начала работы с ботом нажмите "🆔 Получить ID" и сообщите его @ProfeSSor471. '
            f'Он внесёт вас в список пользователей и объяснит дальнейшую работу с ботом.\n\n'
            f'Приятного пользования!'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_unauthorized_keyboard(),
            parse_mode='Markdown'
        )
        return

    user_role = get_user_role(user_id)
    welcome_text = (
        f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n'
        f'Текущее время: {current_time} (Москва)\n'
        f'Ваш ID: {user_id}\n'
        f'Ваша роль: {user_role}\n\n'
        f'Используйте кнопки меню для навигации!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu(user_id)
    )

@authorization_required
async def handle_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for Templates button"""
    user_id = update.effective_user.id
    user_role = get_user_role(user_id)
    
    # Check if user has permission to manage templates
    if user_role in ["гость", "водитель"]:
        await update.message.reply_text(
            "❌ НЕДОСТАТОЧНО ПРАВ\n\n"
            "Управление шаблонами доступно только для администраторов и руководителей",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    await update.message.reply_text(
        "📁 УПРАВЛЕНИЕ ШАБЛОНАМИ\n\n"
        "Выберите действие:",
        reply_markup=get_templates_menu()
    )

@authorization_required 
async def handle_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for Tasks button"""
    user_id = update.effective_user.id
    
    accessible_groups = get_user_accessible_groups(user_id)
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа к группам\n\n"
            "Обратитесь к администратору для предоставления доступа",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    await update.message.reply_text(
        "📋 УПРАВЛЕНИЕ ЗАДАЧАМИ\n\n"
        "Выберите действие:",
        reply_markup=get_tasks_menu()
    )

@authorization_required
@role_required("admin")
async def handle_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle users management - admin only"""
    await update.message.reply_text(
        "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ\n\n"
        "Выберите действие:",
        reply_markup=get_users_menu()
    )

@authorization_required
async def handle_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle groups management"""
    user_id = update.effective_user.id
    user_role = get_user_role(user_id)
    
    if user_role == "гость":
        await update.message.reply_text(
            "❌ НЕДОСТАТОЧНО ПРАВ\n\n"
            "Управление группами доступно только для администраторов и руководителей",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    await update.message.reply_text(
        "🏘️ УПРАВЛЕНИЕ ГРУППАМИ\n\n"
        "Выберите действие:",
        reply_markup=get_groups_menu(user_id)
    )

@authorization_required
async def handle_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle more options"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "ℹ️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ\n\n"
        "Выберите действие:",
        reply_markup=get_more_menu()
    )

@authorization_required
async def handle_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user task status"""
    user_id = update.effective_user.id
    user_tasks = task_manager.get_user_tasks(user_id)
    
    if not user_tasks:
        status_text = "📊 СТАТУС ЗАДАЧ\n\nНет активных задач"
    else:
        status_text = "📊 ВАШИ АКТИВНЫЕ ЗАДАЧИ:\n\n"
        for task_id, task_data in user_tasks.items():
            groups_data = load_groups()
            group_info = groups_data["groups"].get(str(task_data.get("group_id", "")), {})
            group_name = group_info.get('title', f'Group {task_data.get("group_id", "")}')
            
            templates_data = load_templates()
            template_name = task_data.get("template_name", "Unknown")
            template_text = templates_data.get("templates", {}).get(template_name, {}).get("text", "Template")[:50]
            
            status_text += f"📝 Шаблон: {template_text}...\n"
            status_text += f"   🏘️ Группа: {group_name}\n"
            status_text += f"   🕒 Создана: {task_data.get('created_at', '')[:16]}\n"
            status_text += f"   🔧 Тип: {'Основная' if task_data.get('task_type') == 'main' else 'Тестовая'}\n\n"
    
    await update.message.reply_text(
        status_text,
        reply_markup=get_main_menu(user_id)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Skip processing if it's a group
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        return
    
    # Main menu handlers
    if text == "📋 Задачи":
        await handle_tasks(update, context)
    elif text == "📁 Шаблоны":
        await handle_templates(update, context)
    elif text == "👥 Пользователи":
        await handle_users(update, context)
    elif text == "🏘️ Группы":
        await handle_groups(update, context)
    elif text == "ℹ️ Еще":
        await handle_more(update, context)
    elif text == "🔙 Назад в главное меню":
        await update.message.reply_text(
            "Возврат в главное меню",
            reply_markup=get_main_menu(user_id)
        )
    elif text == "🆔 Получить ID":
        await my_id(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    elif text == "📊 Статус задач":
        await handle_task_status(update, context)
    elif text == "🕒 Текущее время":
        await now(update, context)
    elif text == "🆔 Мой ID":
        await my_id(update, context)
    else:
        await update.message.reply_text(
            "Неизвестная команда",
            reply_markup=get_main_menu(user_id) if is_authorized(user_id) else get_unauthorized_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help - available to everyone"""
    user_id = update.effective_user.id

    help_text = """
🤖 СПРАВКА ПО КОМАНДАМ БОТА:

ДОСТУПНО ВСЕМ:
/start - перезапустить бота
/my_id - показать ваш ID (для доступа)
/help - эта справка

ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ:
📋 Задачи - управление задачами
📁 Шаблоны - управление шаблонами (админы/руководители)
👥 Пользователи - управление пользователями (только админы)
🏘️ Группы - управление группами (админы/руководители)
ℹ️ Еще - дополнительные функции

Для доступа свяжитесь с администратором
"""

    if is_authorized(user_id):
        await update.message.reply_text(help_text, reply_markup=get_main_menu(user_id))
    else:
        await update.message.reply_text(help_text, reply_markup=get_unauthorized_keyboard())

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user_id - available to everyone"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if is_authorized(user_id):
        reply_markup = get_main_menu(user_id)
        additional_text = "Вы авторизованы и имеете доступ ко всем функциям бота"
    else:
        reply_markup = get_unauthorized_keyboard()
        additional_text = "Вы не авторизованы. Свяжитесь с администратором для доступа"

    await update.message.reply_text(
        f'🆔 Ваш ID: `{user_id}`\n'
        f'💬 ID чата: `{chat_id}`\n\n'
        f'{additional_text}',
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current time"""
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")
    user_id = update.effective_user.id
    await update.message.reply_text(
        f'🕒 Текущее время: {current_time} (Москва)',
        reply_markup=get_main_menu(user_id)
    )

# Keep alive function for Render
def keep_alive():
    """Periodically ping to keep app awake"""
    def ping():
        while True:
            try:
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    response = requests.get(render_url, timeout=10)
                    print(f"Ping sent: {response.status_code}")
                else:
                    print("Keep-alive: bot active")
            except Exception as e:
                print(f"Ping error: {e}")
            time.sleep(300)  # Ping every 5 minutes
    
    ping_thread = threading.Thread(target=ping, daemon=True)
    ping_thread.start()
    print("Keep-alive system started")

def main():
    """Start bot"""
    print("Starting bot...")
    
    # Initialize database
    init_database()

    # Start keep-alive system
    keep_alive()

    # Create application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(JobQueue())
        .build()
    )

    # Restore tasks on startup
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(task_manager.restore_tasks(application))

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))

    # Conversation handlers
    application.add_handler(add_user_conversation)
    application.add_handler(create_template_conversation)

    # Main menu button handlers
    application.add_handler(MessageHandler(filters.Regex("^📋 Задачи$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📁 Шаблоны$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^👥 Пользователи$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🏘️ Группы$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ Еще$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Назад в главное меню$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Получить ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^❓ Помощь$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📊 Статус задач$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🕒 Текущее время$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Мой ID$"), handle_text))

    # Handler for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Handler for updating group information
    application.add_handler(MessageHandler(filters.ALL, group_manager.update_group_info))

    print("Bot started and ready!")
    
    # Start polling
    application.run_polling()

if __name__ == '__main__':
    main()
