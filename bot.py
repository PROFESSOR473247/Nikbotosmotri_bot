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

def check_database():
    """Проверяет состояние базы данных при запуске"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ ПРИ ЗАПУСКЕ")
    print("=" * 60)
    
    try:
        from database import db
        from template_manager import get_all_templates, load_groups
        
        # Инициализируем базу данных
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
    print("🚀 Запуск бота с открытым доступом...")
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверяем базу данных
    check_database()
    
    # Инициализация файлов шаблонов
    try:
        from template_manager import init_files
        init_files()
        print("✅ Менеджер шаблонов инициализирован")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации шаблонов: {e}")
    
    keep_alive()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Получаем ConversationHandler для шаблонов
    template_conv_handler = get_template_conversation_handler()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("update_menu", update_menu))

    # Добавляем ConversationHandler для шаблонов
    application.add_handler(template_conv_handler)

    # Обработчик для всех текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Бот запущен и готов к работе!")
    print("🎉 Режим: ОТКРЫТЫЙ ДОСТУП")
    print("📝 Все пользователи имеют доступ к созданию шаблонов")
    print("💾 Данные сохраняются в PostgreSQL")
    
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
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
    
    main()