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

# Принудительный сброс и создание администратора
def reset_admin():
    """Полный сброс и создание администратора"""
    print("🚀 Принудительный сброс системы...")
    
    # Удаляем все файлы данных
    files_to_remove = [
        'authorized_users.json',
        'active_tasks.json', 
        'bot_groups.json',
        'user_groups.json',
        'templates.json',
        'user_roles.json'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ Удален файл: {file}")
    
    # Инициализируем базу данных заново
    init_database()
    print("✅ База данных переинициализирована")
    
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
    print("✅ Администратор создан в authorized_users.json")
    
    # Сохраняем в user_roles.json
    user_roles_data = {"user_roles": {str(admin_id): "admin"}}
    with open('user_roles.json', 'w', encoding='utf-8') as f:
        json.dump(user_roles_data, f, ensure_ascii=False, indent=2)
    print("✅ Роль администратора установлена в user_roles.json")
    
    print("\n🎉 Сброс завершен!")
    print(f"👤 Администратор: ID {admin_id}")
    print("🔑 Роль: admin")
    print("📋 Доступ: все функции")

# Инициализация базы данных с принудительным сбросом
print("🔄 Инициализация системы...")
reset_admin()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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

# Keep alive для Render
def keep_alive():
    def ping():
        while True:
            try:
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    requests.get(render_url, timeout=10)
                time.sleep(300)
            except:
                time.sleep(300)
    
    threading.Thread(target=ping, daemon=True).start()

async def main():
    """Основная функция запуска"""
    print("🚀 Запуск бота...")
    
    keep_alive()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(JobQueue())
        .build()
    )

    # Восстанавливаем задачи (только один раз)
    try:
        await task_manager.restore_tasks(application)
        print("✅ Задачи восстановлены")
    except Exception as e:
        print(f"❌ Ошибка восстановления задач: {e}")

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

    print("✅ Бот запущен и готов к работе!")
    
    # Запускаем polling без перезапуска при ошибках
    await application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    # Запускаем бота один раз без рекурсивных перезапусков
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        time.sleep(10)
        # Вместо рекурсивного вызова, завершаем процесс и позволяем Render перезапустить
        os._exit(1)
