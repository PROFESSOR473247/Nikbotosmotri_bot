import logging
import asyncio
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError

from task_manager import get_all_active_tasks, update_task_execution_time, calculate_next_execution
from keyboards.task_keyboards import get_tasks_main_keyboard

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
        print("✅ Планировщик задач инициализирован")
    
    return task_scheduler

async def execute_task(task_id, task_data):
    """Выполняет задачу - отправляет сообщение в указанный чат"""
    global bot_instance
    
    try:
        print(f"🔄 Выполнение задачи: {task_data['template_name']} (ID: {task_id})")
        
        # Определяем чат для отправки
        target_chat_id = task_data.get('target_chat_id')
        
        # Если целевой чат не указан, используем чат создателя (для обратной совместимости)
        if not target_chat_id:
            target_chat_id = task_data.get('created_by')
            print(f"⚠️ Целевой чат не указан, отправляем создателю: {target_chat_id}")
        
        if not target_chat_id:
            print(f"❌ Не указан чат для отправки задачи {task_id}")
            return
        
        # Подготавливаем сообщение
        message_text = task_data.get('template_text', '')
        image_path = task_data.get('template_image')
        
        # Отправляем сообщение
        if image_path and os.path.exists(image_path):
            # Отправляем изображение с текстом
            with open(image_path, 'rb') as photo:
                await bot_instance.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text
                )
            print(f"✅ Отправлено фото + текст в чат {target_chat_id}")
        else:
            # Отправляем только текст
            await bot_instance.send_message(
                chat_id=target_chat_id,
                text=message_text
            )
            print(f"✅ Отправлен текст в чат {target_chat_id}")
        
        # Обновляем время выполнения
        update_task_execution_time(task_id)
        
        print(f"✅ Задача выполнена: {task_data['template_name']}")
        
    except TelegramError as e:
        print(f"❌ Ошибка Telegram при выполнении задачи {task_id}: {e}")
    except Exception as e:
        print(f"❌ Ошибка выполнения задачи {task_id}: {e}")
        import traceback
        traceback.print_exc()

async def execute_test_task(template, update, context, target_chat_id=None):
    """Выполняет тестовую задачу немедленно в указанный чат"""
    try:
        user_id = update.effective_user.id
        
        # Если чат не указан, отправляем в текущий чат
        if not target_chat_id:
            target_chat_id = update.effective_chat.id
        
        print(f"🧪 Выполнение тестовой задачи: {template['name']} в чат {target_chat_id}")
        
        # Подготавливаем сообщение
        message_text = template.get('text', '')
        image_path = template.get('image')
        
        # Отправляем сообщение
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text
                )
            print(f"✅ Тест: отправлено фото + текст в чат {target_chat_id}")
        else:
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=message_text
            )
            print(f"✅ Тест: отправлен текст в чат {target_chat_id}")
        
    except Exception as e:
        print(f"❌ Ошибка тестовой задачи: {e}")
        await update.message.reply_text(
            f"❌ Ошибка отправки тестового сообщения: {e}",
            reply_markup=get_tasks_main_keyboard()
        )

def schedule_existing_tasks():
    """Планирует существующие активные задачи"""
    global task_scheduler
    
    if not task_scheduler:
        print("❌ Планировщик не инициализирован")
        return
    
    active_tasks = get_all_active_tasks()
    scheduled_count = 0
    
    for task_id, task in active_tasks.items():
        if task.get('is_active', True) and not task.get('is_test', False):
            success = schedule_task(task_id, task)
            if success:
                scheduled_count += 1
    
    print(f"✅ Запланировано задач: {scheduled_count}")

def schedule_test_task(task_id, task_data):
    """Планирует выполнение тестовой задачи через 5 секунд"""
    global task_scheduler
    
    if not task_scheduler:
        return False
    
    try:
        # Планируем выполнение через 5 секунд
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
        
        print(f"✅ Тестовая задача запланирована на: {execution_time}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка планирования тестовой задачи {task_id}: {e}")
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
            print(f"⚠️ Не могу запланировать задачу {task_id}: нет времени или дней")
            return False
        
        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        
        # Создаем cron триггер для указанных дней
        trigger = CronTrigger(
            day_of_week=','.join(days),  # 0-понедельник, 6-воскресенье
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
        
        print(f"✅ Задача запланирована: {task_data['template_name']} на {time_str} в дни {days}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка планирования задачи {task_id}: {e}")
        return False

def start_scheduler():
    """Запускает планировщик"""
    global task_scheduler
    
    if task_scheduler and not task_scheduler.running:
        task_scheduler.start()
        schedule_existing_tasks()
        print("✅ Планировщик задач запущен")
        
        # Выводим информацию о запланированных задачах
        jobs = task_scheduler.get_jobs()
        print(f"📅 Запланировано jobs: {len(jobs)}")

def stop_scheduler():
    """Останавливает планировщик"""
    global task_scheduler
    
    if task_scheduler and task_scheduler.running:
        task_scheduler.shutdown()
        print("✅ Планировщик задач остановлен")