import logging
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
from datetime import datetime, timedelta
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
        # Создаем планировщик с правильной конфигурацией
        task_scheduler = AsyncIOScheduler(
            timezone=pytz.timezone('Europe/Moscow'),
            job_defaults={
                'misfire_grace_time': 300,  # 5 минут на выполнение
                'coalesce': True,           # объединять пропущенные выполнения
                'max_instances': 1          # только один экземпляр задачи
            }
        )
        bot_instance = application.bot
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
            # Отправляем изображение с текстом
            with open(image_path, 'rb') as photo:
                await bot_instance.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text,
                    parse_mode='HTML'
                )
            logger.info(f"✅ Отправлено фото + текст в чат {target_chat_id}")
        else:
            # Отправляем только текст
            await bot_instance.send_message(
                chat_id=target_chat_id,
                text=message_text,
                parse_mode='HTML'
            )
            logger.info(f"✅ Отправлен текст в чат {target_chat_id}")
        
        # Обновляем время выполнения
        update_task_execution_time(task_id)
        
        logger.info(f"✅ Задача выполнена: {task_data['template_name']}")
        
    except TelegramError as e:
        logger.error(f"❌ Ошибка Telegram при выполнении задачи {task_id}: {e}")
        
        # Проверяем специфические ошибки Telegram
        if "Chat not found" in str(e) or "bot was blocked" in str(e):
            logger.warning(f"⚠️ Чат {target_chat_id} недоступен, деактивируем задачу {task_id}")
            # Здесь можно добавить логику деактивации задачи
            
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения задачи {task_id}: {e}")
        import traceback
        traceback.print_exc()

async def execute_test_task(template, update, context, target_chat_id=None):
    """Выполняет тестовую задачу немедленно в указанный чат"""
    try:
        user_id = update.effective_user.id
        
        # Если чат не указан, отправляем в текущий чат
        if not target_chat_id:
            target_chat_id = update.effective_chat.id
        
        logger.info(f"🧪 Выполнение тестовой задачи: {template['name']} в чат {target_chat_id}")
        
        # Подготавливаем сообщение
        message_text = template.get('text', '')
        image_path = template.get('image')
        
        # Отправляем сообщение
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text,
                    parse_mode='HTML'
                )
            logger.info(f"✅ Тест: отправлено фото + текст в чат {target_chat_id}")
        else:
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=message_text,
                parse_mode='HTML'
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
    failed_count = 0
    
    logger.info(f"📋 Найдено активных задач: {len(active_tasks)}")
    
    for task_id, task in active_tasks.items():
        if task.get('is_active', True) and not task.get('is_test', False):
            success = schedule_task(task_id, task)
            if success:
                scheduled_count += 1
            else:
                failed_count += 1
                logger.warning(f"⚠️ Не удалось запланировать задачу {task_id}")
    
    logger.info(f"✅ Запланировано задач: {scheduled_count}, не удалось: {failed_count}")

def schedule_test_task(task_id, task_data):
    """Планирует выполнение тестовой задачи через 5 секунд"""
    global task_scheduler
    
    if not task_scheduler:
        logger.error("❌ Планировщик не инициализирован для тестовой задачи")
        return False
    
    try:
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
        logger.error("❌ Планировщик не инициализирован")
        return False
    
    try:
        time_str = task_data.get('time')
        days = task_data.get('days', [])
        
        if not time_str or not days:
            logger.warning(f"⚠️ Не могу запланировать задачу {task_id}: нет времени или дней")
            return False
        
        # Парсим время
        try:
            hour, minute = map(int, time_str.split(':'))
        except ValueError:
            logger.error(f"❌ Неверный формат времени в задаче {task_id}: {time_str}")
            return False
        
        # Преобразуем дни в строки для cron
        days_str = ','.join(map(str, days))
        
        # Создаем cron триггер для указанных дней
        trigger = CronTrigger(
            day_of_week=days_str,
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
        import traceback
        traceback.print_exc()
        return False

def unschedule_task(task_id):
    """Удаляет задачу из планировщика"""
    global task_scheduler
    
    if not task_scheduler:
        return False
    
    try:
        # Пытаемся удалить задачу
        if task_scheduler.get_job(task_id):
            task_scheduler.remove_job(task_id)
            logger.info(f"✅ Задача {task_id} удалена из планировщика")
            return True
        else:
            logger.warning(f"⚠️ Задача {task_id} не найдена в планировщике")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка удаления задачи {task_id}: {e}")
        return False

def reschedule_task(task_id, task_data):
    """Перепланирует задачу (удаляет и создает заново)"""
    # Сначала удаляем старую задачу
    unschedule_task(task_id)
    
    # Затем создаем новую
    return schedule_task(task_id, task_data)

def start_scheduler():
    """Запускает планировщик"""
    global task_scheduler
    
    if task_scheduler and not task_scheduler.running:
        try:
            task_scheduler.start()
            schedule_existing_tasks()
            
            jobs = task_scheduler.get_jobs()
            logger.info(f"✅ Планировщик задач запущен. Запланировано jobs: {len(jobs)}")
            
            # Логируем информацию о запланированных задачах
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    logger.info(f"   📅 {job.name}: следующее выполнение {next_run}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка запуска планировщика: {e}")
            raise

def stop_scheduler():
    """Останавливает планировщик"""
    global task_scheduler
    
    if task_scheduler and task_scheduler.running:
        try:
            # Получаем информацию о задачах перед остановкой
            jobs_count = len(task_scheduler.get_jobs())
            
            task_scheduler.shutdown(wait=True)  # Ждем завершения текущих задач
            
            logger.info(f"✅ Планировщик задач остановлен. Было задач: {jobs_count}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки планировщика: {e}")

def get_scheduler_status():
    """Возвращает статус планировщика"""
    global task_scheduler
    
    if not task_scheduler:
        return {
            'status': 'not_initialized',
            'running': False,
            'jobs_count': 0
        }
    
    jobs = task_scheduler.get_jobs()
    
    return {
        'status': 'running' if task_scheduler.running else 'stopped',
        'running': task_scheduler.running,
        'jobs_count': len(jobs),
        'next_runs': [
            {
                'job_id': job.id,
                'job_name': job.name,
                'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else None
            }
            for job in jobs[:10]  # Ограничиваем количество для логов
        ]
    }

def print_scheduler_status():
    """Выводит статус планировщика в логи"""
    status = get_scheduler_status()
    
    logger.info("📊 СТАТУС ПЛАНИРОВЩИКА ЗАДАЧ:")
    logger.info(f"   • Статус: {status['status']}")
    logger.info(f"   • Запущен: {status['running']}")
    logger.info(f"   • Количество задач: {status['jobs_count']}")
    
    if status['next_runs']:
        logger.info("   • Ближайшие выполнения:")
        for job in status['next_runs']:
            if job['next_run']:
                logger.info(f"     - {job['job_name']}: {job['next_run']}")
