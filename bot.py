import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    JobQueue
)
from config import BOT_TOKEN
from authorized_users import is_authorized, is_admin, add_user, remove_user, get_users_list, get_admin_id
from database import init_database, load_groups, save_groups, load_user_groups, add_user_to_group
from task_manager import task_manager
from group_manager import group_manager
import datetime
import pytz
from datetime import timedelta
import sys
import os
import requests
import threading
import time

# Инициализация базы данных при запуске
init_database()

# Принудительно перезагружаем модуль templates
if 'templates' in sys.modules:
    del sys.modules['templates']

# Импортируем шаблоны
TEMPLATES = {}
try:
    from templates import TEMPLATES as IMPORTED_TEMPLATES
    TEMPLATES = IMPORTED_TEMPLATES
    print("✅ Шаблоны загружены успешно")
except ImportError as import_error:
    print(f"❌ Ошибка загрузки шаблонов: {import_error}")
    exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Состояния для ConversationHandler
ADD_USER_ID, ADD_USER_NAME = range(2)
SELECT_GROUP, SELECT_TEMPLATE = range(2, 4)

# Декоратор для проверки авторизации
def authorization_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_authorized(user_id):
            await update.message.reply_text(
                "❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n"
                "Для доступа к функциям бота обратитесь к администратору",
                reply_markup=get_unauthorized_keyboard()
            )
            print(f"🚫 Неавторизованный доступ от user_id: {user_id} к функции: {func.__name__}")
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

# Главное меню
def get_main_keyboard():
    keyboard = [
        ["📋 Шаблоны", "🧪 Тестирование"],
        ["📊 Статус задач", "⚙️ ЕЩЕ"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_unauthorized_keyboard():
    keyboard = [
        ["🆔 Получить ID"],
        ["📋 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_templates_keyboard():
    keyboard = [
        ["🚗 Hongqi 476 group", "🚙 Matiz 476 group"],
        ["🔙 Главное меню"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_group_selection_keyboard(user_id):
    """Клавиатура для выбора группы"""
    accessible_groups = group_manager.get_accessible_groups_for_user(user_id)
    keyboard = []
    
    for group_id, group_info in accessible_groups.items():
        keyboard.append([f"📋 {group_info.get('title', f'Группа {group_id}')}"])
    
    keyboard.append(["🔙 Главное меню"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Если бот в группе - обновляем информацию о группе
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        await group_manager.update_group_info(update, context)
        return
    
    # Личная переписка
    current_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M:%S")

    if not is_authorized(user_id):
        welcome_text = (
            f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n\n'
            f'Добрый день! Данный бот предназначен для создания отложенных сообщений в тг-группах и каналах.\n\n'
            f'🆔 Ваш ID: `{user_id}`\n'
            f'🕒 Текущее время: {current_time} (МСК)\n\n'
            f'❌ У ВАС НЕДОСТАТОЧНО ПРАВ\n\n'
            f'Для начала работы с ботом нажмите кнопку «Получить ID» и сообщите его @ProfeSSor471. '
            f'Он внесёт Вас в список пользователей и объяснит дальнейшую работу с ботом.\n\n'
            f'Приятного пользования!'
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_unauthorized_keyboard(),
            parse_mode='Markdown'
        )
        return

    welcome_text = (
        f'🤖 БОТ ДЛЯ ОТЛОЖЕННЫХ СООБЩЕНИЙ\n'
        f'🕒 Текущее время: {current_time} (МСК)\n'
        f'🆔 Ваш ID: {user_id}\n\n'
        f'🎹 Используйте кнопки меню для навигации!'
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

@authorization_required
async def handle_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Шаблоны"""
    user_id = update.effective_user.id
    
    accessible_groups = group_manager.get_accessible_groups_for_user(user_id)
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе\n\n"
            "Обратитесь к администратору для получения доступа",
            reply_markup=get_main_keyboard()
        )
        return
    
    await update.message.reply_text(
        "🎯 Выберите группу для работы с шаблонами:",
        reply_markup=get_group_selection_keyboard(user_id)
    )

@authorization_required 
async def handle_testing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Тестирование"""
    user_id = update.effective_user.id
    
    accessible_groups = group_manager.get_accessible_groups_for_user(user_id)
    if not accessible_groups:
        await update.message.reply_text(
            "❌ У вас нет доступа ни к одной группе",
            reply_markup=get_main_keyboard()
        )
        return
    
    await update.message.reply_text(
        "🧪 ТЕСТИРОВАНИЕ ШАБЛОНОВ\n\n"
        "Выберите группу для тестовой отправки:",
        reply_markup=get_group_selection_keyboard(user_id)
    )

@authorization_required
async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ статуса задач пользователя"""
    user_id = update.effective_user.id
    user_tasks = task_manager.get_user_tasks(user_id)
    
    if not user_tasks:
        status_text = "📊 СТАТУС ЗАДАЧ\n\n❌ У вас нет активных задач"
    else:
        status_text = "📊 СТАТУС ВАШИХ АКТИВНЫХ ЗАДАЧ:\n\n"
        for task_id, task_data in user_tasks.items():
            group_info = load_groups()["groups"].get(str(task_data["group_id"]), {})
            group_name = group_info.get('title', f'Группа {task_data["group_id"]}')
            
            status_text += f"🔹 {TEMPLATES.get(task_data['template_name'], {}).get('text', 'Шаблон')[:50]}...\n"
            status_text += f"   📍 Группа: {group_name}\n"
            status_text += f"   🕒 Создана: {task_data['created_at'][:16]}\n"
            status_text += f"   🔧 Тип: {'Основная' if task_data['task_type'] == 'main' else 'Тестовая'}\n\n"
    
    await update.message.reply_text(
        status_text,
        reply_markup=get_main_keyboard()
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Пропускаем обработку если это группа
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        return
    
    if text == "📋 Шаблоны":
        await handle_templates(update, context)
    elif text == "🧪 Тестирование":
        await handle_testing(update, context)
    elif text == "📊 Статус задач":
        await handle_status(update, context)
    elif text == "⚙️ ЕЩЕ":
        await update.message.reply_text(
            "⚙️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ",
            reply_markup=get_more_keyboard(user_id)
        )
    elif text == "🔙 Главное меню":
        await update.message.reply_text(
            "🔙 Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )
    elif text == "🆔 Получить ID":
        await my_id(update, context)
    elif text == "📋 Справка":
        await help_command(update, context)
    else:
        await update.message.reply_text(
            "❌ Неизвестная команда",
            reply_markup=get_main_keyboard() if is_authorized(user_id) else get_unauthorized_keyboard()
        )

# Сохраняем остальные функции из оригинального bot.py
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... существующий код ...

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... существующий код ...

def get_more_keyboard(user_id):
    # ... существующий код ...

# Остальные функции остаются пока без изменений
# ... остальной код из оригинального bot.py ...

def main():
    """Запуск бота"""
    print("🚀 Запуск бота...")
    
    # Инициализация базы данных
    init_database()

    # Создаем приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(JobQueue())
        .build()
    )

    # Восстанавливаем задачи при запуске
    asyncio.run(task_manager.restore_tasks(application))

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("status", handle_status))
    application.add_handler(CommandHandler("update_menu", update_menu))

    # Обработчики кнопок главного меню
    application.add_handler(MessageHandler(filters.Regex("^📋 Шаблоны$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🧪 Тестирование$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📊 Статус задач$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ ЕЩЕ$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🔙 Главное меню$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^🆔 Получить ID$"), handle_text))
    application.add_handler(MessageHandler(filters.Regex("^📋 Справка$"), handle_text))

    # Обработчик для всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Обработчик для обновления информации о группах
    application.add_handler(MessageHandler(filters.ALL, group_manager.update_group_info))

    print("✅ Бот запущен и готов к работе!")
    application.run_polling()

if __name__ == '__main__':
    main()
