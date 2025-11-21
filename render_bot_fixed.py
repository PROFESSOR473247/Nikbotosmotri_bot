import logging
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running!')
    
    def log_message(self, format, *args):
        return

def run_http_server():
    """Запускает HTTP сервер для health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"✅ HTTP server listening on port {port}")
    try:
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Ошибка HTTP сервера: {e}")

def run_bot():
    """Запускает бота в отдельном потоке"""
    import asyncio
    
    # Создаем новый event loop для этого потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def main_async():
        try:
            from telegram.ext import Application
            from config import BOT_TOKEN
            
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
            
            # Запускаем polling - ЭТО БЛОКИРУЮЩИЙ ВЫЗОВ
            await application.run_polling(
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query'],
                close_loop=False
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка бота: {e}")
            raise
    
    try:
        # Запускаем бота в event loop этого потока
        loop.run_until_complete(main_async())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        loop.close()

def main():
    """Основная функция"""
    logger.info("🚀 Запуск системы...")
    
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    logger.info("✅ HTTP сервер запущен")
    
    # Запускаем бота в отдельном потоке
    bot_thread = Thread(target=run_bot, daemon=False)  # daemon=False чтобы бот не завершался
    bot_thread.start()
    logger.info("✅ Бот запущен в отдельном потоке")
    
    # Главный поток просто ждет завершения бота
    try:
        bot_thread.join()
        logger.info("👋 Бот завершил работу")
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки")

if __name__ == '__main__':
    main()
