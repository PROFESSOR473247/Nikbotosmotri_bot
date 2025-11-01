import json
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
import pytz
from database import load_tasks, save_tasks, add_task, remove_task
from templates import TEMPLATES

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.test_tasks = {}

    async def restore_tasks(self, application):
        """Восстановление задач при запуске бота"""
        tasks_data = load_tasks()
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            try:
                chat_id = task_data["chat_id"]
                template_name = task_data["template_name"]
                schedule_type = task_data.get("schedule_type", "main")
                
                if schedule_type == "main":
                    await self.schedule_main_task(application, chat_id, template_name, task_data)
                elif schedule_type == "test":
                    # Тестовые задачи не восстанавливаются
                    continue
                    
            except Exception as e:
                logging.error(f"Ошибка восстановления задачи {task_id}: {e}")

    async def schedule_main_task(self, application, chat_id, template_name, task_data):
        """Планирование основной задачи"""
        try:
            # Здесь будет логика планирования на основе task_data
            # Пока упрощенная версия
            if template_name in TEMPLATES:
                if chat_id not in self.active_tasks:
                    self.active_tasks[chat_id] = {}
                
                # Создаем задание (упрощенно - нужно доработать под конкретное расписание)
                job = application.job_queue.run_daily(
                    self.send_scheduled_message,
                    time=task_data.get("scheduled_time", datetime.now().time()),
                    days=tuple(task_data.get("days", (0,))),
                    chat_id=chat_id,
                    data={"template_name": template_name, "chat_id": chat_id}
                )
                
                self.active_tasks[chat_id][template_name] = job
                logging.info(f"✅ Восстановлена задача: {template_name} для чата {chat_id}")
                
        except Exception as e:
            logging.error(f"Ошибка планирования задачи: {e}")

    async def send_scheduled_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправка запланированного сообщения"""
        job = context.job
        template_name = job.data["template_name"]
        chat_id = job.data["chat_id"]
        
        try:
            if template_name in TEMPLATES:
                template = TEMPLATES[template_name]
                text = template["text"]
                image_path = template.get("image")
                
                if image_path and os.path.exists(image_path):
                    with open(image_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=text
                        )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=text
                    )
                logging.info(f"✅ Отправлено запланированное сообщение {template_name} в чат {chat_id}")
                
        except Exception as e:
            logging.error(f"Ошибка отправки запланированного сообщения: {e}")

    async def create_task(self, user_id, group_id, template_name, task_type="main"):
        """Создание новой задачи"""
        task_id = f"{group_id}_{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "group_id": group_id,
            "template_name": template_name,
            "task_type": task_type,
            "created_at": datetime.now().isoformat(),
            "schedule_type": "main" if task_type == "main" else "test"
        }
        
        if add_task(task_id, task_data):
            return True, task_id
        return False, None

    def get_user_tasks(self, user_id):
        """Получение задач пользователя"""
        tasks_data = load_tasks()
        user_tasks = {}
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data["user_id"] == user_id:
                user_tasks[task_id] = task_data
                
        return user_tasks

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
