import logging
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import pytz
from datetime import datetime, timedelta
from telegram.error import TelegramError

# Глобальный планировщик
task_scheduler = None
bot_instance = None

logger = logging.getLogger(__name__)

def init_scheduler(application):
    """Инициализирует планировщик задач"""
    global task_scheduler, bot_instance
    
    if task_scheduler is None:
        task_scheduler = AsyncIOScheduler()
        bot_instance = application.bot
        logger.info("✅ Планировщик задач инициализирован")
    
    return task_scheduler

# ... остальной код task_scheduler.py остается без изменений

def schedule_all_tasks():
    """Планирует все активные задачи из базы данных"""
    try:
        print("📋 Загрузка активных задач для планирования...")
        
        # Получаем все активные задачи
        active_tasks = get_all_active_tasks()
        
        print(f"📊 Найдено активных задач: {len(active_tasks)}")
        
        # Очищаем существующие задачи
        task_scheduler.remove_all_jobs()
        
        # Планируем каждую задачу
        for task_id, task_data in active_tasks.items():
            schedule_task(task_id, task_data)
        
        print(f"✅ Все задачи запланированы: {len(active_tasks)} задач")
        
    except Exception as e:
        print(f"❌ Ошибка при планировании задач: {e}")
        import traceback
        traceback.print_exc()

def schedule_task(task_id, task_data):
    """Планирует выполнение одной задачи"""
    try:
        if not task_data.get('is_active', True):
            print(f"⏭️ Задача {task_id} неактивна, пропускаем")
            return
        
        time_str = task_data.get('time')
        days = task_data.get('days', [])
        
        if not time_str or not days:
            print(f"⏭️ Задача {task_id} не имеет времени или дней выполнения, пропускаем")
            return
        
        # Парсим время
        hour, minute = map(int, time_str.split(':'))
        
        # Создаем триггеры для каждого дня
        for day in days:
            try:
                day_int = int(day)
                if 0 <= day_int <= 6:  # 0-понедельник, 6-воскресенье
                    # Создаем cron триггер для конкретного дня недели
                    trigger = CronTrigger(
                        day_of_week=day_int,
                        hour=hour,
                        minute=minute,
                        timezone=pytz.timezone('Europe/Moscow')
                    )
                    
                    # Добавляем задачу в планировщик
                    task_scheduler.add_job(
                        execute_task,
                        trigger=trigger,
                        args=[task_id, task_data],
                        id=f"{task_id}_day_{day}",
                        replace_existing=True
                    )
                    
                    print(f"✅ Задача {task_id} запланирована на {day_int} день в {time_str}")
                
            except ValueError as e:
                print(f"⚠️ Ошибка парсинга дня {day} для задачи {task_id}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Ошибка планирования задачи {task_id}: {e}")
        import traceback
        traceback.print_exc()

async def execute_task(task_id, task_data):
    """Выполняет задачу - отправляет сообщение в целевой чат"""
    try:
        print(f"🚀 Выполнение задачи: {task_data['template_name']} (ID: {task_id})")
        
        # Получаем ID целевого чата
        target_chat_id = task_data.get('target_chat_id')
        
        if not target_chat_id:
            print(f"❌ Для задачи {task_id} не указан целевой чат")
            return
        
        # Проверяем, что приложение инициализировано
        if not application:
            print(f"❌ Приложение не инициализировано для задачи {task_id}")
            return
        
        # Получаем текст и изображение
        message_text = task_data.get('template_text', '')
        image_path = task_data.get('template_image')
        
        if not message_text:
            print(f"❌ Для задачи {task_id} отсутствует текст сообщения")
            return
        
        # Добавляем информацию о задаче в сообщение
        formatted_message = format_task_message(message_text, task_data)
        
        print(f"📤 Отправка сообщения в чат {target_chat_id}")
        
        # Отправляем сообщение в целевой чат
        try:
            if image_path and os.path.exists(image_path):
                # Отправляем сообщение с изображением
                with open(image_path, 'rb') as photo:
                    await application.bot.send_photo(
                        chat_id=target_chat_id,
                        photo=photo,
                        caption=formatted_message,
                        parse_mode='Markdown'
                    )
                print(f"✅ Сообщение с изображением отправлено в чат {target_chat_id}")
            else:
                # Отправляем текстовое сообщение
                await application.bot.send_message(
                    chat_id=target_chat_id,
                    text=formatted_message,
                    parse_mode='Markdown'
                )
                print(f"✅ Текстовое сообщение отправлено в чат {target_chat_id}")
            
            # Обновляем время последнего выполнения
            next_execution = calculate_next_execution(task_data['time'], task_data['days'])
            update_task_execution_time(task_id, next_execution)
            
            print(f"✅ Задача {task_id} успешно выполнена")
            
        except Exception as send_error:
            print(f"❌ Ошибка отправки сообщения для задачи {task_id}: {send_error}")
            # Пытаемся отправить просто текстовое сообщение в случае ошибки
            try:
                await application.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"📅 *Напоминание:*\n\n{message_text}",
                    parse_mode='Markdown'
                )
                print(f"✅ Альтернативное сообщение отправлено в чат {target_chat_id}")
                
                # Все равно обновляем время выполнения
                next_execution = calculate_next_execution(task_data['time'], task_data['days'])
                update_task_execution_time(task_id, next_execution)
                
            except Exception as fallback_error:
                print(f"❌ Критическая ошибка отправки для задачи {task_id}: {fallback_error}")
        
    except Exception as e:
        print(f"❌ Ошибка выполнения задачи {task_id}: {e}")
        import traceback
        traceback.print_exc()

def format_task_message(message_text, task_data):
    """Форматирует сообщение для отправки"""
    try:
        template_name = task_data.get('template_name', 'Напоминание')
        
        # Базовое форматирование
        formatted_message = f"📅 *{template_name}*\n\n{message_text}"
        
        # Добавляем информацию о времени, если есть
        time_str = task_data.get('time')
        if time_str:
            formatted_message += f"\n\n⏰ *Время:* {time_str} (МСК)"
        
        # Добавляем информацию о периодичности
        frequency = task_data.get('frequency')
        if frequency:
            frequency_map = {
                "weekly": "еженедельно",
                "2_per_month": "2 раза в месяц",
                "monthly": "ежемесячно"
            }
            freq_text = frequency_map.get(frequency, frequency)
            formatted_message += f"\n🔄 *Повтор:* {freq_text}"
        
        return formatted_message
        
    except Exception as e:
        print(f"⚠️ Ошибка форматирования сообщения: {e}")
        return f"📅 *Напоминание:*\n\n{message_text}"

async def execute_test_task(template, update: Update, context: ContextTypes.DEFAULT_TYPE, target_chat_id=None):
    """Выполняет тестовую задачу - отправляет сообщение сразу"""
    try:
        print(f"🧪 Выполнение тестовой задачи: {template.get('name', 'Без названия')}")
        
        # Если указан целевой чат, отправляем туда, иначе в личные сообщения
        chat_id = target_chat_id if target_chat_id else update.effective_chat.id
        
        message_text = template.get('text', '')
        image_path = template.get('image')
        
        if not message_text:
            await update.message.reply_text("❌ В шаблоне отсутствует текст сообщения")
            return
        
        # Форматируем сообщение для теста
        test_message = format_test_message(message_text, template)
        
        print(f"📤 Тестовая отправка в чат {chat_id}")
        
        try:
            if image_path and os.path.exists(image_path):
                # Отправляем сообщение с изображением
                with open(image_path, 'rb') as photo:
                    if target_chat_id:
                        # Отправляем в целевой чат
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=test_message,
                            parse_mode='Markdown'
                        )
                    else:
                        # Отправляем в личные сообщения
                        await update.message.reply_photo(
                            photo=photo,
                            caption=test_message,
                            parse_mode='Markdown'
                        )
                print(f"✅ Тестовое сообщение с изображением отправлено")
            else:
                # Отправляем текстовое сообщение
                if target_chat_id:
                    # Отправляем в целевой чат
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=test_message,
                        parse_mode='Markdown'
                    )
                else:
                    # Отправляем в личные сообщения
                    await update.message.reply_text(
                        test_message,
                        parse_mode='Markdown'
                    )
                print(f"✅ Тестовое текстовое сообщение отправлено")
            
            # Для тестовых задач в личных сообщениях добавляем информацию
            if not target_chat_id:
                await update.message.reply_text(
                    "✅ *Тестовое сообщение отправлено!*\n\n"
                    "В реальной задаче сообщение будет отправляться автоматически "
                    "в указанное время в выбранный Telegram чат.",
                    parse_mode='Markdown'
                )
            
        except Exception as send_error:
            error_msg = f"❌ Ошибка отправки тестового сообщения: {send_error}"
            print(error_msg)
            await update.message.reply_text(error_msg)
            
            # Пытаемся отправить просто текстовое сообщение
            try:
                if target_chat_id:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🧪 *Тестовое сообщение:*\n\n{message_text}",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        f"🧪 *Тестовое сообщение:*\n\n{message_text}",
                        parse_mode='Markdown'
                    )
                print("✅ Альтернативное тестовое сообщение отправлено")
            except Exception as fallback_error:
                print(f"❌ Критическая ошибка тестовой отправки: {fallback_error}")
        
    except Exception as e:
        error_msg = f"❌ Ошибка выполнения тестовой задачи: {e}"
        print(error_msg)
        await update.message.reply_text(error_msg)
        import traceback
        traceback.print_exc()

def format_test_message(message_text, template):
    """Форматирует тестовое сообщение"""
    try:
        template_name = template.get('name', 'Тестовое напоминание')
        time_str = template.get('time', 'Не указано')
        
        days = template.get('days', [])
        days_names = []
        if days:
            DAYS_OF_WEEK = {
                '0': 'Понедельник', '1': 'Вторник', '2': 'Среда',
                '3': 'Четверг', '4': 'Пятница', '5': 'Суббота', '6': 'Воскресенье'
            }
            days_names = [DAYS_OF_WEEK.get(str(day), f"День {day}") for day in days]
        
        frequency = template.get('frequency', 'weekly')
        frequency_map = {
            "weekly": "еженедельно",
            "2_per_month": "2 раза в месяц", 
            "monthly": "ежемесячно"
        }
        freq_text = frequency_map.get(frequency, frequency)
        
        test_message = f"🧪 *ТЕСТОВОЕ СООБЩЕНИЕ*\n\n"
        test_message += f"📝 *Шаблон:* {template_name}\n"
        test_message += f"⏰ *Время отправки:* {time_str} (МСК)\n"
        
        if days_names:
            test_message += f"📅 *Дни отправки:* {', '.join(days_names)}\n"
        
        test_message += f"🔄 *Периодичность:* {freq_text}\n\n"
        test_message += f"---\n\n{message_text}\n\n---\n\n"
        test_message += "_Это тестовое сообщение. В реальной задаче это уведомление будет отсутствовать._"
        
        return test_message
        
    except Exception as e:
        print(f"⚠️ Ошибка форматирования тестового сообщения: {e}")
        return f"🧪 *ТЕСТОВОЕ СООБЩЕНИЕ*\n\n{message_text}"

def reschedule_task(task_id, task_data):
    """Перепланирует задачу (например, после редактирования)"""
    try:
        # Удаляем старые задания для этой задачи
        remove_task_schedule(task_id)
        
        # Планируем заново
        schedule_task(task_id, task_data)
        
        print(f"✅ Задача {task_id} перепланирована")
        
    except Exception as e:
        print(f"❌ Ошибка перепланирования задачи {task_id}: {e}")

def remove_task_schedule(task_id):
    """Удаляет задачу из расписания"""
    try:
        jobs_removed = 0
        
        # Ищем и удаляем все задания для этой задачи
        for job in task_scheduler.get_jobs():
            if job.id.startswith(f"{task_id}_day_"):
                job.remove()
                jobs_removed += 1
        
        if jobs_removed > 0:
            print(f"✅ Удалено {jobs_removed} заданий для задачи {task_id}")
        else:
            print(f"ℹ️ Не найдено заданий для удаления задачи {task_id}")
            
    except Exception as e:
        print(f"❌ Ошибка удаления задачи {task_id} из расписания: {e}")

def stop_scheduler():
    """Останавливает планировщик задач"""
    global task_scheduler
    if task_scheduler:
        task_scheduler.shutdown()
        print("🛑 Планировщик задач остановлен")

def get_scheduler_status():
    """Возвращает статус планировщика"""
    if not task_scheduler:
        return "❌ Планировщик не инициализирован"
    
    jobs = task_scheduler.get_jobs()
    active_tasks = get_all_active_tasks()
    
    status = f"📊 **Статус планировщика:**\n\n"
    status += f"✅ Планировщик активен\n"
    status += f"📋 Запланировано заданий: {len(jobs)}\n"
    status += f"📁 Активных задач в базе: {len(active_tasks)}\n"
    
    if jobs:
        status += f"\n⏰ **Ближайшие выполнения:**\n"
        next_jobs = sorted(jobs, key=lambda x: x.next_run_time)[:5]  # Показываем 5 ближайших
        
        for i, job in enumerate(next_jobs, 1):
            task_id = job.id.split('_day_')[0]
            task = active_tasks.get(task_id, {})
            task_name = task.get('template_name', 'Неизвестная задача')
            next_run = job.next_run_time.astimezone(pytz.timezone('Europe/Moscow'))
            
            status += f"{i}. **{task_name}** - {next_run.strftime('%d.%m.%Y %H:%M')}\n"
    
    return status

async def send_scheduler_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет статус планировщика"""
    status = get_scheduler_status()
    await update.message.reply_text(status, parse_mode='Markdown')

# Функция для периодической проверки и перепланирования задач
def schedule_periodic_check():
    """Планирует периодическую проверку задач"""
    if task_scheduler:
        # Проверяем каждые 10 минут
        task_scheduler.add_job(
            check_and_reschedule_tasks,
            'interval',
            minutes=10,
            id='periodic_task_check'
        )
        print("✅ Периодическая проверка задач запланирована")

def check_and_reschedule_tasks():
    """Проверяет и перепланирует задачи при необходимости"""
    try:
        print("🔍 Периодическая проверка задач...")
        
        active_tasks = get_all_active_tasks()
        scheduled_jobs = task_scheduler.get_jobs()
        
        # Собираем ID запланированных задач
        scheduled_task_ids = set()
        for job in scheduled_jobs:
            if job.id != 'periodic_task_check':
                task_id = job.id.split('_day_')[0]
                scheduled_task_ids.add(task_id)
        
        # Проверяем, все ли активные задачи запланированы
        for task_id in active_tasks.keys():
            if task_id not in scheduled_task_ids:
                print(f"⚠️ Задача {task_id} активна, но не запланирована. Перепланируем...")
                schedule_task(task_id, active_tasks[task_id])
        
        print("✅ Проверка задач завершена")
        
    except Exception as e:
        print(f"❌ Ошибка при периодической проверке задач: {e}")

# Инициализация при импорте
print("📥 Task_scheduler загружен")
