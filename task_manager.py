import json
import logging
import os
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import ContextTypes
import pytz
from database import load_tasks, save_tasks, add_task, remove_task, load_templates

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.test_tasks = {}

    async def restore_tasks(self, application):
        """Restore all tasks on bot startup"""
        tasks_data = load_tasks()
        logging.info(f"Restoring {len(tasks_data.get('tasks', {}))} tasks...")
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            try:
                if task_data.get("active", True):
                    await self.schedule_task(application, task_data)
                    logging.info(f"Restored task: {task_id}")
            except Exception as e:
                logging.error(f"Error restoring task {task_id}: {e}")

    async def schedule_task(self, application, task_data):
        """Schedule a task based on its configuration"""
        try:
            task_type = task_data.get("task_type", "main")
            template_name = task_data["template_name"]
            chat_id = task_data["chat_id"]
            
            if task_type == "test":
                # Test tasks are one-time and immediate
                return
            
            # Get schedule configuration
            schedule_time = task_data.get("schedule_time", "09:00")
            days_of_week = task_data.get("days_of_week", [])
            frequency = task_data.get("frequency", "1 в неделю")
            
            # Parse time
            time_obj = datetime.strptime(schedule_time, "%H:%M").time()
            
            if frequency == "1 в неделю":
                # Schedule for specific day of week
                if days_of_week:
                    job = application.job_queue.run_daily(
                        self.send_scheduled_message,
                        time=time_obj,
                        days=tuple(days_of_week),
                        data={"task_data": task_data}
                    )
                    self.active_tasks[task_data["task_id"]] = job
                    
            elif frequency == "2 в неделю":
                # Schedule for two specific days
                if len(days_of_week) >= 2:
                    for day in days_of_week[:2]:
                        job = application.job_queue.run_daily(
                            self.send_scheduled_message,
                            time=time_obj,
                            days=(day,),
                            data={"task_data": task_data}
                        )
                        self.active_tasks[f"{task_data['task_id']}_{day}"] = job
                        
            elif frequency in ["1 в месяц", "2 в месяц"]:
                # Monthly scheduling - run monthly with day check
                job = application.job_queue.run_daily(
                    self.send_scheduled_message,
                    time=time_obj,
                    data={"task_data": task_data}
                )
                self.active_tasks[task_data["task_id"]] = job
                
        except Exception as e:
            logging.error(f"Error scheduling task: {e}")

    async def send_scheduled_message(self, context: ContextTypes.DEFAULT_TYPE):
        """Send scheduled message"""
        job = context.job
        task_data = job.data["task_data"]
        
        # For monthly tasks, check if it's the correct day
        frequency = task_data.get("frequency", "1 в неделю")
        if frequency in ["1 в месяц", "2 в месяц"]:
            today = datetime.now().day
            if frequency == "1 в месяц" and today != 1:  # 1st of month
                return
            elif frequency == "2 в месяц" and today not in [1, 15]:  # 1st and 15th
                return
        
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
                logging.info(f"Sent scheduled message to chat {task_data['chat_id']}")
                
        except Exception as e:
            logging.error(f"Error sending scheduled message: {e}")

    async def create_task(self, user_id, chat_id, template_name, task_type="main", 
                         schedule_time="09:00", days_of_week=None, frequency="1 в неделю"):
        """Create new task with full configuration"""
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
        """Get all tasks for user"""
        tasks_data = load_tasks()
        user_tasks = {}
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data["user_id"] == user_id:
                user_tasks[task_id] = task_data
                
        return user_tasks

    def deactivate_task(self, task_id):
        """Deactivate task"""
        tasks_data = load_tasks()
        if task_id in tasks_data.get("tasks", {}):
            tasks_data["tasks"][task_id]["active"] = False
            return save_tasks(tasks_data)
        return False

    async def send_test_message(self, context: ContextTypes.DEFAULT_TYPE, task_data):
        """Send test message immediately"""
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
                return True
            return False
                
        except Exception as e:
            logging.error(f"Error sending test message: {e}")
            return False

# Global task manager instance
task_manager = TaskManager()
