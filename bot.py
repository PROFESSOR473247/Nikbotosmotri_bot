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
from handlers.enhanced_task_handlers import get_enhanced_task_conversation_handler
from handlers.admin_handlers import get_admin_conversation_handler, admin_stats, check_access
from handlers.basic_handlers import handle_text, cancel
from task_scheduler import init_scheduler, task_scheduler
from chat_access_manager import init_chat_access_manager

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
    
    # Останавливаем планировщик задач
    if task_scheduler:
        task_scheduler.stop()
    
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

def check_database():
    """Проверяет состояние базы данных при запуске"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ ПРИ ЗАПУСКЕ")
    print("=" * 60)
    
    try:
        from database import db
        from template_manager import get_all_templates, load_groups
        from task_manager import get_all_active_tasks
        from user_chat_manager import user_chat_manager
        from auth_manager import auth_manager
        
        # Инициализируем базу данных
        print("📊 Инициализация базы данных...")
        db.init_database()
        
        # Проверяем состояние
        print("📊 Проверка состояния базы данных...")
        
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
            
        # Проверяем активные задачи
        active_tasks = get_all_active_tasks()
        print(f"✅ Активных задач: {len(active_tasks)}")
        
        for task_id, task in active_tasks.items():
            target_chat = task.get('target_chat_id', 'Не указан')
            print(f"   📋 {task_id}: {task.get('template_name', 'Без названия')} "
                  f"(чат: {target_chat})")
        
        # Проверяем пользователей и чаты
        users = user_chat_manager.get_all_users()
        chats = user_chat_manager.get_all_chats()
        print(f"✅ Пользователей в системе: {len(users)}")
        print(f"✅ Telegram чатов в системе: {len(chats)}")
        
        # Гарантируем права суперадмина
        from config import ADMIN_USER_ID
        auth_manager.update_user_role_if_needed(ADMIN_USER_ID)
        print(f"✅ Права суперадмина проверены: {ADMIN_USER_ID}")
            
    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")
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
        import traceback
        traceback.print_exc()

def main():
    print("🚀 Запуск бота с улучшенной системой задач...")
    print("🆕 ВЕРСИЯ: 3.0 - Система задач с выбором чатов и проверкой доступа")
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверяем базу данных
    check_database()
    
    # ОБНОВЛЯЕМ СТРУКТУРУ БАЗЫ ДАННЫХ
    try:
        from database_updater import update_database_structure
        update_database_structure()
        print("✅ Структура базы данных проверена и обновлена")
    except Exception as e:
        print(f"⚠️ Ошибка обновления структуры базы данных: {e}")
    
    # Инициализируем файлы шаблонов и задач
    try:
        from template_manager import init_files
        from task_manager import init_task_files
        
        init_files()
        init_task_files()
        print("✅ Менеджер шаблонов и задач инициализирован")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации: {e}")
    
    keep_alive()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # ===== ИНИЦИАЛИЗАЦИЯ СИСТЕМ ДОСТУПА =====
    
    # Инициализируем менеджер доступа к чатам
    init_chat_access_manager(BOT_TOKEN)
    print("✅ Менеджер доступа к чатам инициализирован")

    # ===== ПРАВИЛЬНЫЙ ПОРЯДОК РЕГИСТРАЦИИ ОБРАБОТЧИКОВ =====
    
    print("🔄 Регистрация ConversationHandler...")
    
    # 1. Сначала ConversationHandler (самые специфичные)
    admin_conv_handler = get_admin_conversation_handler()
    template_conv_handler = get_template_conversation_handler()
    enhanced_task_conv_handler = get_enhanced_task_conversation_handler()

    # Добавляем ConversationHandler в правильном порядке
    application.add_handler(admin_conv_handler)          # ПЕРВЫЙ!
    application.add_handler(template_conv_handler)       # ВТОРОЙ
    application.add_handler(enhanced_task_conv_handler)  # ТРЕТИЙ - УЛУЧШЕННЫЙ!

    print(f"✅ ConversationHandler зарегистрированы:")
    print(f"   • Администрирование: {len(admin_conv_handler.states)} состояний")
    print(f"   • Шаблоны: {len(template_conv_handler.states)} состояний")
    print(f"   • Задачи (улучшенные): {len(enhanced_task_conv_handler.states)} состояний")

    # 2. Затем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("update_menu", update_menu))
    
    # Админские команды
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("check_access", check_access))

    # 3. Обработчик отмены
    application.add_handler(CommandHandler("cancel", cancel))

    # 4. Общий текстовый обработчик (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Все обработчики зарегистрированы в правильном порядке")

    # Инициализируем планировщик задач
    try:
        init_scheduler(application)
        print("✅ Планировщик задач инициализирован")
        
        # Запускаем планировщик
        from task_scheduler import start_scheduler
        start_scheduler()
        print("✅ Планировщик задач запущен")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации планировщика: {e}")

    print("✅ Бот запущен и готов к работе!")
    print("🎉 Режим: УЛУЧШЕННАЯ СИСТЕМА ЗАДАЧ")
    print("💬 Контекст: РАЗДЕЛЕНИЕ ЛИЧНЫХ СООБЩЕНИЙ И ГРУПП")
    print("👑 Суперадмин: АВТОМАТИЧЕСКОЕ ВОССТАНОВЛЕНИЕ ПРАВ")
    print("💾 Все данные сохраняются в PostgreSQL")
    print("⏰ Планировщик задач активен")
    print("👥 Система управления пользователями и чатами готова")
    
    # Информация о новых функциях задач
    print("\n" + "="*60)
    print("🆕 НОВЫЕ ВОЗМОЖНОСТИ СИСТЕМЫ ЗАДАЧ:")
    print("• ✅ Выбор конкретного Telegram чата для отправки")
    print("• 🔒 Проверка членства пользователя в выбранном чате")
    print("• ✏️ Редактирование шаблона на этапе создания задачи")
    print("• 📊 Фильтрация задач по доступным пользователю")
    print("• 🧪 Тестирование с отправкой в указанный чат")
    print("• 💬 Вся настройка в личных сообщениях")
    print("• 🚀 Отправка результатов только в целевые чаты")
    print("="*60)
    
    try:
        print("🔄 Запуск бота...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            timeout=60
        )
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске бота: {e}")
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
        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"✅ HTTP server listening on port {port}")
        try:
            server.serve_forever()
        except Exception as e:
            print(f"❌ Ошибка HTTP сервера: {e}")
    
    http_thread = Thread(target=run_http_server)
    http_thread.daemon = True
    http_thread.start()
    
    # Запускаем бота
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()