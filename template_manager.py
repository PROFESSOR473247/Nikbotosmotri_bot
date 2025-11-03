# -*- coding: utf-8 -*-
import logging
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
import pytz

from database import (
    load_templates, save_templates, load_groups, get_user_accessible_groups,
    is_authorized, get_user_role, get_template_by_id, update_template, remove_template,
    get_group_templates, get_subgroup_templates, add_template
)
from menu_manager import (
    get_templates_keyboard, get_groups_keyboard, get_subgroups_keyboard,
    get_days_keyboard, get_frequency_keyboard, get_edit_template_keyboard,
    get_confirmation_keyboard, get_back_button
)
from user_roles import can_create_templates

# Состояния для создания шаблона
TEMPLATE_GROUP, TEMPLATE_SUBGROUP, TEMPLATE_NAME, TEMPLATE_TEXT, TEMPLATE_IMAGE, TEMPLATE_TIME, TEMPLATE_DAY, TEMPLATE_FREQUENCY, TEMPLATE_SECOND_DAY, TEMPLATE_CONFIRM = range(10)

# Состояния для редактирования шаблона
EDIT_TEMPLATE_SELECT, EDIT_TEMPLATE_FIELD, EDIT_TEMPLATE_VALUE = range(3)

# Состояния для удаления шаблона
DELETE_TEMPLATE_GROUP, DELETE_TEMPLATE_SUBGROUP, DELETE_TEMPLATE_SELECT, DELETE_TEMPLATE_CONFIRM = range(4)

class TemplateManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def show_templates_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню шаблонов"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
            
        from menu_manager import get_templates_menu
        keyboard = get_templates_menu(user_id)
        await update.message.reply_text("📁 УПРАВЛЕНИЕ ШАБЛОНАМИ", reply_markup=keyboard)

    # =============================================================================
    # СПИСОК ШАБЛОНОВ
    # =============================================================================

    async def show_templates_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список шаблонов с выбором группы"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return
        
        context.user_data['template_list'] = {
            'user_id': user_id,
            'accessible_groups': accessible_groups
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ ПРОСМОТРА ШАБЛОНОВ:*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_template_list_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для списка шаблонов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            from menu_manager import get_templates_menu
            keyboard = get_templates_menu(query.from_user.id)
            await query.edit_message_text(
                "📁 УПРАВЛЕНИЕ ШАБЛОНАМИ",
                reply_markup=keyboard
            )
            return
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            
            # Получаем подгруппы для выбранной группы
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                # Если есть подгруппы, показываем их
                context.user_data['template_list']['group_id'] = group_id
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                
                await query.edit_message_text(
                    f"📁 *ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}':*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                # Если подгрупп нет, показываем шаблоны напрямую
                templates = get_group_templates(group_id)
                await self._show_templates_for_group(update, context, group_id, templates)

    async def handle_template_list_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для списка шаблонов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            accessible_groups = context.user_data['template_list']['accessible_groups']
            keyboard = get_groups_keyboard(accessible_groups)
            await query.edit_message_text(
                "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ ПРОСМОТРА ШАБЛОНОВ:*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return
        
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = "_".join(parts[1:])
            
            templates = get_subgroup_templates(group_id, subgroup_id)
            await self._show_templates_for_group(update, context, group_id, templates, subgroup_id)

    async def _show_templates_for_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: str, templates: dict, subgroup_id: str = None):
        """Показать шаблоны для группы/подгруппы"""
        query = update.callback_query
        
        if not templates:
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            
            if subgroup_id:
                subgroup_name = group_info.get("subgroups", {}).get(subgroup_id, subgroup_id)
                message = f"📭 *В подгруппе '{subgroup_name}' нет шаблонов*"
            else:
                message = f"📭 *В группе '{group_info.get('name', group_id)}' нет шаблонов*"
            
            await query.edit_message_text(message, parse_mode='Markdown')
            return
        
        # Сохраняем шаблоны для пагинации
        context.user_data['current_templates'] = templates
        
        keyboard = get_templates_keyboard(templates)
        
        groups_data = load_groups()
        group_info = groups_data.get("groups", {}).get(group_id, {})
        
        if subgroup_id:
            subgroup_name = group_info.get("subgroups", {}).get(subgroup_id, subgroup_id)
            message = f"📝 *ШАБЛОНЫ В ПОДГРУППЕ '{subgroup_name}':*"
        else:
            message = f"📝 *ШАБЛОНЫ В ГРУППЕ '{group_info.get('name', group_id)}':*"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def handle_template_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора конкретного шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            # Возврат к списку групп
            accessible_groups = context.user_data.get('template_list', {}).get('accessible_groups', {})
            keyboard = get_groups_keyboard(accessible_groups)
            await query.edit_message_text(
                "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ ПРОСМОТРА ШАБЛОНОВ:*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return
        
        if data.startswith("select_template_"):
            template_id = data.replace("select_template_", "")
            template = get_template_by_id(template_id)
            
            if not template:
                await query.edit_message_text("❌ Шаблон не найден")
                return
            
            # Формируем информацию о шаблоне
            template_info = self._format_template_info(template)
            
            await query.edit_message_text(
                template_info,
                parse_mode='Markdown'
            )

    def _format_template_info(self, template):
        """Форматирование информации о шаблоне"""
        info = f"📝 *{template.get('name', 'Без названия')}*\n\n"
        
        if template.get('text'):
            info += f"📋 *Текст:* {template['text']}\n\n"
        
        if template.get('group'):
            info += f"🏘️ *Группа:* {template['group']}\n"
        
        if template.get('subgroup'):
            info += f"📁 *Подгруппа:* {template['subgroup']}\n"
        
        if template.get('image'):
            info += f"🖼️ *Изображение:* Есть\n"
        else:
            info += f"🖼️ *Изображение:* Нет\n"
        
        if template.get('schedule_time'):
            info += f"⏰ *Время:* {template['schedule_time']} (МСК)\n"
        
        if template.get('frequency'):
            info += f"🔄 *Периодичность:* {template['frequency']}\n"
        
        if template.get('days'):
            days_str = ", ".join(template['days'])
            info += f"📅 *Дни:* {days_str}\n"
        
        if template.get('created_at'):
            try:
                created = datetime.fromisoformat(template['created_at']).strftime("%d.%m.%Y %H:%M")
                info += f"📅 *Создан:* {created}\n"
            except:
                info += f"📅 *Создан:* {template['created_at']}\n"
        
        return info

    # =============================================================================
    # СОЗДАНИЕ ШАБЛОНА
    # =============================================================================

    async def start_create_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать создание нового шаблона"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        if not can_create_templates(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для создания шаблонов")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        # Инициализируем данные создания шаблона
        context.user_data['template_creation'] = {
            'user_id': user_id,
            'step': 'group'
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ШАГ 1/8: ВЫБЕРИТЕ ГРУППУ ДЛЯ ШАБЛОНА*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEMPLATE_GROUP

    async def create_template_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            from menu_manager import get_templates_menu
            keyboard = get_templates_menu(query.from_user.id)
            await query.edit_message_text(
                "📁 УПРАВЛЕНИЕ ШАБЛОНАМИ",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['template_creation']['group_id'] = group_id
            
            # Получаем подгруппы для выбранной группы
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                # Если есть подгруппы, предлагаем выбрать
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ШАГ 2/8: ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}'*\n\n"
                    f"ℹ️ Если подгруппа не нужна, нажмите '🔙 Назад'",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return TEMPLATE_SUBGROUP
            else:
                # Если подгрупп нет, переходим к названию
                context.user_data['template_creation']['subgroup_id'] = None
                await query.edit_message_text(
                    "📝 *ШАГ 3/8: ВВЕДИТЕ НАЗВАНИЕ ШАБЛОНА*\n\n"
                    "ℹ️ Название должно быть понятным и описывать назначение шаблона",
                    parse_mode='Markdown'
                )
                return TEMPLATE_NAME

    async def create_template_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            # Возврат к выбору группы
            user_id = context.user_data['template_creation']['user_id']
            accessible_groups = get_user_accessible_groups(user_id)
            keyboard = get_groups_keyboard(accessible_groups)
            await query.edit_message_text(
                "🏘️ *ШАГ 1/8: ВЫБЕРИТЕ ГРУППУ ДЛЯ ШАБЛОНА*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return TEMPLATE_GROUP
        
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = "_".join(parts[1:])
            
            context.user_data['template_creation']['subgroup_id'] = subgroup_id
            
            await query.edit_message_text(
                "📝 *ШАГ 3/8: ВВЕДИТЕ НАЗВАНИЕ ШАБЛОНА*\n\n"
                "ℹ️ Название должно быть понятным и описывать назначение шаблона",
                parse_mode='Markdown'
            )
            return TEMPLATE_NAME

    async def create_template_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода названия шаблона"""
        template_name = update.message.text.strip()
        
        if len(template_name) < 2:
            await update.message.reply_text("❌ Название слишком короткое. Введите еще раз:")
            return TEMPLATE_NAME
        
        context.user_data['template_creation']['name'] = template_name
        
        await update.message.reply_text(
            "📋 *ШАГ 4/8: ВВЕДИТЕ ТЕКСТ ШАБЛОНА*\n\n"
            "ℹ️ Это основной текст сообщения, который будет отправляться",
            parse_mode='Markdown'
        )
        
        return TEMPLATE_TEXT

    async def create_template_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода текста шаблона"""
        template_text = update.message.text.strip()
        
        if len(template_text) < 5:
            await update.message.reply_text("❌ Текст слишком короткий. Введите еще раз:")
            return TEMPLATE_TEXT
        
        context.user_data['template_creation']['text'] = template_text
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ Добавить изображение", callback_data="add_image")],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_image")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ])
        
        await update.message.reply_text(
            "🖼️ *ШАГ 5/8: ДОБАВИТЬ ИЗОБРАЖЕНИЕ?*\n\n"
            "ℹ️ Изображение будет отправляться вместе с текстом шаблона",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEMPLATE_IMAGE

    async def create_template_image_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора добавления изображения"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "add_image":
            await query.edit_message_text(
                "🖼️ *Отправьте изображение как файл (не как сжатое фото)*\n\n"
                "ℹ️ Рекомендуется отправлять изображения как файлы для лучшего качества",
                parse_mode='Markdown'
            )
            return TEMPLATE_IMAGE
        
        elif data == "skip_image":
            context.user_data['template_creation']['image'] = None
            await query.edit_message_text(
                "⏰ *ШАГ 6/8: ВВЕДИТЕ ВРЕМЯ ОТПРАВКИ (формат ЧЧ:ММ по МСК)*\n\n"
                "ℹ️ Например: 09:00 или 14:30",
                parse_mode='Markdown'
            )
            return TEMPLATE_TIME
        
        elif data == "back":
            await query.edit_message_text(
                "📋 *ШАГ 4/8: ВВЕДИТЕ ТЕКСТ ШАБЛОНА*\n\n"
                "ℹ️ Это основной текст сообщения, который будет отправляться",
                parse_mode='Markdown'
            )
            return TEMPLATE_TEXT

    async def create_template_image_receive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка получения изображения"""
        if update.message.photo:
            # Получаем самое большое фото
            photo_file = await update.message.photo[-1].get_file()
        elif update.message.document and update.message.document.mime_type.startswith('image/'):
            photo_file = await update.message.document.get_file()
        else:
            await update.message.reply_text("❌ Пожалуйста, отправьте изображение как файл")
            return TEMPLATE_IMAGE
        
        # Сохраняем изображение
        images_dir = "images"
        os.makedirs(images_dir, exist_ok=True)
        
        filename = f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = os.path.join(images_dir, filename)
        
        await photo_file.download_to_drive(file_path)
        
        context.user_data['template_creation']['image'] = file_path
        
        await update.message.reply_text(
            "✅ Изображение сохранено!\n\n"
            "⏰ *ШАГ 6/8: ВВЕДИТЕ ВРЕМЯ ОТПРАВКИ (формат ЧЧ:ММ по МСК)*\n\n"
            "ℹ️ Например: 09:00 или 14:30",
            parse_mode='Markdown'
        )
        
        return TEMPLATE_TIME

    async def create_template_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода времени отправки"""
        time_input = update.message.text.strip()
        
        # Проверка формата времени
        try:
            hours, minutes = map(int, time_input.split(':'))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 09:00):")
            return TEMPLATE_TIME
        
        context.user_data['template_creation']['schedule_time'] = time_input
        
        keyboard = get_days_keyboard()
        await update.message.reply_text(
            "📅 *ШАГ 7/8: ВЫБЕРИТЕ ДЕНЬ НЕДЕЛИ ОТПРАВКИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEMPLATE_DAY

    async def create_template_day(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора дня недели"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            await query.edit_message_text(
                "⏰ *ШАГ 6/8: ВВЕДИТЕ ВРЕМЯ ОТПРАВКИ (формат ЧЧ:ММ по МСК)*\n\n"
                "ℹ️ Например: 09:00 или 14:30",
                parse_mode='Markdown'
            )
            return TEMPLATE_TIME
        
        if data.startswith("select_day_"):
            day_key = data.replace("select_day_", "")
            day_names = {
                "monday": "Понедельник",
                "tuesday": "Вторник",
                "wednesday": "Среда", 
                "thursday": "Четверг",
                "friday": "Пятница",
                "saturday": "Суббота",
                "sunday": "Воскресенье"
            }
            
            context.user_data['template_creation']['day'] = day_key
            context.user_data['template_creation']['day_name'] = day_names.get(day_key, day_key)
            
            keyboard = get_frequency_keyboard()
            await query.edit_message_text(
                "🔄 *ШАГ 8/8: ВЫБЕРИТЕ ПЕРИОДИЧНОСТЬ*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return TEMPLATE_FREQUENCY

    async def create_template_frequency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора периодичности"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            keyboard = get_days_keyboard()
            await query.edit_message_text(
                "📅 *ШАГ 7/8: ВЫБЕРИТЕ ДЕНЬ НЕДЕЛИ ОТПРАВКИ*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return TEMPLATE_DAY
        
        if data.startswith("frequency_"):
            frequency_map = {
                "frequency_2_week": "2 раза в неделю",
                "frequency_1_week": "1 раз в неделю", 
                "frequency_2_month": "2 раза в месяц",
                "frequency_1_month": "1 раз в месяц"
            }
            
            frequency = frequency_map.get(data, data)
            context.user_data['template_creation']['frequency'] = frequency
            
            # Если выбрано 2 раза в неделю, запрашиваем второй день
            if data == "frequency_2_week":
                keyboard = get_days_keyboard()
                await query.edit_message_text(
                    "📅 *ВЫБЕРИТЕ ВТОРОЙ ДЕНЬ НЕДЕЛИ*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return TEMPLATE_SECOND_DAY
            else:
                # Переходим к подтверждению
                context.user_data['template_creation']['days'] = [context.user_data['template_creation']['day_name']]
                return await self.show_template_confirmation(update, context)

    async def create_template_second_day(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора второго дня для периодичности 2 раза в неделю"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            keyboard = get_frequency_keyboard()
            await query.edit_message_text(
                "🔄 *ШАГ 8/8: ВЫБЕРИТЕ ПЕРИОДИЧНОСТЬ*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return TEMPLATE_FREQUENCY
        
        if data.startswith("select_day_"):
            second_day_key = data.replace("select_day_", "")
            day_names = {
                "monday": "Понедельник",
                "tuesday": "Вторник",
                "wednesday": "Среда",
                "thursday": "Четверг", 
                "friday": "Пятница",
                "saturday": "Суббота",
                "sunday": "Воскресенье"
            }
            
            first_day = context.user_data['template_creation']['day_name']
            second_day = day_names.get(second_day_key, second_day_key)
            
            context.user_data['template_creation']['second_day'] = second_day_key
            context.user_data['template_creation']['second_day_name'] = second_day
            context.user_data['template_creation']['days'] = [first_day, second_day]
            
            return await self.show_template_confirmation(update, context)

    async def show_template_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать подтверждение создания шаблона"""
        template_data = context.user_data['template_creation']
        
        confirmation_text = self._format_template_confirmation(template_data)
        
        keyboard = get_confirmation_keyboard("confirm_create_template", "edit_create_template")
        
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
        
        return TEMPLATE_CONFIRM

    def _format_template_confirmation(self, template_data):
        """Форматирование подтверждения шаблона"""
        text = "✅ *ПОДТВЕРЖДЕНИЕ СОЗДАНИЯ ШАБЛОНА*\n\n"
        
        text += f"📝 *Название:* {template_data.get('name')}\n"
        
        groups_data = load_groups()
        group_id = template_data.get('group_id')
        group_name = groups_data.get('groups', {}).get(group_id, {}).get('name', group_id)
        text += f"🏘️ *Группа:* {group_name}\n"
        
        if template_data.get('subgroup_id'):
            subgroup_name = groups_data.get('groups', {}).get(group_id, {}).get('subgroups', {}).get(
                template_data.get('subgroup_id'), template_data.get('subgroup_id')
            )
            text += f"📁 *Подгруппа:* {subgroup_name}\n"
        
        text += f"📋 *Текст:* {template_data.get('text', '')[:100]}...\n"
        
        if template_data.get('image'):
            text += f"🖼️ *Изображение:* Да\n"
        else:
            text += f"🖼️ *Изображение:* Нет\n"
        
        text += f"⏰ *Время:* {template_data.get('schedule_time')} (МСК)\n"
        
        days = template_data.get('days', [])
        if days:
            days_str = ", ".join(days)
            text += f"📅 *Дни:* {days_str}\n"
        
        text += f"🔄 *Периодичность:* {template_data.get('frequency')}\n\n"
        
        text += "❓ *Все верно?*"
        
        return text

    async def create_template_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения создания шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_create_template":
            # Сохраняем шаблон
            template_data = context.user_data['template_creation']
            template_id = f"template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            template_to_save = {
                'template_id': template_id,
                'name': template_data['name'],
                'text': template_data['text'],
                'group': template_data['group_id'],
                'subgroup': template_data.get('subgroup_id'),
                'image': template_data.get('image'),
                'schedule_time': template_data['schedule_time'],
                'frequency': template_data['frequency'],
                'days': template_data.get('days', []),
                'created_at': datetime.now().isoformat(),
                'created_by': template_data['user_id']
            }
            
            # Сохраняем в базу
            success = add_template(template_id, template_to_save)
            
            if success:
                await query.edit_message_text(
                    f"✅ *Шаблон '{template_data['name']}' успешно создан!*\n\n"
                    f"🆔 ID шаблона: `{template_id}`",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ *Ошибка при создании шаблона '{template_data['name']}'*",
                    parse_mode='Markdown'
                )
            
            # Очищаем временные данные
            context.user_data.pop('template_creation', None)
            return ConversationHandler.END
        
        elif data == "edit_create_template":
            keyboard = get_edit_template_keyboard()
            await query.edit_message_text(
                "✏️ *КАКОЙ ПУНКТ ВЫ ХОТИТЕ ИЗМЕНИТЬ?*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return EDIT_TEMPLATE_FIELD

    # =============================================================================
    # РЕДАКТИРОВАНИЕ ШАБЛОНА
    # =============================================================================

    async def start_edit_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать редактирование шаблона"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        if not can_create_templates(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для редактирования шаблонов")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        context.user_data['template_edit'] = {
            'user_id': user_id,
            'step': 'select_group'
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ РЕДАКТИРОВАНИЯ ШАБЛОНА*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return EDIT_TEMPLATE_SELECT

    # =============================================================================
    # УДАЛЕНИЕ ШАБЛОНА  
    # =============================================================================

    async def start_delete_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начать удаление шаблона"""
        user_id = update.effective_user.id
        
        if not is_authorized(user_id):
            await update.message.reply_text("❌ Недостаточно прав")
            return ConversationHandler.END
        
        if not can_create_templates(get_user_role(user_id)):
            await update.message.reply_text("❌ Недостаточно прав для удаления шаблонов")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        context.user_data['template_delete'] = {
            'user_id': user_id,
            'step': 'select_group'
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ ШАБЛОНА*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return DELETE_TEMPLATE_GROUP

    async def delete_template_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для удаления шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            from menu_manager import get_templates_menu
            keyboard = get_templates_menu(query.from_user.id)
            await query.edit_message_text(
                "📁 УПРАВЛЕНИЕ ШАБЛОНАМИ",
                reply_markup=keyboard
            )
            return ConversationHandler.END
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['template_delete']['group_id'] = group_id
            
            # Получаем подгруппы для выбранной группы
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                # Если есть подгруппы, предлагаем выбрать
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}':*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return DELETE_TEMPLATE_SUBGROUP
            else:
                # Если подгрупп нет, показываем шаблоны напрямую
                templates = get_group_templates(group_id)
                return await self._show_templates_for_deletion(update, context, group_id, templates)

    async def delete_template_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для удаления шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            accessible_groups = get_user_accessible_groups(query.from_user.id)
            keyboard = get_groups_keyboard(accessible_groups)
            await query.edit_message_text(
                "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ ШАБЛОНА*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return DELETE_TEMPLATE_GROUP
        
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = "_".join(parts[1:])
            
            context.user_data['template_delete']['subgroup_id'] = subgroup_id
            
            templates = get_subgroup_templates(group_id, subgroup_id)
            return await self._show_templates_for_deletion(update, context, group_id, templates, subgroup_id)

    async def _show_templates_for_deletion(self, update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: str, templates: dict, subgroup_id: str = None):
        """Показать шаблоны для удаления"""
        query = update.callback_query
        
        if not templates:
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            
            if subgroup_id:
                subgroup_name = group_info.get("subgroups", {}).get(subgroup_id, subgroup_id)
                message = f"📭 *В подгруппе '{subgroup_name}' нет шаблонов для удаления*"
            else:
                message = f"📭 *В группе '{group_info.get('name', group_id)}' нет шаблонов для удаления*"
            
            await query.edit_message_text(message, parse_mode='Markdown')
            return ConversationHandler.END
        
        context.user_data['template_delete']['templates'] = templates
        
        keyboard = get_templates_keyboard(templates)
        
        groups_data = load_groups()
        group_info = groups_data.get("groups", {}).get(group_id, {})
        
        if subgroup_id:
            subgroup_name = group_info.get("subgroups", {}).get(subgroup_id, subgroup_id)
            message = f"🗑️ *ВЫБЕРИТЕ ШАБЛОН ДЛЯ УДАЛЕНИЯ ИЗ ПОДГРУППЫ '{subgroup_name}':*"
        else:
            message = f"🗑️ *ВЫБЕРИТЕ ШАБЛОН ДЛЯ УДАЛЕНИЯ ИЗ ГРУППЫ '{group_info.get('name', group_id)}':*"
        
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return DELETE_TEMPLATE_SELECT

    async def delete_template_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора шаблона для удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            # Возврат к выбору группы/подгруппы
            if context.user_data['template_delete'].get('subgroup_id'):
                group_id = context.user_data['template_delete']['group_id']
                groups_data = load_groups()
                group_info = groups_data.get("groups", {}).get(group_id, {})
                subgroups = group_info.get("subgroups", {})
                
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}':*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return DELETE_TEMPLATE_SUBGROUP
            else:
                accessible_groups = get_user_accessible_groups(query.from_user.id)
                keyboard = get_groups_keyboard(accessible_groups)
                await query.edit_message_text(
                    "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ ШАБЛОНА*",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return DELETE_TEMPLATE_GROUP
        
        if data.startswith("select_template_"):
            template_id = data.replace("select_template_", "")
            template = get_template_by_id(template_id)
            
            if not template:
                await query.edit_message_text("❌ Шаблон не найден")
                return ConversationHandler.END
            
            context.user_data['template_delete']['template_id'] = template_id
            context.user_data['template_delete']['template'] = template
            
            keyboard = get_confirmation_keyboard("confirm_delete_template", "cancel_delete_template")
            
            await query.edit_message_text(
                f"⚠️ *ВЫ УВЕРЕНЫ, ЧТО ХОТИТЕ УДАЛИТЬ ШАБЛОН?*\n\n"
                f"📝 *Название:* {template.get('name', 'Без названия')}\n"
                f"🏘️ *Группа:* {template.get('group', 'Не указана')}\n"
                f"📁 *Подгруппа:* {template.get('subgroup', 'Не указана')}\n\n"
                f"❌ *Это действие нельзя отменить!*",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            return DELETE_TEMPLATE_CONFIRM

    async def delete_template_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения удаления шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_delete_template":
            template_id = context.user_data['template_delete']['template_id']
            template_name = context.user_data['template_delete']['template'].get('name', 'Без названия')
            
            # Удаляем шаблон
            success = remove_template(template_id)
            
            if success:
                await query.edit_message_text(
                    f"✅ *Шаблон '{template_name}' успешно удален!*",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ *Ошибка при удалении шаблона '{template_name}'*",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text("❌ Удаление отменено")
        
        # Очищаем временные данные
        context.user_data.pop('template_delete', None)
        return ConversationHandler.END

    # =============================================================================
    # ОБРАБОТЧИКИ КНОПОК
    # =============================================================================

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки шаблонов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if not is_authorized(user_id):
            await query.edit_message_text("❌ Недостаточно прав")
            return
        
        try:
            if data == "back":
                from menu_manager import get_templates_menu
                keyboard = get_templates_menu(user_id)
                await query.message.reply_text(
                    "📁 УПРАВЛЕНИЕ ШАБЛОНАМИ",
                    reply_markup=keyboard
                )
                await query.message.delete()
            
            elif data.startswith("select_group_"):
                if 'template_list' in context.user_data:
                    await self.handle_template_list_group(update, context)
                elif 'template_creation' in context.user_data:
                    await self.create_template_group(update, context)
                elif 'template_delete' in context.user_data:
                    await self.delete_template_group(update, context)
            
            elif data.startswith("select_subgroup_"):
                if 'template_list' in context.user_data:
                    await self.handle_template_list_subgroup(update, context)
                elif 'template_creation' in context.user_data:
                    await self.create_template_subgroup(update, context)
                elif 'template_delete' in context.user_data:
                    await self.delete_template_subgroup(update, context)
            
            elif data.startswith("select_template_"):
                if 'template_list' in context.user_data:
                    await self.handle_template_select(update, context)
                elif 'template_delete' in context.user_data:
                    await self.delete_template_select(update, context)
            
            elif data.startswith("templates_page_"):
                page = int(data.replace("templates_page_", ""))
                templates = context.user_data.get('current_templates', {})
                from menu_manager import get_templates_keyboard
                keyboard = get_templates_keyboard(templates, page)
                await query.edit_message_reply_markup(reply_markup=keyboard)
            
            else:
                await query.edit_message_text(
                    "🛠️ Функция в разработке",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка в обработчике шаблонов: {e}")
            await query.edit_message_text(
                "❌ Ошибка при обработке запроса",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
            )

    async def handle_edit_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора поля для редактирования"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        field = data.replace("edit_field_", "")
        
        # Здесь будет логика для каждого поля
        await query.edit_message_text(
            f"✏️ *Редактирование поля: {field}*\n\nЭта функция в разработке...",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END

    async def cancel_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена операции с шаблоном"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        context.user_data.pop('template_creation', None)
        context.user_data.pop('template_edit', None)
        context.user_data.pop('template_delete', None)
        context.user_data.pop('template_list', None)
        context.user_data.pop('current_templates', None)
        
        from menu_manager import get_main_menu
        await update.message.reply_text(
            "❌ Операция с шаблоном отменена",
            reply_markup=get_main_menu(user_id)
        )
        return ConversationHandler.END

    def get_conversation_handler(self):
        """Получить ConversationHandler для шаблонов"""
        return ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^📋 Список шаблонов$"), self.show_templates_list),
                MessageHandler(filters.Regex("^➕ Добавить новый$"), self.start_create_template),
                MessageHandler(filters.Regex("^✏️ Редактировать$"), self.start_edit_template),
                MessageHandler(filters.Regex("^🗑️ Удалить$"), self.start_delete_template),
            ],
            states={
                # States for template list
                TEMPLATE_GROUP: [
                    CallbackQueryHandler(self.handle_template_list_group, pattern="^(select_group_|back)"),
                ],
                TEMPLATE_SUBGROUP: [
                    CallbackQueryHandler(self.handle_template_list_subgroup, pattern="^(select_subgroup_|back)"),
                ],
                
                # States for template creation
                CREATE_GROUP: [
                    CallbackQueryHandler(self.create_template_group, pattern="^(select_group_|back)"),
                ],
                CREATE_SUBGROUP: [
                    CallbackQueryHandler(self.create_template_subgroup, pattern="^(select_subgroup_|back)"),
                ],
                CREATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_template_name)],
                CREATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_template_text)],
                CREATE_IMAGE: [
                    CallbackQueryHandler(self.create_template_image_choice, pattern="^(add_image|skip_image|back)"),
                    MessageHandler(filters.PHOTO | filters.Document.IMAGE, self.create_template_image_receive),
                ],
                CREATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.create_template_time)],
                CREATE_DAY: [
                    CallbackQueryHandler(self.create_template_day, pattern="^(select_day_|back)"),
                ],
                CREATE_FREQUENCY: [
                    CallbackQueryHandler(self.create_template_frequency, pattern="^(frequency_|back)"),
                ],
                CREATE_SECOND_DAY: [
                    CallbackQueryHandler(self.create_template_second_day, pattern="^(select_day_|back)"),
                ],
                CREATE_CONFIRM: [
                    CallbackQueryHandler(self.create_template_confirmation, pattern="^(confirm_create_template|edit_create_template)"),
                ],
                
                # States for template editing
                EDIT_SELECT: [
                    CallbackQueryHandler(self.create_template_group, pattern="^(select_group_|back)"),
                ],
                EDIT_FIELD: [
                    CallbackQueryHandler(self.handle_edit_field, pattern="^edit_field_"),
                ],
                
                # States for template deletion
                DELETE_GROUP: [
                    CallbackQueryHandler(self.delete_template_group, pattern="^(select_group_|back)"),
                ],
                DELETE_SUBGROUP: [
                    CallbackQueryHandler(self.delete_template_subgroup, pattern="^(select_subgroup_|back)"),
                ],
                DELETE_SELECT: [
                    CallbackQueryHandler(self.delete_template_select, pattern="^(select_template_|back)"),
                ],
                DELETE_CONFIRM: [
                    CallbackQueryHandler(self.delete_template_confirmation, pattern="^(confirm_delete_template|cancel_delete_template)"),
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_operation)],
            name="template_conversation"
        )

# Глобальный экземпляр менеджера шаблонов
template_manager = TemplateManager()
