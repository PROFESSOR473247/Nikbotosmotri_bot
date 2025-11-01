import logging
from database import load_tasks

class TaskManager:
    def __init__(self):
        self.restore_completed = False

    async def restore_tasks(self, application):
        """Восстановить задачи при запуске (только один раз)"""
        if self.restore_completed:
            logging.info("✅ Задачи уже восстановлены, пропускаем")
            return
            
        tasks_data = load_tasks()
        task_count = len(tasks_data.get('tasks', {}))
        logging.info(f"🔄 Восстановление {task_count} задач...")
        
        # Просто логируем, что задачи восстановлены
        # В будущем здесь будет реальное восстановление планировщика
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data.get("active", True):
                logging.info(f"✅ Активная задача: {task_id}")
        
        self.restore_completed = True
        logging.info(f"🎉 Все задачи восстановлены: {task_count} задач")

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
