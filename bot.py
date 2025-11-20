import logging
import os
import asyncio
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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
from task_scheduler import init_scheduler, start_scheduler

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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    try:
        raise context.error
    except Exception as e:
        logger.error(f"❌ Ошибка в обработчике: {e}")
        if "Conflict" in str(e):
            logger.error("⚠️ Обнаружен конфликт - вероятно запущен другой экземпляр бота")

async def debug_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Временная команда для отладки создания задачи"""
    user_id = update.effective_user.id
    
    try:
        await update.message.reply_text("🔄 Запуск отладки создания задачи...")
        
        from task_manager import create_task_from_template
        from template_manager import get_template_by_name_and_group
        
        template_name = "Тестовый шаблон для размещения задачи"
        group_id = "hongqi"
        
        logger.info(f"🔍 Поиск шаблона: {template_name} в группе {group_id}")
        
        template_id, template_data = get_template_by_name_and_group(template_name, group_id)
        
        if not template_data:
            await update.message.reply_text("❌ Шаблон не найден")
            return
        
        logger.info(f"✅ Шаблон найден: {template_data.get('name')}")
        
        success, task_id = create_task_from_template(
            template_data,
            created_by=user_id,
            target_chat_id=update.effective_chat.id,
            is_test=False
        )
        
        if success:
            await update.message.reply_text(
                f"✅ Тестовая задача создана успешно!\n🆔 ID задачи: `{task_id}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка создания задачи в тестовом режиме")
            
    except Exception as e:
        error_msg = f"💥 Критическая ошибка: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(error_msg)

def check_database():
    """Проверяет состояние базы данных при запуске"""
    logger.info("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ ПРИ ЗАПУСКЕ")
    
    try:
        from database import db
        from template_manager import get_all_templates, load_groups
        from task_manager import get_all_active_tasks
        from user_chat_manager import user_chat_manager
        from auth_manager import auth_manager
        
        db.init_database()
        
        templates = get_all_templates()
        groups_data = load_groups()
        groups_count = len(groups_data.get('groups', {}))
        active_tasks = get_all_active_tasks()
        users = user_chat_manager.get_all_users()
        chats = user_chat_manager.get_all_chats()
        
        logger.info(f"✅ Шаблонов в базе данных: {len(templates)}")
        logger.info(f"✅ Групп в базе данных: {groups_count}")
        logger.info(f"✅ Активных задач: {len(active_tasks)}")
        logger.info(f"✅ Пользователей в системе: {len(users)}")
        logger.info(f"✅ Telegram чатов в системе: {len(chats)}")
        
        from config import ADMIN_USER_ID
        auth_manager.update_user_role_if_needed(ADMIN_USER_ID)
        logger.info(f"✅ Права суперадмина проверены: {ADMIN_USER_ID}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки базы данных: {e}")

def setup_handlers(application):
    """Настраивает все обработчики для приложения"""
    
    logger.info("🔄 Регистрация обработчиков...")
    
    # 1. ConversationHandler (самые специфичные)
    admin_conv_handler = get_admin_conversation_handler()
    template_conv_handler = get_template_conversation_handler()
    task_conv_handler = get_enhanced_task_conversation_handler()

    application.add_handler(admin_conv_handler)
    application.add_handler(template_conv_handler)
    application.add_handler(task_conv_handler)

    logger.info(f"✅ ConversationHandler зарегистрированы")

    # 2. Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("my_id", my_id))
    application.add_handler(CommandHandler("now", now))
    application.add_handler(CommandHandler("update_menu", update_menu))
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("check_access", check_access))
    application.add_handler(CommandHandler("debug_task", debug_task_command))

    # 3. Обработчик отмены
    application.add_handler(CommandHandler("cancel", cancel))

    # 4. Общий текстовый обработчик (последний)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ Все обработчики зарегистрированы")

def initialize_services():
    """Инициализирует все сервисы приложения"""
    
    # Проверяем базу данных
    check_database()
    
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

async def main():
    """Основная асинхронная функция запуска бота"""
    logger.info("🚀 Запуск бота...")
    
    # Инициализируем сервисы
    initialize_services()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Настраиваем обработчики
    setup_handlers(application)

    # Инициализируем и запускаем планировщик
    try:
        init_scheduler(application)
        start_scheduler()
        logger.info("✅ Планировщик задач инициализирован и запущен")
    except Exception as e:
        logger.error(f"⚠️ Ошибка инициализации планировщика: {e}")

    logger.info("✅ Бот запущен и готов к работе!")
    
    # Запускаем бота с обработкой исключений
    try:
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            timeout=60,
            close_loop=False
        )
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    # Запускаем HTTP сервер в отдельном потоке
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()
    logger.info("✅ HTTP сервер запущен")
    
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")