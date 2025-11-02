import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import pytz
from database import load_tasks, save_tasks, load_templates, get_user_accessible_groups
from authorized_users import is_authorized, get_user_role

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.restore_completed = False

    async def restore_tasks(self, application):
        """Восстановить активные задачи при запуске"""
        if self.restore_completed:
            return
            
        tasks_data = load_tasks()
        active_count = 0
        
        for task_id, task_data in tasks_data.get("tasks", {}).items():
            if task_data.get("active", True):
                self.active_tasks[task_id] = task_data
                active_count += 1
                
                # Здесь будет логика восстановления планировщика задач
                # Пока просто логируем
                logging.info(f"✅ Восстановлена активная задача: {task_id}")
        
        self.restore_completed = True
        logging.info(f"🎉 Восстановление завершено: {active_count} активных задач")

    async def show_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню задач"""
        user_id = update.effective_user.id
        from menu_manager import get_tasks_menu
        
        keyboard = get_tasks_menu()
        await update.message.reply_text("📋 УПРАВЛЕНИЕ ЗАДАЧАМИ", reply_markup=keyboard)

    async def show_templates_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню шаблонов"""
        user_id = update.effective_user.id
        user_role = get_user_role(user_id)
        
        if user_role in ["гость", "водитель"]:
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        from menu_manager import get_templates_menu
        await update.message.reply_text("📁 УПРАВЛЕНИЕ ШАБЛОНАМИ", reply_markup=get_templates_menu())

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        data = query.data
        
        if data == "task_status":
            await self.show_task_status(update, context)
        elif data == "template_list":
            await self.show_template_groups(update, context)
        elif data.startswith("group_select_"):
            group_id = data.replace("group_select_", "")
            await self.show_group_templates(update, context, group_id)

    async def show_task_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус активных задач"""
        user_id = update.effective_user.id
        
        if not self.active_tasks:
            await update.callback_query.edit_message_text("📊 Нет активных задач")
            return
        
        status_text = "📊 СТАТУС АКТИВНЫХ ЗАДАЧ:\n\n"
        
        for task_id, task_data in self.active_tasks.items():
            status_text += f"🔹 {task_data.get('template_name', 'Неизвестно')}\n"
            status_text += f"   📍 Группа: {task_data.get('group_name', 'Неизвестно')}\n"
            status_text += f"   ⏰ Время: {task_data.get('schedule_time', 'Неизвестно')}\n"
            status_text += f"   🔄 Периодичность: {task_data.get('frequency', 'Неизвестно')}\n"
            status_text += f"   🆔 ID: {task_id}\n\n"
        
        await update.callback_query.edit_message_text(status_text)

    async def show_template_groups(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать группы шаблонов"""
        user_id = update.effective_user.id
        accessible_groups = get_user_accessible_groups(user_id)
        
        if not accessible_groups:
            await update.callback_query.edit_message_text("❌ Нет доступных групп")
            return
        
        keyboard = []
        for group_id, group_info in accessible_groups.items():
            keyboard.append([InlineKeyboardButton(
                f"🏘️ {group_info.get('title', group_id)}", 
                callback_data=f"group_select_{group_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_templates")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            "📁 ВЫБЕРИТЕ ГРУППУ ШАБЛОНОВ:",
            reply_markup=reply_markup
        )

    async def show_group_templates(self, update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: str):
        """Показать шаблоны в группе"""
        templates_data = load_templates()
        group_templates = []
        
        for template_id, template in templates_data.get("templates", {}).items():
            if template.get('group') == group_id:
                group_templates.append((template_id, template))
        
        if not group_templates:
            await update.callback_query.edit_message_text("❌ В этой группе нет шаблонов")
            return
        
        keyboard = []
        for template_id, template in group_templates:
            keyboard.append([InlineKeyboardButton(
                f"📝 {template.get('name', 'Без названия')}", 
                callback_data=f"template_view_{template_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад к группам", callback_data="template_list")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(
            f"📋 ШАБЛОНЫ В ГРУППЕ:",
            reply_markup=reply_markup
        )

    def create_task(self, task_data):
        """Создать новую задачу"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_data['created_at'] = datetime.now().isoformat()
        task_data['active'] = True
        
        self.active_tasks[task_id] = task_data
        
        # Сохраняем в базу данных
        tasks_data = load_tasks()
        tasks_data["tasks"][task_id] = task_data
        save_tasks(tasks_data)
        
        logging.info(f"✅ Создана новая задача: {task_id}")
        return task_id

    def deactivate_task(self, task_id):
        """Деактивировать задачу"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id]['active'] = False
            del self.active_tasks[task_id]
            
            # Обновляем в базе данных
            tasks_data = load_tasks()
            if task_id in tasks_data["tasks"]:
                tasks_data["tasks"][task_id]['active'] = False
                save_tasks(tasks_data)
            
            logging.info(f"✅ Задача деактивирована: {task_id}")
            return True
        return False

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
