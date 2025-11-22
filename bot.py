import logging
import os
import asyncio
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработчик health-check запросов"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'✅ Bot is alive and running!')
        
        # Логируем запрос (но не слишком часто)
        current_time = time.time()
        if not hasattr(self, 'last_log_time') or current_time - self.last_log_time > 300:  # Раз в 5 минут
            logger.info(f"🌐 Health check received from {self.client_address[0]}")
            self.last_log_time = current_time
    
    def log_message(self, format, *args):
        """Уменьшаем логирование health-check запросов"""
        return

class InternalPinger:
    """Внутренний пинг-сервис для поддержания активности"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or os.environ.get('RENDER_EXTERNAL_URL', '')
        self.is_active = bool(self.base_url)
        self.thread = None
        self.stop_event = threading.Event()
        
    def start(self):
        """Запускает внутренний пинг-сервис"""
        if not self.is_active:
            logger.warning("⚠️ Internal pinger: URL не указан, сервис отключен")
            return
            
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info(f"🔄 Internal pinger запущен для {self.base_url}")
    
    def stop(self):
        """Останавливает пинг-сервис"""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Internal pinger остановлен")
    
    def _ping_loop(self):
        """Цикл отправки ping-запросов"""
        ping_interval = 300  # 5 минут
        
        while not self.stop_event.is_set():
            try:
                response = requests.get(self.base_url, timeout=10)
                if response.status_code == 200:
                    logger.debug("✅ Internal ping successful")
                else:
                    logger.warning(f"⚠️ Internal ping: статус {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Internal ping error: {e}")
            
            # Ждем перед следующим ping
            self.stop_event.wait(ping_interval)

def run_http_server():
    """Запускает HTTP сервер для health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"✅ HTTP server listening on port {port}")
    
    try:
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP сервера: {e}")
    finally:
        server.server_close()
        logger.info("🛑 HTTP server stopped")

async def run_bot():
    """Запускает бота - основная асинхронная функция"""
    from telegram.ext import Application
    from config import BOT_TOKEN
    
    application = None
    
    try:
        logger.info("🚀 Инициализация бота...")
        
        # Инициализация сервисов
        from database import db
        db.init_database()
        logger.info("✅ База данных инициализирована")
        
        # Обновление структуры БД
        try:
            from database_updater import update_database_structure
            update_database_structure()
            logger.info("✅ Структура БД обновлена")
        except Exception as e:
            logger.error(f"⚠️ Ошибка обновления БД: {e}")
        
        # Инициализация файлов
        try:
            from template_manager import init_files
            from task_manager import init_task_files
            init_files()
            init_task_files()
            logger.info("✅ Файлы инициализированы")
        except Exception as e:
            logger.error(f"⚠️ Ошибка инициализации файлов: {e}")
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Настраиваем обработчик ошибок
        async def error_handler(update, context):
            try:
                raise context.error
            except Exception as e:
                logger.error(f"❌ Ошибка в обработчике: {e}")
        
        application.add_error_handler(error_handler)
        
        # Регистрируем обработчики
        logger.info("🔄 Регистрация обработчиков...")
        
        from telegram.ext import CommandHandler, MessageHandler, filters
        from handlers.start_handlers import start, help_command, my_id, now, update_menu
        from handlers.admin_handlers import admin_stats, check_access
        from handlers.basic_handlers import handle_text, cancel
        from handlers.template_handlers import get_template_conversation_handler
        from handlers.enhanced_task_handlers import get_enhanced_task_conversation_handler
        from handlers.admin_handlers import get_admin_conversation_handler
        
        # ConversationHandler
        application.add_handler(get_admin_conversation_handler())
        application.add_handler(get_template_conversation_handler())
        application.add_handler(get_enhanced_task_conversation_handler())
        
        # Команды
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("my_id", my_id))
        application.add_handler(CommandHandler("now", now))
        application.add_handler(CommandHandler("update_menu", update_menu))
        application.add_handler(CommandHandler("admin_stats", admin_stats))
        application.add_handler(CommandHandler("check_access", check_access))
        application.add_handler(CommandHandler("cancel", cancel))
        
        # Текстовый обработчик
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        logger.info("✅ Обработчики зарегистрированы")
        
        # Инициализируем планировщик
        from task_scheduler import init_scheduler, start_scheduler
        init_scheduler(application)
        start_scheduler()
        logger.info("✅ Планировщик запущен")
        
        logger.info("✅ Бот запущен и готов к работе!")
        
        # ЯВНОЕ УПРАВЛЕНИЕ APPLICATION - чтобы все корутины были properly awaited
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
        # Бесконечный цикл ожидания
        while True:
            await asyncio.sleep(3600)  # Спим 1 час
        
    except asyncio.CancelledError:
        logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка бота: {e}")
        raise
    finally:
        # КОРРЕКТНАЯ ОСТАНОВКА - все корутины properly awaited
        if application:
            try:
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
                logger.info("✅ Бот корректно остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка при остановке бота: {e}")

def start_bot():
    """Запускает бота в отдельном event loop"""
    # Создаем новый event loop для бота
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Запускаем основную асинхронную функцию
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен по запросу пользователя")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        # Закрываем loop после завершения работы бота
        if not loop.is_closed():
            loop.close()
        logger.info("✅ Event loop бота закрыт")

def main():
    """Основная функция"""
    logger.info("🚀 Запуск системы...")
    
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    logger.info("✅ HTTP сервер запущен")
    
    # Запускаем внутренний пинг-сервис
    pinger = InternalPinger("https://nikbotosmotri-bot.onrender.com/")
    pinger.start()
    logger.info("✅ Internal pinger запущен")
    
    try:
        # Запускаем бота в основном потоке
        start_bot()
    finally:
        # Останавливаем пинг-сервис при завершении
        pinger.stop()

if __name__ == '__main__':
    main()