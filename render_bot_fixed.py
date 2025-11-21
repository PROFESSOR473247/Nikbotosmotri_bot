import logging
import os
import asyncio
import signal
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Настройка логирования ДО всех импортов
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

def initialize_services():
    """Инициализирует все сервисы приложения"""
    logger.info("🔍 Инициализация сервисов...")
    
    try:
        from database import db
        db.init_database()
        logger.info("✅ База данных инициализирована")
        
        # Обновляем структуру базы данных
        try:
            from database_updater import update_database_structure
            update_database_structure()
            logger.info("✅ Структура базы данных проверена и обновлена")
        except Exception as e:
            logger.error(f"⚠️ Ошибка обновления структуры базы данных: {e}")
        
        # Инициализируем файлы шаблонов и задач
        try:
            from template_manager import init_files
            from task_manager import init_task_files
            init_files()
            init_task_files()
            logger.info("✅ Менеджер шаблонов и задач инициализирован")
        except Exception as e:
            logger.error(f"⚠️ Ошибка инициализации: {e}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации сервисов: {e}")
        raise

async def setup_application():
    """Создает и настраивает приложение бота"""
    from telegram.ext import Application
    from config import BOT_TOKEN
    
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
    
    # ConversationHandler (самые специфичные)
    admin_conv_handler = get_admin_conversation_handler()
    template_conv_handler = get_template_conversation_handler()
    task_conv_handler = get_enhanced_task_conversation_handler()

    application.add_handler(admin_conv_handler)
    application.add_handler(template_conv_handler)
    application.add_handler(task_conv_handler)

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("update_menu", update_menu))
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("check_access", check_access))

    # Обработчик отмены
    application.add_handler(CommandHandler("cancel", cancel))

    # Общий текстовый обработчик (последний)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ Все обработчики зарегистрированы")
    
    return application

async def run_bot():
    """Запускает бота"""
    try:
        # Инициализируем сервисы
        initialize_services()
        
        # Создаем приложение
        application = await setup_application()
        
        # Инициализируем планировщик
        from task_scheduler import init_scheduler, start_scheduler
        init_scheduler(application)
        start_scheduler()
        logger.info("✅ Планировщик задач инициализирован и запущен")

        logger.info("✅ Бот запущен и готов к работе!")
        
        # Запускаем polling с правильной обработкой остановки
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
        # Ждем остановки
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        logger.info("🛑 Получен сигнал остановки")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        # Останавливаем приложение
        try:
            if 'application' in locals():
                await application.updater.stop()
                await application.stop()
                await application.shutdown()
                logger.info("✅ Бот остановлен корректно")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке бота: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"🛑 Получен сигнал {signum}, завершаем работу...")
    # Завершаем процесс
    sys.exit(0)

def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск бота для Render...")
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    logger.info("✅ HTTP сервер запущен")
    
    # Создаем и запускаем event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Запускаем бота
        bot_task = loop.create_task(run_bot())
        loop.run_until_complete(bot_task)
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
    finally:
        # Останавливаем loop
        try:
            # Отменяем все задачи
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Ждем завершения задач
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.close()
            logger.info("✅ Event loop закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии event loop: {e}")

if __name__ == '__main__':
    main()
