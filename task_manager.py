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
    add_task, remove_task, deactivate_task, get_group_templates, get_subgroup_templates
)
from menu_manager import (
    get_groups_keyboard, get_subgroups_keyboard,
    get_templates_keyboard, get_confirmation_keyboard, get_back_button
)
from user_roles import can_create_tasks, can_cancel_tasks, can_test_tasks, can_view_tasks

# Состояния для создания задачи
CREATE_TASK_GROUP, CREATE_TASK_SUBGROUP, CREATE_TASK_TEMPLATE, CREATE_TASK_CHANNEL, CREATE_TASK_CONFIRM = range(5)

# Состояния для отмены задачи
CANCEL_TASK_GROUP, CANCEL_TASK_SUBGROUP, CANCEL_TASK_SELECT, CANCEL_TASK_CONFIRM = range(4)

# Состояния для тестирования задачи
TEST_TASK_GROUP, TEST_TASK_SUBGROUP, TEST_TASK_TEMPLATE, TEST_TASK_CONFIRM = range(4)

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
                
                # Восстанавливаем планировщик задач
                await self._schedule_task(application, task_id, task_data)
                
        self.restore_completed = True
        logging.info(f"🎉 Восстановление завершено: {active_count} активных задач")

    async def _schedule_task(self, application, task_id, task_data):
        """Запланировать выполнение задачи"""
        # Здесь будет логика планирования задач
        # Пока просто логируем
        logging.info(f"📅 Запланирована задача: {task_id}")

    async def show_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню задач"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
            
        from menu_manager import get_tasks_menu
        keyboard = get_tasks_menu(user_id)
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
        
        if not can_create_tasks(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для создания задач")
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
            "🏘️ *ШАГ 1/4: ВЫБЕРИТЕ ГРУППУ ДЛЯ СОЗДАНИЯ ЗАДАЧИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CREATE_TASK_GROUP

    async def create_task_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            from menu_manager import get_tasks_menu
            keyboard = get_tasks_menu(query.from_user.id)
            await query.edit_message_text(
                "📋 УПРАВЛЕНИЕ ЗАДАЧАМИ",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['task_creation']['group_id'] = group_id
            
            # Получаем подгруппы для выбранной группы
            from database import load_groups
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ШАГ 2/4: ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}'*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return CREATE_TASK_SUBGROUP
            else:
                # Пропускаем шаг подгруппы
                context.user_data['task_creation']['subgroup_id'] = None
                return await self._show_templates_for_task(update, context)

    async def create_task_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            user_id = context.user_data['task_creation']['user_id']
            accessible_groups = get_user_accessible_groups(user_id)
            keyboard = get_groups_keyboard(accessible_groups)
            await query.edit_message_text(
                "🏘️ *ШАГ 1/4: ВЫБЕРИТЕ ГРУППУ ДЛЯ СОЗДАНИЯ ЗАДАЧИ*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return CREATE_TASK_GROUP
        
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = "_".join(parts[1:])
            
            context.user_data['task_creation']['subgroup_id'] = subgroup_id
            return await self._show_templates_for_task(update, context)

    async def _show_templates_for_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать шаблоны для создания задачи"""
        task_data = context.user_data['task_creation']
        group_id = task_data['group_id']
        subgroup_id = task_data.get('subgroup_id')
        
        # Получаем шаблоны
        if subgroup_id and subgroup_id != "none":
            templates = get_subgroup_templates(group_id, subgroup_id)
        else:
            templates = get_group_templates(group_id)
        
        if not templates:
            await update.callback_query.edit_message_text(
                "❌ *В выбранной группе/подгруппе нет шаблонов*",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        context.user_data['task_creation']['templates'] = templates
        keyboard = get_templates_keyboard(templates)
        
        from database import load_groups
        groups_data = load_groups()
        group_name = groups_data.get("groups", {}).get(group_id, {}).get('name', group_id)
        
        if subgroup_id and subgroup_id != "none":
            subgroup_name = groups_data.get("groups", {}).get(group_id, {}).get('subgroups', {}).get(subgroup_id, subgroup_id)
            message_text = f"📝 *ШАГ 3/4: ВЫБЕРИТЕ ШАБЛОН ИЗ ПОДГРУППЫ '{subgroup_name}'*"
        else:
            message_text = f"📝 *ШАГ 3/4: ВЫБЕРИТЕ ШАБЛОН ИЗ ГРУППЫ '{group_name}'*"
        
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CREATE_TASK_TEMPLATE

    async def create_task_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора шаблона для задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            if context.user_data['task_creation'].get('subgroup_id'):
                group_id = context.user_data['task_creation']['group_id']
                from database import load_groups
                groups_data = load_groups()
                group_info = groups_data.get("groups", {}).get(group_id, {})
                subgroups = group_info.get("subgroups", {})
                
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ШАГ 2/4: ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}'*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return CREATE_TASK_SUBGROUP
            else:
                user_id = context.user_data['task_creation']['user_id']
                accessible_groups = get_user_accessible_groups(user_id)
                keyboard = get_groups_keyboard(accessible_groups)
                await query.edit_message_text(
                    "🏘️ *ШАГ 1/4: ВЫБЕРИТЕ ГРУППУ ДЛЯ СОЗДАНИЯ ЗАДАЧИ*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return CREATE_TASK_GROUP
        
        if data.startswith("select_template_"):
            template_id = data.replace("select_template_", "")
            template = get_template_by_id(template_id)
            
            if not template:
                await query.edit_message_text("❌ Шаблон не найден")
                return ConversationHandler.END
            
            context.user_data['task_creation']['template_id'] = template_id
            context.user_data['task_creation']['template'] = template
            
            # Заглушка для выбора канала (будет реализовано позже)
            context.user_data['task_creation']['channel_id'] = "-100123456789"
            context.user_data['task_creation']['channel_name'] = "Тестовый канал"
            
            return await self._show_task_confirmation(update, context)

    async def _show_task_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение создания задачи"""
        task_data = context.user_data['task_creation']
        template = task_data['template']
        
        confirmation_text = self._format_task_confirmation(task_data)
        
        keyboard = get_confirmation_keyboard("confirm_create_task", "edit_create_task")
        
        await update.callback_query.edit_message_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CREATE_TASK_CONFIRM

    def _format_task_confirmation(self, task_data):
        """Форматирование подтверждения задачи"""
        template = task_data['template']
        
        text = "✅ *ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ЗАДАЧИ*\n\n"
        
        text += f"📝 *Шаблон:* {template.get('name', 'Без названия')}\n"
        text += f"📋 *Текст:* {template.get('text', '')[:100]}...\n"
        
        if template.get('image'):
            text += f"🖼️ *С изображением:* Да\n"
        else:
            text += f"🖼️ *С изображением:* Нет\n"
        
        from database import load_groups
        groups_data = load_groups()
        group_id = task_data.get('group_id')
        group_name = groups_data.get("groups", {}).get(group_id, {}).get('name', group_id)
        text += f"🏘️ *Группа:* {group_name}\n"
        
        if task_data.get('subgroup_id'):
            subgroup_name = groups_data.get("groups", {}).get(group_id, {}).get('subgroups', {}).get(
                task_data.get('subgroup_id'), task_data.get('subgroup_id')
            )
            text += f"📁 *Подгруппа:* {subgroup_name}\n"
        
        text += f"📢 *Канал:* {task_data.get('channel_name', 'Не указан')}\n"
        text += f"⏰ *Время:* {template.get('schedule_time', 'Не указано')} (МСК)\n"
        text += f"🔄 *Периодичность:* {template.get('frequency', 'Не указана')}\n"
        
        if template.get('days'):
            days_str = ", ".join(template['days'])
            text += f"📅 *Дни:* {days_str}\n"
        
        text += "\n❓ *Все верно?*"
        
        return text

    async def create_task_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения создания задачи"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_create_task":
            # Создаем задачу
            task_data = context.user_data['task_creation']
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            task_to_save = {
                'task_id': task_id,
                'template_id': task_data['template_id'],
                'template_name': task_data['template'].get('name'),
                'template_text': task_data['template'].get('text'),
                'template_image': task_data['template'].get('image'),
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
                
                # Планируем задачу
                from bot import application
                await self._schedule_task(application, task_id, task_to_save)
                
                await query.edit_message_text(
                    f"✅ *Задача успешно создана!*\n\n"
                    f"📝 Шаблон: {task_data['template'].get('name')}\n"
                    f"🆔 ID задачи: `{task_id}`\n"
                    f"⏰ Будет выполняться по расписанию",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ *Ошибка при создании задачи*",
                    parse_mode='Markdown'
                )
            
            return ConversationHandler.END
        
        elif data == "edit_create_task":
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

    # =============================================================================
    # ОТМЕНА ЗАДАЧИ
    # =============================================================================

    async def start_cancel_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать отмену задачи"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        if not can_cancel_tasks(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для отмены задач")
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
            await update.message.reply_text("📭 *Нет активных задач для отмены*", parse_mode='Markdown')
            return ConversationHandler.END
        
        context.user_data['task_cancellation'] = {
            'user_id': user_id,
            'user_tasks': user_tasks
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ ОТМЕНЫ ЗАДАЧИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return CANCEL_TASK_GROUP

    # =============================================================================
    # ТЕСТИРОВАНИЕ ЗАДАЧИ
    # =============================================================================

    async def start_test_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать тестирование задачи"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        if not can_test_tasks(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для тестирования задач")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        context.user_data['task_testing'] = {
            'user_id': user_id,
            'step': 'group'
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ ТЕСТИРОВАНИЯ ЗАДАЧИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEST_TASK_GROUP

    # =============================================================================
    # СТАТУС ЗАДАЧ
    # =============================================================================

    async def show_task_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статус активных задач"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        if not can_view_tasks(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для просмотра задач")
            return
        
        # Получаем задачи, доступные пользователю
        user_accessible_groups = get_user_accessible_groups(user_id)
        accessible_group_ids = list(user_accessible_groups.keys())
        
        user_tasks = {}
        for task_id, task_data in self.active_tasks.items():
            if task_data.get('group_id') in accessible_group_ids:
                user_tasks[task_id] = task_data
        
        if not user_tasks:
            await update.message.reply_text("📊 *Нет активных задач*", parse_mode='Markdown')
            return
        
        status_text = "📊 *СТАТУС АКТИВНЫХ ЗАДАЧ:*\n\n"
        
        for task_id, task_data in user_tasks.items():
            status_text += f"🔹 *{task_data.get('template_name', 'Неизвестно')}*\n"
            
            from database import load_groups
            groups_data = load_groups()
            group_id = task_data.get('group_id')
            group_name = groups_data.get("groups", {}).get(group_id, {}).get('name', group_id)
            status_text += f"   🏘️ Группа: {group_name}\n"
            
            if task_data.get('subgroup_id'):
                subgroup_name = groups_data.get("groups", {}).get(group_id, {}).get('subgroups', {}).get(
                    task_data.get('subgroup_id'), task_data.get('subgroup_id')
                )
                status_text += f"   📁 Подгруппа: {subgroup_name}\n"
            
            status_text += f"   📢 Канал: {task_data.get('channel_name', 'Неизвестно')}\n"
            status_text += f"   ⏰ Время: {task_data.get('schedule_time', 'Неизвестно')} (МСК)\n"
            status_text += f"   🔄 Периодичность: {task_data.get('frequency', 'Неизвестно')}\n"
            
            if task_data.get('days'):
                days_str = ", ".join(task_data['days'])
                status_text += f"   📅 Дни: {days_str}\n"
            
            status_text += f"   🆔 ID: `{task_id}`\n\n"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')

    # =============================================================================
    # ОБРАБОТЧИКИ КНОПОК
    # =============================================================================

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки задач"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if not is_authorized(user_id):
            await query.edit_message_text("❌ Недостаточно прав")
            return
        
        try:
            if data == "back":
                from menu_manager import get_tasks_menu
                keyboard = get_tasks_menu(user_id)
                await query.message.reply_text(
                    "📋 УПРАВЛЕНИЕ ЗАДАЧАМИ",
                    reply_markup=keyboard
                )
                await query.message.delete()
            
            elif data.startswith("select_group_"):
                if 'task_creation' in context.user_data:
                    await self.create_task_group(update, context)
                elif 'task_cancellation' in context.user_data:
                    await self.cancel_task_group(update, context)
                elif 'task_testing' in context.user_data:
                    await self.test_task_group(update, context)
            
            elif data.startswith("select_subgroup_"):
                if 'task_creation' in context.user_data:
                    await self.create_task_subgroup(update, context)
                elif 'task_cancellation' in context.user_data:
                    await self.cancel_task_subgroup(update, context)
                elif 'task_testing' in context.user_data:
                    await self.test_task_subgroup(update, context)
            
            elif data.startswith("select_template_"):
                if 'task_creation' in context.user_data:
                    await self.create_task_template(update, context)
                elif 'task_testing' in context.user_data:
                    await self.test_task_template(update, context)
            
            elif data.startswith("confirm_create_task"):
                await self.create_task_confirmation(update, context)
            
            else:
                await query.edit_message_text(
                    "🛠️ *Функция в разработке*",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике задач: {e}")
            await query.edit_message_text(
                "❌ *Ошибка при обработке задачи*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]]),
                parse_mode='Markdown'
            )

    async def cancel_task_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции с задачей"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        context.user_data.pop('task_creation', None)
        context.user_data.pop('task_cancellation', None)
        context.user_data.pop('task_testing', None)
        
        from menu_manager import get_main_menu
        await update.message.reply_text(
            "❌ Операция с задачей отменена",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

    def get_conversation_handler(self):
        """Получить ConversationHandler для задач"""
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^📝 Создать задачу$"), self.start_create_task),
                MessageHandler(filters.Regex("^❌ Отменить задачу$"), self.start_cancel_task),
                MessageHandler(filters.Regex("^🧪 Тестирование$"), self.start_test_task),
                MessageHandler(filters.Regex("^📊 Статус задач$"), self.show_task_status),
            ],
            states={
                # States for creating task
                CREATE_TASK_GROUP: [CallbackQueryHandler(self.create_task_group, pattern="^(select_group_|back)")],
                CREATE_TASK_SUBGROUP: [CallbackQueryHandler(self.create_task_subgroup, pattern="^(select_subgroup_|back)")],
                CREATE_TASK_TEMPLATE: [CallbackQueryHandler(self.create_task_template, pattern="^(select_template_|back)")],
                CREATE_TASK_CONFIRM: [CallbackQueryHandler(self.create_task_confirmation, pattern="^(confirm_create_task|edit_create_task)")],
                
                # States for canceling task
                CANCEL_TASK_GROUP: [CallbackQueryHandler(self.cancel_task_group, pattern="^(select_group_|back)")],
                
                # States for testing task
                TEST_TASK_GROUP: [CallbackQueryHandler(self.test_task_group, pattern="^(select_group_|back)")],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_task_operation)],
            name="task_conversation"
        )

    # Заглушки для нереализованных методов
    async def cancel_task_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для отмены задачи"""
        await update.callback_query.edit_message_text("🛠️ *Функция отмены задач в разработке*", parse_mode='Markdown')
        return ConversationHandler.END

    async def cancel_task_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для отмены задачи"""
        await update.callback_query.edit_message_text("🛠️ *Функция отмены задач в разработке*", parse_mode='Markdown')
        return ConversationHandler.END

    async def test_task_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для тестирования задачи"""
        await update.callback_query.edit_message_text("🛠️ *Функция тестирования задач в разработке*", parse_mode='Markdown')
        return ConversationHandler.END

    async def test_task_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для тестирования задачи"""
        await update.callback_query.edit_message_text("🛠️ *Функция тестирования задач в разработке*", parse_mode='Markdown')
        return ConversationHandler.END

    async def test_task_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора шаблона для тестирования задачи"""
        await update.callback_query.edit_message_text("🛠️ *Функция тестирования задач в разработке*", parse_mode='Markdown')
        return ConversationHandler.END

# Глобальный экземпляр менеджера задач
task_manager = TaskManager()
