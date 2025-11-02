# -*- coding: utf-8 -*-
import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
import pytz

from database import (
    load_tasks, save_tasks, load_templates, get_user_accessible_groups, 
    is_authorized, get_user_role, get_template_by_id, get_active_tasks,
    add_task, remove_task, deactivate_task
)
from menu_manager import (
    get_groups_keyboard, get_subgroups_keyboard,
    get_templates_keyboard, get_confirmation_keyboard, get_back_button
)

# Состояния для создания задачи
TASK_GROUP, TASK_SUBGROUP, TASK_TEMPLATE, TASK_CHANNEL, TASK_CONFIRM, TASK_EDIT = range(6)

# Состояния для отмены задачи
CANCEL_TASK_GROUP, CANCEL_TASK_SUBGROUP, CANCEL_TASK_SELECT, CANCEL_TASK_CONFIRM = range(4)

class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.restore_completed = False

    async def restore_tasks(self, application):
        """Восстановить активные задачи при запуске"""
        if self.restore_completed:
            logging.info("✅ Задачи уже восстановлены, пропускаем")
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
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
            
        from menu_manager import get_tasks_menu
        keyboard = get_tasks_menu()
        await update.message.reply_text("📋 УПРАВЛЕНИЕ ЗАДАЧАМИ", reply_markup=keyboard)

    # =============================================================================
    # СОЗДАНИЕ ЗАДАЧИ
    # =============================================================================

    async def start_create_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание новой задачи"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        context.user_data['task_creation'] = {
            'user_id': user_id,
            'step': 'group'
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ СОЗДАНИЯ ЗАДАЧИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TASK_GROUP

    async def task_group_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['task_creation']['group_id'] = group_id
            
            # Получаем подгруппы
            from database import load_groups
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}'*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return TASK_SUBGROUP
            else:
                # Пропускаем шаг подгруппы
                context.user_data['task_creation']['subgroup_id'] = None
                return await self.show_templates_for_task(update, context)

    async def task_subgroup_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = parts[1]
            
            context.user_data['task_creation']['subgroup_id'] = subgroup_id
            return await self.show_templates_for_task(update, context)

    async def show_templates_for_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать шаблоны для создания задачи"""
        task_data = context.user_data['task_creation']
        group_id = task_data['group_id']
        subgroup_id = task_data.get('subgroup_id')
        
        # Получаем шаблоны
        from database import get_group_templates, get_subgroup_templates
        
        if subgroup_id:
            templates = get_subgroup_templates(group_id, subgroup_id)
        else:
            templates = get_group_templates(group_id)
        
        if not templates:
            await update.callback_query.edit_message_text("❌ В выбранной группе/подгруппе нет шаблонов")
            return ConversationHandler.END
        
        context.user_data['task_creation']['templates'] = templates
        keyboard = get_templates_keyboard(templates)
        
        from database import load_groups
        groups_data = load_groups()
        group_name = groups_data.get("groups", {}).get(group_id, {}).get('name', group_id)
        
        if subgroup_id:
            subgroup_name = groups_data.get("groups", {}).get(group_id, {}).get('subgroups', {}).get(subgroup_id, subgroup_id)
            message_text = f"📝 *ВЫБЕРИТЕ ШАБЛОН ИЗ ПОДГРУППЫ '{subgroup_name}'*"
        else:
            message_text = f"📝 *ВЫБЕРИТЕ ШАБЛОН ИЗ ГРУППЫ '{group_name}'*"
        
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TASK_TEMPLATE

    async def task_template_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора шаблона для задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("select_template_"):
            template_id = data.replace("select_template_", "")
            template = get_template_by_id(template_id)
            
            if not template:
                await query.edit_message_text("❌ Шаблон не найден")
                return ConversationHandler.END
            
            context.user_data['task_creation']['template_id'] = template_id
            context.user_data['task_creation']['template'] = template
            
            # Здесь будет выбор Telegram канала
            # Пока используем заглушку
            context.user_data['task_creation']['channel_id'] = "-100123456789"  # Заглушка
            context.user_data['task_creation']['channel_name'] = "Тестовый канал"
            
            return await self.show_task_confirmation(update, context)

    async def show_task_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение создания задачи"""
        task_data = context.user_data['task_creation']
        template = task_data['template']
        
        confirmation_text = self._format_task_confirmation(task_data)
        
        keyboard = get_confirmation_keyboard("confirm_task", "edit_task")
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(
                confirmation_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                confirmation_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        return TASK_CONFIRM

    def _format_task_confirmation(self, task_data):
        """Форматирование подтверждения задачи"""
        template = task_data['template']
        
        text = "✅ *ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ЗАДАЧИ*\n\n"
        
        text += f"📝 *Шаблон:* {template.get('name', 'Без названия')}\n"
        text += f"📋 *Текст:* {template.get('text', '')[:50]}...\n"
        
        if template.get('image'):
            text += f"🖼️ *С изображением:* Да\n"
        else:
            text += f"🖼️ *С изображением:* Нет\n"
        
        text += f"🏘️ *Группа:* {task_data.get('group_id')}\n"
        
        if task_data.get('subgroup_id'):
            text += f"📁 *Подгруппа:* {task_data.get('subgroup_id')}\n"
        
        text += f"📢 *Канал:* {task_data.get('channel_name', 'Не указан')}\n"
        text += f"⏰ *Время:* {template.get('schedule_time', 'Не указано')}\n"
        text += f"🔄 *Периодичность:* {template.get('frequency', 'Не указана')}\n\n"
        
        if template.get('days'):
            days_str = ", ".join(template['days'])
            text += f"📅 *Дни:* {days_str}\n\n"
        
        text += "❓ *Все верно?*"
        
        return text

    async def task_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения создания задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_task":
            # Создаем задачу
            task_data = context.user_data['task_creation']
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            task_to_save = {
                'task_id': task_id,
                'template_id': task_data['template_id'],
                'template_name': task_data['template'].get('name'),
                'group_id': task_data['group_id'],
                'subgroup_id': task_data.get('subgroup_id'),
                'channel_id': task_data['channel_id'],
                'channel_name': task_data['channel_name'],
                'schedule_time': task_data['template'].get('schedule_time'),
                'frequency': task_data['template'].get('frequency'),
                'days': task_data['template'].get('days', []),
                'active': True,
                'created_at': datetime.now().isoformat(),
                'created_by': task_data['user_id']
            }
            
            # Сохраняем в базу
            success = add_task(task_id, task_to_save)
            
            if success:
                self.active_tasks[task_id] = task_to_save
                
                from menu_manager import get_main_menu
                await query.edit_message_text(
                    f"✅ *Задача успешно создана!*\n\n"
                    f"📝 Шаблон: {task_data['template'].get('name')}\n"
                    f"🆔 ID задачи: `{task_id}`\n"
                    f"⏰ Будет выполняться по расписанию",
                    reply_markup=get_main_menu(task_data['user_id']),
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка при создании задачи",
                    parse_mode='Markdown'
                )
            
            return ConversationHandler.END
        
        elif data == "edit_task":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏘️ Группу", callback_data="edit_task_group")],
                [InlineKeyboardButton("📁 Подгруппу", callback_data="edit_task_subgroup")],
                [InlineKeyboardButton("📝 Шаблон", callback_data="edit_task_template")],
                [InlineKeyboardButton("⚙️ Настройки шаблона", callback_data="edit_task_template_settings")],
                get_back_button()[0]
            ])
            
            await query.edit_message_text(
                "✏️ *КАКОЙ ПУНКТ ВЫ ХОТИТЕ ИЗМЕНИТЬ?*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return TASK_EDIT

    # =============================================================================
    # СТАТУС ЗАДАЧ
    # =============================================================================

    async def show_task_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус активных задач"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        # Получаем задачи, доступные пользователю
        user_accessible_groups = get_user_accessible_groups(user_id)
        accessible_group_ids = list(user_accessible_groups.keys())
        
        user_tasks = {}
        for task_id, task_data in self.active_tasks.items():
            if task_data.get('group_id') in accessible_group_ids:
                user_tasks[task_id] = task_data
        
        if not user_tasks:
            await update.message.reply_text("📊 Нет активных задач")
            return
        
        status_text = "📊 *СТАТУС АКТИВНЫХ ЗАДАЧ:*\n\n"
        
        for task_id, task_data in user_tasks.items():
            status_text += f"🔹 *{task_data.get('template_name', 'Неизвестно')}*\n"
            status_text += f"   📍 Группа: {task_data.get('group_id', 'Неизвестно')}\n"
            
            if task_data.get('subgroup_id'):
                status_text += f"   📁 Подгруппа: {task_data.get('subgroup_id')}\n"
            
            status_text += f"   📢 Канал: {task_data.get('channel_name', 'Неизвестно')}\n"
            status_text += f"   ⏰ Время: {task_data.get('schedule_time', 'Неизвестно')}\n"
            status_text += f"   🔄 Периодичность: {task_data.get('frequency', 'Неизвестно')}\n"
            
            if task_data.get('days'):
                days_str = ", ".join(task_data['days'])
                status_text += f"   📅 Дни: {days_str}\n"
            
            status_text += f"   🆔 ID: `{task_id}`\n\n"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')

    # =============================================================================
    # ОТМЕНА ЗАДАЧИ
    # =============================================================================

    async def start_cancel_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать отмену задачи"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        # Получаем активные задачи пользователя
        user_tasks = {}
        for task_id, task_data in self.active_tasks.items():
            if task_data.get('group_id') in accessible_groups:
                user_tasks[task_id] = task_data
        
        if not user_tasks:
            await update.message.reply_text("📭 Нет активных задач для отмены")
            return ConversationHandler.END
        
        context.user_data['task_cancellation'] = {
            'user_id': user_id,
            'user_tasks': user_tasks
        }
        
        # Группируем задачи по группам
        tasks_by_group = {}
        for task_id, task_data in user_tasks.items():
            group_id = task_data.get('group_id')
            if group_id not in tasks_by_group:
                tasks_by_group[group_id] = []
            tasks_by_group[group_id].append((task_id, task_data))
        
        context.user_data['task_cancellation']['tasks_by_group'] = tasks_by_group
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ ОТМЕНЫ ЗАДАЧИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CANCEL_TASK_GROUP

    # =============================================================================
    # ОБРАБОТЧИКИ КНОПОК
    # =============================================================================

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if not is_authorized(user_id):
            await query.edit_message_text("❌ Недостаточно прав")
            return
        
        if data == "back":
            from menu_manager import get_tasks_menu
            keyboard = get_tasks_menu()
            await query.edit_message_text(
                "📋 УПРАВЛЕНИЕ ЗАДАЧАМИ",
                reply_markup=keyboard
            )

    def get_conversation_handler(self):
        """Получить ConversationHandler для задач"""
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^📝 Создать задачу$"), self.start_create_task),
                MessageHandler(filters.Regex("^❌ Отменить задачу$"), self.start_cancel_task),
                MessageHandler(filters.Regex("^📊 Статус задач$"), self.show_task_status),
            ],
            states={
                # States for creating task
                TASK_GROUP: [CallbackQueryHandler(self.task_group_selected, pattern="^select_group_")],
                TASK_SUBGROUP: [CallbackQueryHandler(self.task_subgroup_selected, pattern="^select_subgroup_")],
                TASK_TEMPLATE: [CallbackQueryHandler(self.task_template_selected, pattern="^select_template_")],
                TASK_CONFIRM: [CallbackQueryHandler(self.task_confirmation_handler, pattern="^(confirm_task|edit_task)")],
                TASK_EDIT: [CallbackQueryHandler(self.handle_task_edit, pattern="^edit_task_")],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_task_operation)],
            name="task_conversation"
        )

    async def handle_task_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка редактирования задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        field = data.replace("edit_task_", "")
        
        # Здесь будет логика для каждого поля
        await query.edit_message_text(f"✏️ Редактирование поля задачи: {field}\n\nЭта функция в разработке...")
        
        return ConversationHandler.END

    async def cancel_task_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции с задачей"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        context.user_data.pop('task_creation', None)
        context.user_data.pop('task_cancellation', None)
        
        from menu_manager import get_main_menu
        await update.message.reply_text(
            "❌ Операция с задачей отменена",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
