import logging
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError

from task_manager import get_all_active_tasks, update_task_execution_time

# Глобальный планировщик
task_scheduler = None
bot_instance = None

logger = logging.getLogger(__name__)

def init_scheduler(application):
    """Инициализирует планировщик задач с использованием application"""
    global task_scheduler, bot_instance
    
    if task_scheduler is None:
        task_scheduler = AsyncIOScheduler()
        bot_instance = application.bot
        
        # Настраиваем планировщик
        task_scheduler.configure(
            timezone=pytz.timezone('Europe/Moscow'),
            job_defaults={
                'misfire_grace_time': 300,  # 5 минут на выполнение
                'coalesce': True,  # объединять пропущенные выполнения
                'max_instances': 1  # только один экземпляр задачи
            }
        )
        
        logger.info("✅ Планировщик задач инициализирован")
    
    return task_scheduler

async def execute_task(task_id, task_data):
    """Выполняет задачу - отправляет сообщение в указанный чат"""
    global bot_instance
    
    try:
        logger.info(f"🔄 Выполнение задачи: {task_data['template_name']} (ID: {task_id})")
        
        # Определяем чат для отправки
        target_chat_id = task_data.get('target_chat_id')
        
        # Если целевой чат не указан, используем чат создателя
        if not target_chat_id:
            target_chat_id = task_data.get('created_by')
            logger.info(f"⚠️ Целевой чат не указан, отправляем создателю: {target_chat_id}")
        
        if not target_chat_id:
            logger.error(f"❌ Не указан чат для отправки задачи {task_id}")
            return
        
        # Подготавливаем сообщение
        message_text = task_data.get('template_text', '')
        image_path = task_data.get('template_image')
        
        # Отправляем сообщение
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await bot_instance.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text
                )
            logger.info(f"✅ Отправлено фото + текст в чат {target_chat_id}")
        else:
            await bot_instance.send_message(
                chat_id=target_chat_id,
                text=message_text
            )
            logger.info(f"✅ Отправлен текст в чат {target_chat_id}")
        
        # Обновляем время выполнения
        update_task_execution_time(task_id)
        
        logger.info(f"✅ Задача выполнена: {task_data['template_name']}")
        
    except TelegramError as e:
        logger.error(f"❌ Ошибка Telegram при выполнении задачи {task_id}: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения задачи {task_id}: {e}")

async def execute_test_task(template, update, context, target_chat_id=None):
    """Выполняет тестовую задачу немедленно в указанный чат"""
    try:
        user_id = update.effective_user.id
        
        if not target_chat_id:
            target_chat_id = update.effective_chat.id
        
        logger.info(f"🧪 Выполнение тестовой задачи: {template['name']} в чат {target_chat_id}")
        
        message_text = template.get('text', '')
        image_path = template.get('image')
        
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text
                )
            logger.info(f"✅ Тест: отправлено фото + текст в чат {target_chat_id}")
        else:
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=message_text
            )
            logger.info(f"✅ Тест: отправлен текст в чат {target_chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестовой задачи: {e}")
        from keyboards.task_keyboards import get_tasks_main_keyboard
        await update.message.reply_text(
            f"❌ Ошибка отправки тестового сообщения: {e}",
            reply_markup=get_tasks_main_keyboard()
        )

def schedule_existing_tasks():
    """Планирует существующие активные задачи"""
    global task_scheduler
    
    if not task_scheduler:
        logger.error("❌ Планировщик не инициализирован")
        return
    
    active_tasks = get_all_active_tasks()
    scheduled_count = 0
    
    for task_id, task in active_tasks.items():
        if task.get('is_active', True) and not task.get('is_test', False):
            success = schedule_task(task_id, task)
            if success:
                scheduled_count += 1
    
    logger.info(f"✅ Запланировано задач: {scheduled_count}")

def schedule_test_task(task_id, task_data):
    """Планирует выполнение тестовой задачи через 5 секунд"""
    global task_scheduler
    
    if not task_scheduler:
        return False
    
    try:
        from datetime import datetime, timedelta
        from apscheduler.triggers.date import DateTrigger
        
        execution_time = datetime.now() + timedelta(seconds=5)
        
        task_scheduler.add_job(
            execute_task,
            trigger=DateTrigger(run_date=execution_time),
            args=[task_id, task_data],
            id=f"test_{task_id}",
            name=f"test_task_{task_id}",
            replace_existing=True
        )
        
        logger.info(f"✅ Тестовая задача запланирована на: {execution_time}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка планирования тестовой задачи {task_id}: {e}")
        return False

def schedule_task(task_id, task_data):
    """Планирует выполнение задачи по расписанию"""
    global task_scheduler
    
    if not task_scheduler:
        return False
    
    try:
        time_str = task_data.get('time')
        days = task_data.get('days', [])
        
        if not time_str or not days:
            logger.warning(f"⚠️ Не могу запланировать задачу {task_id}: нет времени или дней")
            return False
        
        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        
        # Создаем cron триггер для указанных дней
        trigger = CronTrigger(
            day_of_week=','.join(map(str, days)),  # Преобразуем в строки
            hour=hour,
            minute=minute,
            timezone=pytz.timezone('Europe/Moscow')
        )
        
        # Добавляем задачу в планировщик
        task_scheduler.add_job(
            execute_task,
            trigger=trigger,
            args=[task_id, task_data],
            id=task_id,
            name=f"task_{task_id}",
            replace_existing=True
        )
        
        logger.info(f"✅ Задача запланирована: {task_data['template_name']} на {time_str} в дни {days}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка планирования задачи {task_id}: {e}")
        return False

def start_scheduler():
    """Запускает планировщик"""
    global task_scheduler
    
    if task_scheduler and not task_scheduler.running:
        task_scheduler.start()
        schedule_existing_tasks()
        
        jobs = task_scheduler.get_jobs()
        logger.info(f"✅ Планировщик задач запущен. Запланировано jobs: {len(jobs)}")

def stop_scheduler():
    """Останавливает планировщик"""
    global task_scheduler
    
    if task_scheduler and task_scheduler.running:
        task_scheduler.shutdown(wait=False)
        logger.info("✅ Планировщик задач остановлен")