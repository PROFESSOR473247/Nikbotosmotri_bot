import logging
from database import load_tasks

class TaskManager:
    def __init__(self):
        self.restore_completed = False

    async def restore_tasks(self, application):
        """Восстановить задачи при запуске"""
        if self.restore_completed:
            logging.info("✅ Задачи уже восстановлены, пропускаем")
            return
            
        tasks_data = load_tasks()
        task_count = len(tasks_data.get('tasks', {}))
        logging.info(f"🔄 Восстановление {task_count} задач...")
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data.get("active", True):
                logging.info(f"✅ Активная задача: {task_id}")
        
        self.restore_completed = True
        logging.info(f"🎉 Все задачи восстановлены: {task_count} задач")

    async def show_tasks_menu(self, update, context):
        """Показать меню задач"""
        from menu_manager import get_tasks_menu
        await update.message.reply_text("📋 УПРАВЛЕНИЕ ЗАДАЧАМИ", reply_markup=get_tasks_menu())

    async def show_templates_menu(self, update, context):
        """Показать меню шаблонов"""
        from menu_manager import get_templates_menu
        await update.message.reply_text("📁 УПРАВЛЕНИЕ ШАБЛОНАМИ", reply_markup=get_templates_menu())

    async def handle_button(self, update, context):
        """Обработчик кнопок"""
        query = update.callback_query
        await query.answer("Функция в разработке 🛠️")

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
