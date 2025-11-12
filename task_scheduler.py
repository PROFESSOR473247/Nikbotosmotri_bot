import schedule
import time
import threading
from datetime import datetime
import logging
from task_manager import load_active_tasks, save_active_tasks
from telegram import Bot
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.bot = Bot(token=bot_token)
        self.is_running = False
        self.scheduler_thread = None

    def start(self):
        """Запускает планировщик задач в отдельном потоке"""
        if self.is_running:
            logger.info("Планировщик уже запущен")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        logger.info("Планировщик задач запущен")

    def stop(self):
        """Останавливает планировщик задач"""
        self.is_running = False
        logger.info("Планировщик задач остановлен")

    def _run_scheduler(self):
        """Запускает цикл планировщика"""
        # Сначала планируем все существующие задачи
        self.schedule_existing_tasks()
        
        # Затем запускаем основной цикл
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                time.sleep(60)

    def schedule_existing_tasks(self):
        """Планирует все активные задачи из файла"""
        tasks = load_active_tasks()
        logger.info(f"Загружено {len(tasks)} активных задач")
        
        # Очищаем существующие задания
        schedule.clear()
        
        for task_id, task in tasks.items():
            if task.get('is_active', False) and not task.get('is_test', False):
                self.schedule_task(task_id, task)

    def schedule_task(self, task_id, task_data):
        """Планирует выполнение задачи"""
        try:
            time_str = task_data.get('time', '00:00')
            days = task_data.get('days', [])
            
            if not days:
                logger.warning(f"Задача {task_id} не имеет дней выполнения")
                return
            
            # Создаем job для каждого дня
            for day in days:
                day_name = self.get_day_name(day)
                if day_name:
                    # Создаем job с передачей task_id и task_data
                    job = schedule.every().__getattribute__(day_name).at(time_str)
                    job.do(self.execute_task, task_id, task_data)
                    logger.info(f"🕐 Запланирована задача '{task_data['template_name']}' на {day_name} в {time_str}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка планирования задачи {task_id}: {e}")

    def get_day_name(self, day_number):
        """Возвращает название дня недели для schedule"""
        day_map = {
            0: "monday",     # Понедельник
            1: "tuesday",    # Вторник
            2: "wednesday",  # Среда
            3: "thursday",   # Четверг
            4: "friday",     # Пятница
            5: "saturday",   # Суббота
            6: "sunday"      # Воскресенье
        }
        return day_map.get(day_number)

    def execute_task(self, task_id, task_data):
        """Выполняет задачу - отправляет сообщение"""
        try:
            logger.info(f"🚀 Выполнение задачи: {task_data['template_name']}")
            
            # Создаем новое событие loop для асинхронного выполнения
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Выполняем отправку сообщения
            loop.run_until_complete(self._send_task_message(task_data))
            loop.close()
            
            # Обновляем время последнего выполнения
            self.update_task_execution_time(task_id)
            
            logger.info(f"✅ Задача '{task_data['template_name']}' выполнена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения задачи {task_id}: {e}")

    async def _send_task_message(self, task_data):
        """Асинхронно отправляет сообщение задачи"""
        try:
            text = task_data.get('template_text', '')
            image_path = task_data.get('template_image')
            group_name = task_data.get('group', '')
            
            # Определяем chat_id на основе группы
            chat_id = self.get_chat_id_by_group(group_name)
            
            if not chat_id:
                logger.error(f"❌ Не найден chat_id для группы: {group_name}")
                return
            
            logger.info(f"📤 Отправка сообщения в чат {chat_id} для группы {group_name}")
            
            if image_path and os.path.exists(image_path):
                # Отправляем изображение с текстом
                with open(image_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text,
                        parse_mode='HTML'
                    )
                logger.info(f"✅ Отправлено фото с текстом в чат {chat_id}")
            else:
                # Отправляем только текст
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Отправлен текст в чат {chat_id}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {e}")

    def get_chat_id_by_group(self, group_name):
        """Возвращает chat_id на основе названия группы"""
        # Здесь нужно настроить соответствие групп и chat_id
        group_chat_map = {
            "hongqi": "-1002128554474",  # Замените на реальный chat_id для Hongqi
            "turbomatiz": "-1002128554474"  # Замените на реальный chat_id для TurboMatiz
        }
        
        # Если группа содержит эмодзи, извлекаем чистый ID
        clean_group = group_name
        if "🚗" in group_name:
            clean_group = "hongqi"
        elif "🚙" in group_name:
            clean_group = "turbomatiz"
        
        return group_chat_map.get(clean_group)

    def update_task_execution_time(self, task_id):
        """Обновляет время выполнения задачи"""
        try:
            tasks = load_active_tasks()
            
            if task_id in tasks:
                tasks[task_id]['last_executed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Пересчитываем следующее выполнение
                next_execution = self.calculate_next_execution(tasks[task_id])
                tasks[task_id]['next_execution'] = next_execution
                
                save_active_tasks(tasks)
                logger.info(f"⏰ Время выполнения задачи {task_id} обновлено")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления времени выполнения: {e}")

    def calculate_next_execution(self, task_data):
        """Вычисляет следующее время выполнения задачи"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        time_str = task_data.get('time', '00:00')
        days = task_data.get('days', [])
        
        try:
            hours, minutes = map(int, time_str.split(':'))
            
            # Находим следующий подходящий день
            for days_ahead in range(1, 8):  # Проверяем следующие 7 дней
                future_date = now + timedelta(days=days_ahead)
                future_weekday = future_date.weekday()
                
                if future_weekday in days:
                    next_time = future_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    return next_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Если не нашли подходящий день в ближайшую неделю
            return "Не определено"
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета следующего выполнения: {e}")
            return "Ошибка расчета"

# Глобальный экземпляр планировщика
task_scheduler = None

def init_scheduler(bot_token):
    """Инициализирует глобальный планировщик"""
    global task_scheduler
    task_scheduler = TaskScheduler(bot_token)
    return task_scheduler

async def execute_test_task(template_data, update, context):
    """Немедленно выполняет тестовую задачу"""
    try:
        bot = context.bot
        text = template_data.get('text', '')
        image_path = template_data.get('image')
        group_name = template_data.get('group', '')
        
        logger.info(f"🧪 Запуск тестовой задачи для группы: {group_name}")
        
        # Определяем chat_id для теста (можно отправлять в личный чат или группу)
        test_chat_id = update.effective_chat.id  # Отправляем в чат с пользователем
        
        if image_path and os.path.exists(image_path):
            # Отправляем изображение с текстом
            with open(image_path, 'rb') as photo:
                await bot.send_photo(
                    chat_id=test_chat_id,
                    photo=photo,
                    caption=f"🧪 **ТЕСТОВОЕ СООБЩЕНИЕ**\n\n{text}",
                    parse_mode='Markdown'
                )
            logger.info("✅ Тестовое сообщение с фото отправлено")
        else:
            # Отправляем только текст
            await bot.send_message(
                chat_id=test_chat_id,
                text=f"🧪 **ТЕСТОВОЕ СООБЩЕНИЕ**\n\n{text}",
                parse_mode='Markdown'
            )
            logger.info("✅ Тестовое сообщение с текстом отправлено")
            
        logger.info("✅ Тестовая задача выполнена успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения тестовой задачи: {e}")
        from keyboards.task_keyboards import get_tasks_main_keyboard
        await update.message.reply_text(
            f"❌ Ошибка отправки тестового сообщения: {e}",
            reply_markup=get_tasks_main_keyboard()
        )

# Добавим импорт os в начало файла
import os