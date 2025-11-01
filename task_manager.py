import json
import logging
import os
from datetime import datetime
from telegram.ext import ContextTypes
from database import load_tasks, add_task, remove_task
from templates import TEMPLATES

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.test_tasks = {}

    async def restore_tasks(self, application):
        """Restore tasks on bot startup - simplified for now"""
        print("🔧 Task restoration temporarily disabled for stability")
        # This will be implemented after basic bot works
        pass

    async def send_scheduled_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Send scheduled message"""
        try:
            job = context.job
            template_name = job.data["template_name"]
            chat_id = job.data["chat_id"]
            
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
                logging.info(f"✅ Sent scheduled message {template_name} to chat {chat_id}")
                
        except Exception as e:
            logging.error(f"❌ Error sending scheduled message: {e}")

    async def create_task(self, user_id, group_id, template_name, task_type="main"):
        """Create new task"""
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
        """Get user tasks"""
        tasks_data = load_tasks()
        user_tasks = {}
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data.get("user_id") == user_id:
                user_tasks[task_id] = task_data
                
        return user_tasks

# Global task manager instance
task_manager = TaskManager()
