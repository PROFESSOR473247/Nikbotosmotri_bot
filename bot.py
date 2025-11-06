import os
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN

# Импорт обработчиков
from handlers.start_handlers import start, help_command
from handlers.basic_handlers import handle_main_menu, handle_text
from handlers.template_handlers import get_template_conversation_handler
from handlers.task_handlers import get_task_conversation_handler

# Импорт планировщика задач
from task_scheduler import init_scheduler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Основная функция бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        
        # Добавляем ConversationHandler для шаблонов
        application.add_handler(get_template_conversation_handler())
        
        # Добавляем ConversationHandler для задач
        application.add_handler(get_task_conversation_handler())
        
        # Добавляем обработчики текстовых сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Добавляем обработчик для главного меню
        application.add_handler(MessageHandler(filters.Regex("^🔙 Главное меню$"), handle_main_menu))
        
        # Запускаем планировщик задач
        logger.info("Запуск планировщика задач...")
        scheduler = init_scheduler(BOT_TOKEN)
        scheduler.start()
        logger.info("Планировщик задач запущен")
        
        # Запускаем бота
        logger.info("Бот запускается...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()
