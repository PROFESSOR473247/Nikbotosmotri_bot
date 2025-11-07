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

def main():
    print("🚀 Запуск бота с модульной структурой...")
    
    # Исправляем структуру данных при запуске
    try:
        from fix_data import fix_users_data, init_required_files
        fix_users_data()
        init_required_files()
        print("✅ Структура данных проверена и исправлена")
    except Exception as e:
        print(f"⚠️ Предупреждение при проверке данных: {e}")
    
    # Инициализируем файлы шаблонов
    try:
        from template_manager import init_files
        init_files()
        print("✅ Файлы шаблонов инициализированы")
    except Exception as e:
        print(f"⚠️ Ошибка инициализации шаблонов: {e}")
    
    keep_alive()
    # ... остальной код

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

    # Добавляем ConversationHandler для шаблонов
    application.add_handler(template_conv_handler)
    
    # Добавляем ConversationHandler для задач
    application.add_handler(task_conv_handler)

    # Обработчик для всех текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("✅ Бот запущен и готов к работе!")
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
