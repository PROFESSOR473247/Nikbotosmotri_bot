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
import sys

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

# Инициализация базы данных
print("🔄 Инициализация системы...")
init_database()
reset_admin()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ... остальной код без изменений ...

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

    # Восстанавливаем задачи
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
    print("🤖 Бот работает в режиме polling...")
    
    # Запускаем polling
    await application.run_polling()

if __name__ == '__main__':
    # Простой запуск без сложной обработки ошибок
    asyncio.run(main())
