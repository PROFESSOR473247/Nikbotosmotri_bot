import json
import logging
import os
from datetime import datetime, time
from telegram.ext import ContextTypes
from database import load_tasks, add_task, remove_task, load_templates

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.test_tasks = {}
        self.restore_completed = False  # Флаг для отслеживания восстановления

    async def restore_tasks(self, application):
        """Восстановить задачи при запуске (только один раз)"""
        if self.restore_completed:
            logging.info("✅ Задачи уже восстановлены, пропускаем")
            return
            
        tasks_data = load_tasks()
        task_count = len(tasks_data.get('tasks', {}))
        logging.info(f"🔄 Восстановление {task_count} задач...")
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            try:
                if task_data.get("active", True):
                    await self.schedule_task(application, task_data)
                    logging.info(f"✅ Восстановлена задача: {task_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка восстановления задачи {task_id}: {e}")
        
        self.restore_completed = True
        logging.info(f"🎉 Все задачи восстановлены: {task_count} задач")

    async def schedule_task(self, application, task_data):
        """Запланировать задачу"""
        try:
            task_type = task_data.get("task_type", "main")
            
            if task_type == "test":
                return  # Тестовые задачи не планируем
            
            # Здесь будет логика планирования задач
            # Пока просто логируем
            logging.info(f"📅 Запланирована задача: {task_data.get('template_name')}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка планирования задачи: {e}")

    async def send_scheduled_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Отправить запланированное сообщение"""
        job = context.job
        task_data = job.data["task_data"]
        
        try:
            templates_data = load_templates()
            template = templates_data["templates"].get(task_data["template_name"], {})
            
            if template:
                text = template.get("text", "")
                image_path = template.get("image")
                
                if image_path and os.path.exists(image_path):
                    with open(image_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=task_data["chat_id"],
                            photo=photo,
                            caption=text
                        )
                else:
                    await context.bot.send_message(
                        chat_id=task_data["chat_id"],
                        text=text
                    )
                logging.info(f"✅ Отправлено сообщение в чат {task_data['chat_id']}")
                
        except Exception as e:
            logging.error(f"❌ Ошибка отправки сообщения: {e}")

    async def create_task(self, user_id, chat_id, template_name, task_type="main", 
                         schedule_time="09:00", days_of_week=None, frequency="1 в неделю"):
        """Создать новую задачу"""
        task_id = f"{chat_id}_{template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "template_name": template_name,
            "task_type": task_type,
            "schedule_time": schedule_time,
            "days_of_week": days_of_week or [],
            "frequency": frequency,
            "created_at": datetime.now().isoformat(),
            "active": True
        }
        
        if add_task(task_id, task_data):
            return True, task_id
        return False, None

    def get_user_tasks(self, user_id):
        """Получить задачи пользователя"""
        tasks_data = load_tasks()
        user_tasks = {}
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data.get("user_id") == user_id:
                user_tasks[task_id] = task_data
                
        return user_tasks

    def deactivate_task(self, task_id):
        """Деактивировать задачу"""
        tasks_data = load_tasks()
        if task_id in tasks_data.get("tasks", {}):
            tasks_data["tasks"][task_id]["active"] = False
            # Здесь нужно добавить сохранение
            return True
        return False

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
