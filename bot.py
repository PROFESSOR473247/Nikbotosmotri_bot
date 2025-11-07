import logging
import asyncio
import os
import threading
import time
import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, ConversationHandler
)

from config import BOT_TOKEN
from handlers.start_handlers import start, help_command, my_id, now, update_menu
from handlers.template_handlers import get_template_conversation_handler
from handlers.task_handlers import get_task_conversation_handler
from handlers.basic_handlers import handle_text, cancel

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def keep_alive():
    """Периодически пингует приложение чтобы не дать ему заснуть"""
    def ping():
        while True:
            try:
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    response = requests.get(render_url, timeout=10)
                    print(f"🔄 Пинг отправлен: {response.status_code}")
                else:
                    print("🔄 Keep-alive: бот активен")
            except Exception as e:
                print(f"⚠️ Ошибка пинга: {e}")
            time.sleep(300)
    
    ping_thread = threading.Thread(target=ping, daemon=True)
    ping_thread.start()
    print("✅ Keep-alive система запущена")

async def debug_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная информация о шаблонах"""
    user_id = update.effective_user.id
    
    from authorized_users import is_admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    import os
    import json
    
    templates_file = 'data/templates.json'
    groups_file = 'data/groups.json'
    
    message = f"🔍 **Отладочная информация о шаблонах**\n\n"
    
    # Проверяем файл шаблонов
    templates_exists = os.path.exists(templates_file)
    templates_size = os.path.getsize(templates_file) if templates_exists else 0
    
    message += f"📁 **Файл шаблонов:** `{templates_file}`\n"
    message += f"   Существует: {'✅ Да' if templates_exists else '❌ Нет'}\n"
    message += f"   Размер: {templates_size} байт\n"
    
    if templates_exists and templates_size > 0:
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            
            message += f"   📋 Шаблонов в файле: {len(templates_data)}\n\n"
            
            if templates_data:
                message += "**Список шаблонов:**\n"
                for i, (template_id, template) in enumerate(templates_data.items(), 1):
                    message += f"{i}. **{template.get('name', 'Без названия')}**\n"
                    message += f"   ID: `{template_id}`\n"
                    message += f"   Группа: {template.get('group', 'Не указана')}\n"
                    message += f"   Время: {template.get('time', 'Не указано')}\n"
                    message += f"   Дней: {len(template.get('days', []))}\n"
                    message += f"   Текст: {template.get('text', '')[:50]}...\n\n"
            else:
                message += "📭 Шаблонов нет\n\n"
                
        except Exception as e:
            message += f"❌ Ошибка чтения: {e}\n\n"
    else:
        message += "📭 Файл пуст или не существует\n\n"
    
    # Проверяем файл групп
    groups_exists = os.path.exists(groups_file)
    groups_size = os.path.getsize(groups_file) if groups_exists else 0
    
    message += f"📁 **Файл групп:** `{groups_file}`\n"
    message += f"   Существует: {'✅ Да' if groups_exists else '❌ Нет'}\n"
    message += f"   Размер: {groups_size} байт\n"
    
    if groups_exists and groups_size > 0:
        try:
            with open(groups_file, 'r', encoding='utf-8') as f:
                groups_data = json.load(f)
            
            groups_count = len(groups_data.get('groups', {}))
            message += f"   👥 Групп в файле: {groups_count}\n\n"
            
            if groups_count > 0:
                message += "**Список групп:**\n"
                for group_id, group_data in groups_data.get('groups', {}).items():
                    message += f"• {group_data.get('name', 'Без названия')} (ID: {group_id})\n"
            
        except Exception as e:
            message += f"❌ Ошибка чтения: {e}\n\n"
    else:
        message += "📭 Файл пуст или не существует\n\n"
    
    # Проверяем директорию images
    images_dir = 'data/images'
    images_exists = os.path.exists(images_dir)
    message += f"📁 **Директория изображений:** `{images_dir}`\n"
    message += f"   Существует: {'✅ Да' if images_exists else '❌ Нет'}\n"
    
    if images_exists:
        try:
            images_count = len([f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))])
            message += f"   🖼️ Изображений: {images_count}\n"
        except Exception as e:
            message += f"❌ Ошибка чтения: {e}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def debug_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общая отладочная информация о системе"""
    user_id = update.effective_user.id
    
    from authorized_users import is_admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    import json
    import platform
    from datetime import datetime
    
    message = "🖥️ **Системная информация**\n\n"
    
    # Базовая информация о системе
    message += f"💻 **Платформа:** {platform.system()} {platform.release()}\n"
    message += f"🐍 **Python:** {platform.python_version()}\n"
    message += f"🕐 **Время сервера:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Информация о файловой системе
    message += f"📊 **Файловая система:**\n"
    
    try:
        # Проверяем доступное место в текущей директории
        import shutil
        total, used, free = shutil.disk_usage(".")
        message += f"   💽 Всего места: {total // (2**30)} GB\n"
        message += f"   📁 Использовано: {used // (2**30)} GB\n"
        message += f"   📂 Свободно: {free // (2**30)} GB\n"
    except Exception as e:
        message += f"   ⚠️ Не удалось получить информацию о диске: {e}\n"
    
    message += f"\n"
    
    # Переменные окружения
    message += f"🌐 **Окружение:**\n"
    message += f"   RENDER: {'✅ Да' if 'RENDER' in os.environ else '❌ Нет'}\n"
    if 'RENDER_EXTERNAL_URL' in os.environ:
        message += f"   URL: {os.environ['RENDER_EXTERNAL_URL']}\n"
    if 'RENDER_SERVICE_NAME' in os.environ:
        message += f"   Сервис: {os.environ['RENDER_SERVICE_NAME']}\n"
    
    # Информация о процессе
    message += f"\n⚙️ **Процесс:**\n"
    message += f"   PID: {os.getpid()}\n"
    message += f"   Рабочая директория: {os.getcwd()}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def debug_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о состоянии бота"""
    user_id = update.effective_user.id
    
    from authorized_users import is_admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    # Используем прямые импорты функций вместо глобального template_manager
    from template_manager import get_all_templates, load_groups
    from task_manager import load_active_tasks, load_test_tasks
    
    message = "🤖 **Информация о боте**\n\n"
    
    # Информация о шаблонах
    try:
        templates = get_all_templates()
        message += f"📝 **Шаблоны:** {len(templates)}\n"
    except Exception as e:
        message += f"📝 **Шаблоны:** Ошибка загрузки: {e}\n"
    
    # Информация о задачах
    try:
        active_tasks = load_active_tasks()
        test_tasks = load_test_tasks()
        message += f"📋 **Активные задачи:** {len(active_tasks)}\n"
        message += f"🧪 **Тестовые задачи:** {len(test_tasks)}\n\n"
    except Exception as e:
        message += f"📋 **Задачи:** Ошибка загрузки: {e}\n\n"
    
    # Информация о группах
    try:
        groups_data = load_groups()
        groups_count = len(groups_data.get('groups', {}))
        message += f"👥 **Группы:** {groups_count}\n\n"
    except Exception as e:
        message += f"👥 **Группы:** Ошибка загрузки: {e}\n\n"
    
    # Информация о пользовательских данных
    message += f"📊 **Данные:**\n"
    try:
        if hasattr(context.application, 'persistence') and context.application.persistence:
            if hasattr(context.application.persistence, 'user_data'):
                user_data_count = len(context.application.persistence.user_data)
                message += f"   👤 Пользователей: {user_data_count}\n"
            else:
                message += f"   👤 Данные пользователей: не доступны\n"
            
            if hasattr(context.application.persistence, 'chat_data'):
                chat_data_count = len(context.application.persistence.chat_data)
                message += f"   💬 Чатов: {chat_data_count}\n"
        else:
            message += f"   💾 Persistence: не настроен\n"
    except Exception as e:
        message += f"   ⚠️ Ошибка получения данных: {e}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

def check_template_files():
    """Проверяет состояние файлов шаблонов при запуске"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА ФАЙЛОВ ШАБЛОНОВ ПРИ ЗАПУСКЕ")
    print("=" * 60)
    
    import json
    import os
    
    templates_file = 'data/templates.json'
    groups_file = 'data/groups.json'
    images_dir = 'data/images'
    
    # Проверяем файл шаблонов
    if os.path.exists(templates_file):
        try:
            with open(templates_file, 'r', encoding='utf-8') as f:
                templates_data = json.load(f)
            print(f"✅ Файл шаблонов: {len(templates_data)} записей")
            
            for template_id, template in templates_data.items():
                print(f"   📝 {template_id}: {template.get('name', 'Без названия')} "
                      f"(группа: {template.get('group', 'Не указана')})")
                      
        except Exception as e:
            print(f"❌ Ошибка чтения файла шаблонов: {e}")
    else:
        print("❌ Файл шаблонов не существует")
    
    # Проверяем файл групп
    if os.path.exists(groups_file):
        try:
            with open(groups_file, 'r', encoding='utf-8') as f:
                groups_data = json.load(f)
            groups_count = len(groups_data.get('groups', {}))
            print(f"✅ Файл групп: {groups_count} групп")
            
            for group_id, group_data in groups_data.get('groups', {}).items():
                print(f"   👥 {group_id}: {group_data.get('name', 'Без названия')}")
                
        except Exception as e:
            print(f"❌ Ошибка чтения файла групп: {e}")
    else:
        print("❌ Файл групп не существует")
    
    # Проверяем директорию изображений
    if os.path.exists(images_dir):
        try:
            images_count = len([f for f in os.listdir(images_dir) if os.path.isfile(os.path.join(images_dir, f))])
            print(f"✅ Директория изображений: {images_count} файлов")
        except Exception as e:
            print(f"❌ Ошибка чтения директории изображений: {e}")
    else:
        print("❌ Директория изображений не существует")
    
    print("=" * 60)

def main():
    print("🚀 Запуск бота с улучшенным логированием...")
    
    # Детальная проверка файлов при запуске
    try:
        check_template_files()
        
        # Дополнительная проверка через template_manager
        from template_manager import get_all_templates
        templates = get_all_templates()
        print(f"📊 Итог: {len(templates)} шаблонов загружено")
        
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке данных: {e}")
    
    # Инициализация файлов шаблонов
    try:
        from template_manager import init_files
        init_files()
        print("✅ Файлы шаблонов инициализированы")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации шаблонов: {e}")
    
    # Исправляем структуру данных при запуске
    try:
        from fix_data import fix_users_data, init_required_files
        fix_users_data()
        init_required_files()
        print("✅ Структура данных проверена и исправлена")
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке данных: {e}")
    
    keep_alive()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Получаем ConversationHandler для шаблонов
    template_conv_handler = get_template_conversation_handler()
    
    # Получаем ConversationHandler для задач
    task_conv_handler = get_task_conversation_handler()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("update_menu", update_menu))
    
    # Отладочные команды (только для админов)
    application.add_handler(CommandHandler("debug", debug_templates))
    application.add_handler(CommandHandler("debug_system", debug_system))
    application.add_handler(CommandHandler("debug_bot", debug_bot))

    # Добавляем ConversationHandler для шаблонов
    application.add_handler(template_conv_handler)
    
    # Добавляем ConversationHandler для задач
    application.add_handler(task_conv_handler)

    # Обработчик для всех текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Бот запущен и готов к работе!")
    print("📝 Доступные отладочные команды для админов:")
    print("   /debug - информация о шаблонах")
    print("   /debug_system - системная информация") 
    print("   /debug_bot - информация о состоянии бота")
    
    application.run_polling()

if __name__ == '__main__':
    # Для Render Web Service
    import os
    from threading import Thread
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        
        def log_message(self, format, *args):
            return
    
    def run_http_server():
        port = int(os.environ.get('PORT', 5000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"✅ HTTP server listening on port {port}")
        server.serve_forever()
    
    http_thread = Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    main()