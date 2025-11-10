import logging
import asyncio
import os
import threading
import time
import requests
import signal
import sys
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

# Глобальная переменная для graceful shutdown
is_shutting_down = False

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global is_shutting_down
    print(f"🛑 Получен сигнал {signum}, завершаем работу...")
    is_shutting_down = True
    sys.exit(0)

def keep_alive():
    """Периодически пингует приложение чтобы не дать ему заснуть"""
    def ping():
        while not is_shutting_down:
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
    
    from template_manager import get_all_templates, load_groups
    
    message = f"🔍 **Отладочная информация о шаблонах**\n\n"
    
    # Проверяем шаблоны из базы данных
    try:
        templates = get_all_templates()
        message += f"📝 **Шаблоны в базе данных:** {len(templates)}\n\n"
        
        if templates:
            message += "**Список шаблонов:**\n"
            for i, (template_id, template) in enumerate(templates.items(), 1):
                message += f"{i}. **{template.get('name', 'Без названия')}**\n"
                message += f"   ID: `{template_id}`\n"
                message += f"   Группа: {template.get('group', 'Не указана')}\n"
                message += f"   Время: {template.get('time', 'Не указано')}\n"
                message += f"   Дней: {len(template.get('days', []))}\n"
                message += f"   Текст: {template.get('text', '')[:50]}...\n\n"
        else:
            message += "📭 Шаблонов нет\n\n"
            
    except Exception as e:
        message += f"❌ Ошибка загрузки шаблонов: {e}\n\n"
    
    # Проверяем группы из базы данных
    try:
        groups_data = load_groups()
        groups_count = len(groups_data.get('groups', {}))
        message += f"👥 **Группы в базе данных:** {groups_count}\n\n"
        
        if groups_count > 0:
            message += "**Список групп:**\n"
            for group_id, group_data in groups_data.get('groups', {}).items():
                message += f"• {group_data.get('name', 'Без названия')} (ID: {group_id})\n"
        
    except Exception as e:
        message += f"❌ Ошибка загрузки групп: {e}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def debug_system(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общая отладочная информация о системе"""
    user_id = update.effective_user.id
    
    from authorized_users import is_admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
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
    
    # Используем прямые импорты функций
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

async def debug_database(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная информация о базе данных"""
    user_id = update.effective_user.id
    
    from authorized_users import is_admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    from database import db
    
    message = "🗄️ **Информация о базе данных**\n\n"
    
    # Проверяем подключение
    conn = db.get_connection()
    if conn:
        message += "✅ **Подключение:** Успешно\n"
        
        try:
            cursor = conn.cursor()
            
            # Проверяем таблицы
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cursor.fetchall()
            
            message += f"📊 **Таблицы в базе:** {len(tables)}\n"
            for table in tables:
                message += f"   - {table[0]}\n"
            
            # Проверяем шаблоны
            cursor.execute("SELECT COUNT(*) FROM templates")
            templates_count = cursor.fetchone()[0]
            message += f"\n📝 **Шаблонов в базе:** {templates_count}\n"
            
            if templates_count > 0:
                cursor.execute("SELECT id, name, group_name FROM templates LIMIT 10")
                templates = cursor.fetchall()
                message += "**Последние шаблоны:**\n"
                for template in templates:
                    message += f"   - {template[1]} (ID: {template[0]}, Группа: {template[2]})\n"
            
            # Проверяем группы
            cursor.execute("SELECT COUNT(*) FROM groups")
            groups_count = cursor.fetchone()[0]
            message += f"👥 **Групп в базе:** {groups_count}\n"
            
            if groups_count > 0:
                cursor.execute("SELECT id, name FROM groups")
                groups = cursor.fetchall()
                message += "**Группы:**\n"
                for group in groups:
                    message += f"   - {group[1]} (ID: {group[0]})\n"
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            message += f"❌ **Ошибка запроса:** {e}\n"
            try:
                conn.close()
            except:
                pass
    else:
        message += "❌ **Подключение:** Не удалось\n"
        message += f"📡 **DATABASE_URL:** {'✅ Найден' if db.connection_string else '❌ Не найден'}\n"
        if db.connection_string:
            # Показываем только начало URL для безопасности
            safe_url = db.connection_string.split('@')[0] + '@***' if '@' in db.connection_string else '***'
            message += f"🔗 **Подключение:** {safe_url}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def debug_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отладочная информация о доступе пользователя"""
    user_id = update.effective_user.id
    
    from authorized_users import is_authorized, get_user_groups
    from template_manager import get_user_accessible_groups, load_groups
    
    message = "🔐 **Информация о доступе**\n\n"
    
    message += f"👤 **Пользователь:** {user_id}\n"
    message += f"✅ **Авторизован:** {'Да' if is_authorized(user_id) else 'Нет'}\n"
    
    if is_authorized(user_id):
        user_groups = get_user_groups(user_id)
        message += f"📋 **Группы в authorized_users.json:** {user_groups}\n\n"
        
        accessible_groups = get_user_accessible_groups(user_id)
        message += f"🔓 **Доступные группы:** {len(accessible_groups)}\n"
        
        if accessible_groups:
            for group_id, group_data in accessible_groups.items():
                message += f"   - {group_data.get('name', 'Без названия')} (ID: {group_id})\n"
        else:
            message += "   ❌ Нет доступных групп\n"
        
        # Покажем все группы из базы для сравнения
        groups_data = load_groups()
        all_groups = groups_data.get('groups', {})
        message += f"\n📊 **Все группы в базе:** {len(all_groups)}\n"
        for group_id, group_data in all_groups.items():
            status = "✅" if group_id in user_groups else "❌"
            message += f"   {status} {group_data.get('name', 'Без названия')} (ID: {group_id})\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def debug_create_test_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание тестового шаблона для отладки"""
    user_id = update.effective_user.id
    
    from authorized_users import is_admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для этой команды")
        return
    
    from template_manager import create_template
    
    # Создаем тестовый шаблон
    test_template = {
        'name': 'Тестовый шаблон',
        'group': 'hongqi',
        'text': 'Это тестовый шаблон для проверки работы базы данных',
        'time': '12:00',
        'days': [0, 2, 4],  # Понедельник, Среда, Пятница
        'frequency': 'weekly',
        'created_by': user_id
    }
    
    success, template_id = create_template(test_template)
    
    if success:
        await update.message.reply_text(
            f"✅ Тестовый шаблон успешно создан!\n\n"
            f"ID: `{template_id}`\n"
            f"Название: {test_template['name']}\n"
            f"Группа: {test_template['group']}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ Ошибка создания тестового шаблона\n\n"
            f"Проверьте логи для подробной информации",
            parse_mode='Markdown'
        )

async def fix_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Исправление доступа пользователя"""
    user_id = update.effective_user.id
    
    try:
        from authorized_users import get_user_groups, update_user_groups
        
        # Даем доступ ко всем группам
        all_groups = ["hongqi", "turbomatiz"]
        success, message = update_user_groups(user_id, all_groups)
        
        if success:
            await update.message.reply_text(
                f"✅ Доступ к группам предоставлен!\n\n"
                f"User ID: {user_id}\n"
                f"Группы: {', '.join(all_groups)}\n"
                f"Теперь попробуйте создать шаблон снова.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Не удалось предоставить доступ: {message}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

def check_template_files():
    """Проверяет состояние данных при запуске"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА ДАННЫХ ПРИ ЗАПУСКЕ")
    print("=" * 60)
    
    try:
        from template_manager import get_all_templates, load_groups
        
        # Инициализируем базу данных
        from database import db
        print("🔄 Инициализация базы данных...")
        db_success = db.init_database()
        print(f"✅ База данных инициализирована: {db_success}")
        
        # Проверяем шаблоны
        templates = get_all_templates()
        print(f"✅ Шаблонов в базе данных: {len(templates)}")
        
        for template_id, template in templates.items():
            print(f"   📝 {template_id}: {template.get('name', 'Без названия')} "
                  f"(группа: {template.get('group', 'Не указана')})")
        
        # Проверяем группы
        groups_data = load_groups()
        groups_count = len(groups_data.get('groups', {}))
        print(f"✅ Групп в базе данных: {groups_count}")
        
        for group_id, group_data in groups_data.get('groups', {}).items():
            print(f"   👥 {group_id}: {group_data.get('name', 'Без названия')}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки данных: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    try:
        raise context.error
    except Exception as e:
        print(f"❌ Ошибка в обработчике: {e}")
        if "Conflict" in str(e):
            print("⚠️ Обнаружен конфликт - вероятно запущен другой экземпляр бота")
            # Не пытаемся отправлять сообщение, чтобы не усугублять конфликт
        import traceback
        traceback.print_exc()

def main():
    print("🚀 Запуск бота с улучшенным логированием...")
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Детальная проверка файлов при запуске
    try:
        check_template_files()
        
        # Дополнительная проверка через template_manager
        from template_manager import get_all_templates
        templates = get_all_templates()
        print(f"📊 Итог: {len(templates)} шаблонов загружено")
        
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке данных: {e}")
        import traceback
        traceback.print_exc()
    
    # Инициализация файлов шаблонов
    try:
        from template_manager import init_files
        init_files()
        print("✅ Файлы шаблонов инициализированы")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации шаблонов: {e}")
        import traceback
        traceback.print_exc()
    
    # Исправляем структуру данных при запуске
    try:
        from fix_data import fix_users_data, init_required_files
        fix_users_data()
        init_required_files()
        print("✅ Структура данных проверена и исправлена")
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке данных: {e}")
        import traceback
        traceback.print_exc()
    
    keep_alive()

    # Создаем приложение с обработчиком ошибок
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

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
    application.add_handler(CommandHandler("debug_database", debug_database))
    application.add_handler(CommandHandler("debug_access", debug_access))
    application.add_handler(CommandHandler("debug_test_template", debug_create_test_template))
    application.add_handler(CommandHandler("fix_access", fix_access))

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
    print("   /debug_database - информация о базе данных")
    print("   /debug_access - информация о доступе пользователя")
    print("   /debug_test_template - создать тестовый шаблон")
    print("   /fix_access - исправить доступ к группам")
    
    try:
        application.run_polling(
            drop_pending_updates=True,  # Игнорируем старые сообщения при запуске
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске бота: {e}")
        if "Conflict" in str(e):
            print("💡 Решение: Подождите 10 секунд и перезапустите бота")
            print("💡 Или остановите все другие экземпляры бота")
        import traceback
        traceback.print_exc()

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
        try:
            server.serve_forever()
        except Exception as e:
            print(f"❌ Ошибка HTTP сервера: {e}")
    
    http_thread = Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    main()