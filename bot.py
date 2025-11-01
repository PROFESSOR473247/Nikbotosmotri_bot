# -*- coding: utf-8 -*-
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler, JobQueue
)
from config import BOT_TOKEN
from authorized_users import is_authorized, is_admin, get_user_role
from database import init_database
from task_manager import task_manager
from group_manager import group_manager
from menu_manager import *
import datetime
import pytz
import os
import requests
import threading
import time
import json

# Принудительный сброс и создание администратора (только если файлов нет)
def reset_admin():
    """Сброс и создание администратора только при первом запуске"""
    if os.path.exists('authorized_users.json'):
        print("✅ Файлы уже существуют, пропускаем сброс")
        return
        
    print("🚀 Первоначальная настройка системы...")
    
    # Создаем администратора
    admin_id = 812934047
    admin_data = {
        "users": {
            str(admin_id): {
                "name": "Никита",
                "role": "admin",
                "groups": ["all"]
            }
        },
        "admin_id": admin_id
    }
    
    # Сохраняем в authorized_users.json
    with open('authorized_users.json', 'w', encoding='utf-8') as f:
        json.dump(admin_data, f, ensure_ascii=False, indent=4)
    print("✅ Администратор создан")
    
    # Сохраняем в user_roles.json
    user_roles_data = {"user_roles": {str(admin_id): "admin"}}
    with open('user_roles.json', 'w', encoding='utf-8') as f:
        json.dump(user_roles_data, f, ensure_ascii=False, indent=2)
    print("✅ Роль администратора установлена")
    
    print(f"🎉 Настройка завершена! Администратор: ID {admin_id}")

# Keep alive для Render
def start_keep_alive():
    """Функция для поддержания активности приложения на Render"""
    def ping():
        while True:
            try:
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    response = requests.get(render_url, timeout=10)
                    print(f"✅ Ping sent: {response.status_code}")
                else:
                    print("🔄 Keep-alive: bot active")
            except Exception as e:
                print(f"⚠️ Ping error: {e}")
            time.sleep(300)  # Ping every 5 minutes
    
    ping_thread = threading.Thread(target=ping, daemon=True)
    ping_thread.start()
    print("🚀 Keep-alive system started")

# Инициализация базы данных
print("🔄 Инициализация системы...")
init_database()
reset_admin()

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
            await update.message.reply_text(
                "❌ НЕДОСТАТОЧНО ПРАВ\n\n"
                "Для доступа к боту свяжитесь с администратором @ProfeSSor471",
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
            await update.message.reply_text(
                "❌ ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА\n\n"
                "Эта функция доступна только администратору",
                reply_markup=get_main_menu(user_id)
            )
            return None
        return await func(update, context, *args, **kwargs)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Если бот в группе - обновляем информацию
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        await group_manager.update_group_info(update, context)
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

@authorization_required
async def handle_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Задачи"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "📋 УПРАВЛЕНИЕ ЗАДАЧАМИ",
        reply_markup=get_tasks_menu()
    )

@authorization_required
async def handle_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Шаблоны"""
    user_id = update.effective_user.id
    user_role = get_user_role(user_id)
    
    if user_role in ["гость", "водитель"]:
        await update.message.reply_text(
            "❌ НЕДОСТАТОЧНО ПРАВ\n\n"
            "Управление шаблонами доступно только администраторам и руководителям",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    await update.message.reply_text(
        "📁 УПРАВЛЕНИЕ ШАБЛОНАМИ",
        reply_markup=get_templates_menu()
    )

@authorization_required
@admin_required
async def handle_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Пользователи (только админ)"""
    await update.message.reply_text(
        "👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ",
        reply_markup=get_users_menu()
    )

@authorization_required
async def handle_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Группы"""
    user_id = update.effective_user.id
    user_role = get_user_role(user_id)
    
    if user_role == "гость":
        await update.message.reply_text(
            "❌ НЕДОСТАТОЧНО ПРАВ\n\n"
            "Управление группами доступно только администраторам и руководителям",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    await update.message.reply_text(
        "🏘️ УПРАВЛЕНИЕ ГРУППАМИ",
        reply_markup=get_groups_menu(user_id)
    )

@authorization_required
async def handle_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки Еще"""
    user_id = update.effective_user.id
    await update.message.reply_text(
        "ℹ️ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ",
        reply_markup=get_more_menu(user_id)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Пропускаем обработку в группах
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        return
    
    # Обработка кнопок главного меню
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

    # Обработчик всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Обработчик обновления информации о группах
    application.add_handler(MessageHandler(filters.ALL, group_manager.update_group_info))

async def main():
    """Основная асинхронная функция запуска"""
    print("🚀 Запуск бота...")
    
    # Запускаем keep-alive систему
    start_keep_alive()

    # Создаем приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(JobQueue())
        .build()
    )

    # Настраиваем обработчики
    setup_handlers(application)

    # Восстанавливаем задачи
    await task_manager.restore_tasks(application)

    print("✅ Бот запущен и готов к работе!")
    print("🤖 Бот работает в режиме polling...")
    
    # Запускаем polling
    await application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    # Простой асинхронный запуск
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        time.sleep(10)
        # Завершаем процесс, чтобы Render перезапустил его
        os._exit(1)
