import logging
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
from datetime import datetime, timedelta
from telegram.error import TelegramError

from task_manager import get_all_active_tasks, update_task_execution_time, deactivate_task

# Глобальный планировщик
task_scheduler = None
bot_instance = None

logger = logging.getLogger(__name__)

def init_scheduler(application):
    """Инициализирует планировщик задач с использованием application"""
    global task_scheduler, bot_instance
    
    if task_scheduler is None:
        # Создаем планировщик с правильной конфигурацией для Render
        task_scheduler = AsyncIOScheduler(
            timezone=pytz.timezone('Europe/Moscow'),
            job_defaults={
                'misfire_grace_time': 300,
                'coalesce': True,
                'max_instances': 1
            }
        )
        bot_instance = application.bot
        logger.info("✅ Планировщик задач инициализирован")
    
    return task_scheduler

def validate_image_path(image_path):
    """Проверяет существование файла изображения и возвращает корректный путь"""
    if not image_path:
        return None
    
    # Проверяем существование файла
    if os.path.exists(image_path):
        return image_path
    
    # Пробуем найти файл в разных директориях
    possible_paths = [
        image_path,
        os.path.join('images', os.path.basename(image_path)),
        os.path.join('task_images', os.path.basename(image_path)),
        image_path.replace('\\', '/'),  # Для Windows путей
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"✅ Изображение найдено по альтернативному пути: {path}")
            return path
    
    logger.warning(f"⚠️ Файл изображения не найден: {image_path}")
    return None

async def execute_task(task_id, task_data):
    """Выполняет задачу - отправляет сообщение в указанный чат"""
    global bot_instance
    
    try:
        logger.info(f"🔄 Выполнение задачи: {task_data['template_name']} (ID: {task_id})")
        
        # Определяем чат для отправки
        target_chat_id = task_data.get('target_chat_id')
        
        if not target_chat_id:
            target_chat_id = task_data.get('created_by')
            logger.info(f"⚠️ Целевой чат не указан, отправляем создателю: {target_chat_id}")
        
        if not target_chat_id:
            logger.error(f"❌ Не указан чат для отправки задачи {task_id}")
            return
        
        logger.info(f"📨 Попытка отправки в чат: {target_chat_id}")
        
        # ПОДГОТАВЛИВАЕМ СООБЩЕНИЕ
        message_text = task_data.get('template_text', '')
        image_path = validate_image_path(task_data.get('template_image'))  # ВАЛИДИРУЕМ ПУТЬ
        
        logger.info(f"📊 Данные для отправки: текст='{message_text[:50]}...', изображение='{image_path}'")
        
        # ПРОБУЕМ РАЗНЫЕ ФОРМАТЫ ID ДЛЯ ЧАТОВ
        chat_ids_to_try = [target_chat_id]
        
        if target_chat_id > 0:
            chat_ids_to_try.append(-target_chat_id)
        else:
            chat_ids_to_try.append(abs(target_chat_id))
        
        success = False
        last_error = None
        
        for chat_id in chat_ids_to_try:
            try:
                # ПРОВЕРЯЕМ И ОТПРАВЛЯЕМ ИЗОБРАЖЕНИЕ С ТЕКСТОМ
                if image_path:
                    logger.info(f"🖼️ Попытка отправки изображения: {image_path}")
                    with open(image_path, 'rb') as photo:
                        await bot_instance.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=message_text
                        )
                    logger.info(f"✅ Отправлено фото + текст в чат {chat_id}")
                else:
                    # Если изображения нет, отправляем только текст
                    await bot_instance.send_message(
                        chat_id=chat_id,
                        text=message_text
                    )
                    logger.info(f"✅ Отправлен текст в чат {chat_id}")
                
                success = True
                break
                
            except TelegramError as e:
                last_error = e
                logger.warning(f"⚠️ Не удалось отправить в чат {chat_id}: {e}")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Ошибка отправки в чат {chat_id}: {e}")
                continue
        
        if success:
            # Обновляем время выполнения
            update_task_execution_time(task_id)
            
            # ДЛЯ ТЕСТОВЫХ ЗАДАЧ: деактивируем после выполнения
            if task_data.get('is_test', False):
                success_deactivate, message = deactivate_task(task_id)
                if success_deactivate:
                    logger.info(f"✅ Тестовая задача {task_id} деактивирована после выполнения")
                    unschedule_task(task_id)
                else:
                    logger.error(f"❌ Ошибка деактивации тестовой задачи {task_id}: {message}")
            
            logger.info(f"✅ Задача выполнена: {task_data['template_name']}")
        else:
            logger.error(f"❌ Не удалось отправить сообщение ни в один вариант чата. Последняя ошибка: {last_error}")
            deactivate_task(task_id)
            unschedule_task(task_id)
        
    except Exception as e:
        logger.error(f"❌ Общая ошибка выполнения задачи {task_id}: {e}")

async def execute_test_task(template, update, context, target_chat_id=None):
    """Выполняет тестовую задачу немедленно в указанный чат"""
    try:
        user_id = update.effective_user.id
        
        if not target_chat_id:
            target_chat_id = update.effective_chat.id
        
        logger.info(f"🧪 Выполнение тестовой задачи: {template['name']} в чат {target_chat_id}")
        
        message_text = template.get('text', '')
        image_path = template.get('image')
        
        logger.info(f"📊 Тестовые данные: текст='{message_text[:50]}...', изображение='{image_path}'")

        # ПРОВЕРЯЕМ И ОТПРАВЛЯЕМ ИЗОБРАЖЕНИЕ С ТЕКСТОМ
        if image_path and os.path.exists(image_path):
            logger.info(f"🖼️ Попытка отправки тестового изображения: {image_path}")
            with open(image_path, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=target_chat_id,
                    photo=photo,
                    caption=message_text
                )
            logger.info(f"✅ Тест: отправлено фото + текст в чат {target_chat_id}")
        else:
            # Если изображения нет или файл не существует, отправляем только текст
            if image_path:
                logger.warning(f"⚠️ Файл тестового изображения не найден: {image_path}")
            
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
        hour, minute = map(int, time_str.split(':'))
        
        # Создаем cron триггер для указанных дней
        trigger = CronTrigger(
            day_of_week=','.join(map(str, days)),
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

def unschedule_task(task_id):
    """Удаляет задачу из планировщика"""
    global task_scheduler
    
    if not task_scheduler:
        return False
    
    try:
        # Пытаемся удалить обычную задачу
        if task_scheduler.get_job(task_id):
            task_scheduler.remove_job(task_id)
            logger.info(f"✅ Задача {task_id} удалена из планировщика")
            return True
        
        # Пытаемся удалить тестовую задачу
        test_job_id = f"test_{task_id}"
        if task_scheduler.get_job(test_job_id):
            task_scheduler.remove_job(test_job_id)
            logger.info(f"✅ Тестовая задача {task_id} удалена из планировщика")
            return True
            
        logger.warning(f"⚠️ Задача {task_id} не найдена в планировщике")
        return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка удаления задачи {task_id}: {e}")
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

def get_scheduler_status():
    """Возвращает статус планировщика"""
    global task_scheduler
    
    if not task_scheduler:
        return "❌ Планировщик не инициализирован"
    
    status = "✅ Планировщик запущен\n" if task_scheduler.running else "❌ Планировщик остановлен\n"
    jobs = task_scheduler.get_jobs()
    status += f"📊 Запланировано задач: {len(jobs)}\n"
    
    for job in jobs:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "Не запланировано"
        status += f"  - {job.name}: {next_run}\n"
    
    return status
