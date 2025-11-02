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
    get_group_templates, get_subgroup_templates
)
from menu_manager import (
    get_templates_keyboard, get_groups_keyboard, get_subgroups_keyboard,
    get_days_keyboard, get_frequency_keyboard, get_edit_template_keyboard,
    get_confirmation_keyboard, get_back_button
)

# Состояния для создания шаблона
TEMPLATE_GROUP, TEMPLATE_SUBGROUP, TEMPLATE_NAME, TEMPLATE_TEXT, TEMPLATE_IMAGE, TEMPLATE_TIME, TEMPLATE_DAY, TEMPLATE_FREQUENCY, TEMPLATE_SECOND_DAY, TEMPLATE_CONFIRM = range(10)

# Состояния для редактирования шаблона
EDIT_TEMPLATE_SELECT, EDIT_TEMPLATE_FIELD, EDIT_TEMPLATE_GROUP, EDIT_TEMPLATE_SUBGROUP, EDIT_TEMPLATE_TEXT, EDIT_TEMPLATE_IMAGE, EDIT_TEMPLATE_TIME, EDIT_TEMPLATE_FREQUENCY, EDIT_TEMPLATE_CONFIRM = range(9)

# Состояния для удаления шаблона
DELETE_TEMPLATE_GROUP, DELETE_TEMPLATE_SUBGROUP, DELETE_TEMPLATE_SELECT, DELETE_TEMPLATE_CONFIRM = range(4)

class TemplateManager:
    def __init__(self):
        self.temp_data = {}

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

    async def show_template_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список доступных групп для выбора шаблонов"""
        user_id = update.effective_user.id
        accessible_groups = get_user_accessible_groups(user_id)
        
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "📁 ВЫБЕРИТЕ ГРУППУ ДЛЯ ПРОСМОТРА ШАБЛОНОВ:",
            reply_markup=keyboard
        )

    async def handle_template_group_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для просмотра шаблонов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            
            # Получаем подгруппы
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                # Если есть подгруппы, показываем их
                context.user_data['selected_group'] = group_id
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}':",
                    reply_markup=keyboard
                )
            else:
                # Если подгрупп нет, показываем шаблоны напрямую
                templates = get_group_templates(group_id)
                if not templates:
                    await query.edit_message_text(f"❌ В группе '{group_info.get('name', group_id)}' нет шаблонов")
                    return
                
                keyboard = get_templates_keyboard(templates)
                await query.edit_message_text(
                    f"📝 ШАБЛОНЫ В ГРУППЕ '{group_info.get('name', group_id)}':",
                    reply_markup=keyboard
                )

    async def handle_template_subgroup_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для просмотра шаблонов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = parts[1]
            
            templates = get_subgroup_templates(group_id, subgroup_id)
            if not templates:
                await query.edit_message_text("❌ В этой подгруппе нет шаблонов")
                return
            
            keyboard = get_templates_keyboard(templates)
            
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroup_name = group_info.get("subgroups", {}).get(subgroup_id, subgroup_id)
            
            await query.edit_message_text(
                f"📝 ШАБЛОНЫ В ПОДГРУППЕ '{subgroup_name}':",
                reply_markup=keyboard
            )

    async def handle_template_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора конкретного шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
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
            text_preview = template['text'][:100] + "..." if len(template['text']) > 100 else template['text']
            info += f"📋 *Текст:* {text_preview}\n"
        
        if template.get('group'):
            info += f"🏘️ *Группа:* {template['group']}\n"
        
        if template.get('subgroup'):
            info += f"📁 *Подгруппа:* {template['subgroup']}\n"
        
        if template.get('image'):
            info += f"🖼️ *Есть изображение:* Да\n"
        else:
            info += f"🖼️ *Есть изображение:* Нет\n"
        
        if template.get('schedule_time'):
            info += f"⏰ *Время:* {template['schedule_time']}\n"
        
        if template.get('frequency'):
            info += f"🔄 *Периодичность:* {template['frequency']}\n"
        
        if template.get('days'):
            days_str = ", ".join(template['days'])
            info += f"📅 *Дни:* {days_str}\n"
        
        if template.get('created_at'):
            created = datetime.fromisoformat(template['created_at']).strftime("%d.%m.%Y %H:%M")
            info += f"📅 *Создан:* {created}\n"
        
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
        
        user_role = get_user_role(user_id)
        if user_role not in ["admin", "руководитель"]:
            await update.message.reply_text("❌ Недостаточно прав для создания шаблонов")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
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

    async def template_group_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['template_creation']['group_id'] = group_id
            
            # Получаем подгруппы
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 *ШАГ 2/8: ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}'*\n\n"
                    f"ℹ️ Если подгруппа не нужна, нажмите '🔙 Назад'",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return TEMPLATE_SUBGROUP
            else:
                # Пропускаем шаг подгруппы
                context.user_data['template_creation']['subgroup_id'] = None
                await query.edit_message_text(
                    "📝 *ШАГ 3/8: ВВЕДИТЕ НАЗВАНИЕ ШАБЛОНА*\n\n"
                    "ℹ️ Название должно быть понятным и описывать назначение шаблона",
                    parse_mode='Markdown'
                )
                return TEMPLATE_NAME

    async def template_subgroup_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            subgroup_id = parts[1]
            
            context.user_data['template_creation']['subgroup_id'] = subgroup_id
            
            await query.edit_message_text(
                "📝 *ШАГ 3/8: ВВЕДИТЕ НАЗВАНИЕ ШАБЛОНА*\n\n"
                "ℹ️ Название должно быть понятным и описывать назначение шаблона",
                parse_mode='Markdown'
            )
            return TEMPLATE_NAME

    async def template_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    async def template_text_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода текста шаблона"""
        template_text = update.message.text.strip()
        
        if len(template_text) < 5:
            await update.message.reply_text("❌ Текст слишком короткий. Введите еще раз:")
            return TEMPLATE_TEXT
        
        context.user_data['template_creation']['text'] = template_text
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼️ Добавить изображение", callback_data="add_image")],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_image")],
            get_back_button()[0]
        ])
        
        await update.message.reply_text(
            "🖼️ *ШАГ 5/8: ДОБАВИТЬ ИЗОБРАЖЕНИЕ?*\n\n"
            "ℹ️ Изображение будет отправляться вместе с текстом шаблона",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEMPLATE_IMAGE

    async def template_image_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                "⏰ *ШАГ 6/8: ВВЕДИТЕ ВРЕМЯ АКТИВАЦИИ (формат ЧЧ:ММ по МСК)*\n\n"
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

    async def template_image_receive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "⏰ *ШАГ 6/8: ВВЕДИТЕ ВРЕМЯ АКТИВАЦИИ (формат ЧЧ:ММ по МСК)*\n\n"
            "ℹ️ Например: 09:00 или 14:30",
            parse_mode='Markdown'
        )
        
        return TEMPLATE_TIME

    async def template_time_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода времени активации"""
        time_input = update.message.text.strip()
        
        # Проверка формата времени
        try:
            hours, minutes = map(int, time_input.split(':'))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 09:00):")
            return TEMPLATE_TIME
        
        context.user_data['template_creation']['time'] = time_input
        
        keyboard = get_days_keyboard()
        await update.message.reply_text(
            "📅 *ШАГ 7/8: ВЫБЕРИТЕ ДЕНЬ НЕДЕЛИ АКТИВАЦИИ*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return TEMPLATE_DAY

    async def template_day_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора дня недели"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            await query.edit_message_text(
                "⏰ *ШАГ 6/8: ВВЕДИТЕ ВРЕМЯ АКТИВАЦИИ (формат ЧЧ:ММ по МСК)*\n\n"
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

    async def template_frequency_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора периодичности"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "back":
            keyboard = get_days_keyboard()
            await query.edit_message_text(
                "📅 *ШАГ 7/8: ВЫБЕРИТЕ ДЕНЬ НЕДЕЛИ АКТИВАЦИИ*",
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
                return await self.show_template_confirmation(update, context)

    async def template_second_day_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        keyboard = get_confirmation_keyboard("confirm_template", "edit_template")
        
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
        text += f"🏘️ *Группа:* {template_data.get('group_id')}\n"
        
        if template_data.get('subgroup_id'):
            text += f"📁 *Подгруппа:* {template_data.get('subgroup_id')}\n"
        
        text += f"📋 *Текст:* {template_data.get('text', '')[:50]}...\n"
        
        if template_data.get('image'):
            text += f"🖼️ *Изображение:* Да\n"
        else:
            text += f"🖼️ *Изображение:* Нет\n"
        
        text += f"⏰ *Время:* {template_data.get('time')} (МСК)\n"
        text += f"📅 *День:* {template_data.get('day_name')}\n"
        
        if template_data.get('second_day_name'):
            text += f"📅 *Второй день:* {template_data.get('second_day_name')}\n"
        
        text += f"🔄 *Периодичность:* {template_data.get('frequency')}\n\n"
        
        text += "❓ *Все верно?*"
        
        return text

    async def template_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения создания шаблона"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "confirm_template":
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
                'schedule_time': template_data['time'],
                'frequency': template_data['frequency'],
                'days': [template_data['day_name']] + ([template_data['second_day_name']] if template_data.get('second_day_name') else []),
                'created_at': datetime.now().isoformat(),
                'created_by': template_data['user_id']
            }
            
            # Сохраняем в базу
            templates_data = load_templates()
            templates_data['templates'][template_id] = template_to_save
            save_templates(templates_data)
            
            # Очищаем временные данные
            context.user_data.pop('template_creation', None)
            
            from menu_manager import get_main_menu
            await query.edit_message_text(
                f"✅ *Шаблон '{template_data['name']}' успешно создан!*\n\n"
                f"🆔 ID шаблона: `{template_id}`",
                reply_markup=get_main_menu(template_data['user_id']),
                parse_mode='Markdown'
            )
            
            return ConversationHandler.END
        
        elif data == "edit_template":
            keyboard = get_edit_template_keyboard()
            await query.edit_message_text(
                "✏️ *КАКОЙ ПУНКТ ВЫ ХОТИТЕ ИЗМЕНИТЕ?*",
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
        
        user_role = get_user_role(user_id)
        if user_role not in ["admin", "руководитель"]:
            await update.message.reply_text("❌ Недостаточно прав для редактирования шаблонов")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        context.user_data['template_edit'] = {
            'user_id': user_id,
            'step': 'group'
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
        
        user_role = get_user_role(user_id)
        if user_role not in ["admin", "руководитель"]:
            await update.message.reply_text("❌ Недостаточно прав для удаления шаблонов")
            return ConversationHandler.END
        
        accessible_groups = get_user_accessible_groups(user_id)
        if not accessible_groups:
            await update.message.reply_text("❌ У вас нет доступа к каким-либо группам")
            return ConversationHandler.END
        
        # Инициализируем template_delete
        context.user_data['template_delete'] = {
            'user_id': user_id
        }
        
        keyboard = get_groups_keyboard(accessible_groups)
        await update.message.reply_text(
            "🏘️ *ВЫБЕРИТЕ ГРУППУ ДЛЯ УДАЛЕНИЯ ШАБЛОНА*",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        return DELETE_TEMPLATE_GROUP

    async def handle_delete_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора группы для удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, инициализирован ли template_delete в user_data
        if 'template_delete' not in context.user_data:
            context.user_data['template_delete'] = {}
        
        if data.startswith("select_group_"):
            group_id = data.replace("select_group_", "")
            context.user_data['template_delete']['group_id'] = group_id
            
            # Получаем подгруппы
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroups = group_info.get("subgroups", {})
            
            if subgroups:
                keyboard = get_subgroups_keyboard(subgroups, group_id)
                await query.edit_message_text(
                    f"📁 ВЫБЕРИТЕ ПОДГРУППУ В ГРУППЕ '{group_info.get('name', group_id)}':",
                    reply_markup=keyboard
                )
                return DELETE_TEMPLATE_SUBGROUP
            else:
                # Если подгрупп нет, показываем шаблоны напрямую
                templates = get_group_templates(group_id)
                if not templates:
                    await query.edit_message_text(f"❌ В группе '{group_info.get('name', group_id)}' нет шаблонов")
                    return ConversationHandler.END
                
                context.user_data['template_delete']['templates'] = templates
                keyboard = get_templates_keyboard(templates)
                await query.edit_message_text(
                    f"🗑️ ВЫБЕРИТЕ ШАБЛОН ДЛЯ УДАЛЕНИЯ ИЗ ГРУППЫ '{group_info.get('name', group_id)}':",
                    reply_markup=keyboard
                )
                return DELETE_TEMPLATE_SELECT

    async def handle_delete_subgroup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора подгруппы для удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, инициализирован ли template_delete в user_data
        if 'template_delete' not in context.user_data:
            context.user_data['template_delete'] = {}
        
        if data.startswith("select_subgroup_"):
            parts = data.replace("select_subgroup_", "").split("_")
            group_id = parts[0]
            subgroup_id = parts[1]
            
            context.user_data['template_delete']['subgroup_id'] = subgroup_id
            
            templates = get_subgroup_templates(group_id, subgroup_id)
            if not templates:
                await query.edit_message_text("❌ В этой подгруппе нет шаблонов")
                return ConversationHandler.END
            
            context.user_data['template_delete']['templates'] = templates
            keyboard = get_templates_keyboard(templates)
            
            groups_data = load_groups()
            group_info = groups_data.get("groups", {}).get(group_id, {})
            subgroup_name = group_info.get("subgroups", {}).get(subgroup_id, subgroup_id)
            
            await query.edit_message_text(
                f"🗑️ ВЫБЕРИТЕ ШАБЛОН ДЛЯ УДАЛЕНИЯ ИЗ ПОДГРУППЫ '{subgroup_name}':",
                reply_markup=keyboard
            )
            return DELETE_TEMPLATE_SELECT

    async def handle_delete_template_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора шаблона для удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, инициализирован ли template_delete в user_data
        if 'template_delete' not in context.user_data:
            context.user_data['template_delete'] = {}
        
        if data.startswith("select_template_"):
            template_id = data.replace("select_template_", "")
            template = get_template_by_id(template_id)
            
            if not template:
                await query.edit_message_text("❌ Шаблон не найден")
                return ConversationHandler.END
            
            context.user_data['template_delete']['template_id'] = template_id
            context.user_data['template_delete']['template'] = template
            
            keyboard = get_confirmation_keyboard("confirm_delete", "cancel_delete")
            
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

    async def handle_delete_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения удаления"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Проверяем, инициализирован ли template_delete в user_data
        if 'template_delete' not in context.user_data:
            await query.edit_message_text("❌ Ошибка: данные удаления не найдены")
            return ConversationHandler.END
        
        if data == "confirm_delete":
            template_id = context.user_data['template_delete']['template_id']
            template_name = context.user_data['template_delete']['template'].get('name', 'Без названия')
            
            # Удаляем шаблон
            success = remove_template(template_id)
            
            if success:
                await query.edit_message_text(
                    f"✅ Шаблон '{template_name}' успешно удален!",
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка при удалении шаблона '{template_name}'",
                    parse_mode='Markdown'
                )
        else:
            await query.edit_message_text("❌ Удаление отменено")
        
        # Очищаем временные данные
        context.user_data.pop('template_delete', None)
        return ConversationHandler.END

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
                await self.handle_template_group_select(update, context)
            elif data.startswith("select_subgroup_"):
                await self.handle_template_subgroup_select(update, context)
            elif data.startswith("select_template_"):
                await self.handle_template_select(update, context)
            elif data.startswith("groups_page_"):
                page = int(data.replace("groups_page_", ""))
                accessible_groups = get_user_accessible_groups(user_id)
                from menu_manager import get_groups_keyboard
                keyboard = get_groups_keyboard(accessible_groups, page)
                await query.edit_message_reply_markup(reply_markup=keyboard)
            elif data.startswith("subgroups_page_"):
                parts = data.replace("subgroups_page_", "").split("_")
                group_id = parts[0]
                page = int(parts[1])
                
                groups_data = load_groups()
                group_info = groups_data.get("groups", {}).get(group_id, {})
                subgroups = group_info.get("subgroups", {})
                
                from menu_manager import get_subgroups_keyboard
                keyboard = get_subgroups_keyboard(subgroups, group_id, page)
                await query.edit_message_reply_markup(reply_markup=keyboard)
            elif data.startswith("templates_page_"):
                page = int(data.replace("templates_page_", ""))
                templates = context.user_data.get('current_templates', {})
                from menu_manager import get_templates_keyboard
                keyboard = get_templates_keyboard(templates, page)
                await query.edit_message_reply_markup(reply_markup=keyboard)
            else:
                await query.edit_message_text(
                    "🛠️ Функция шаблонов в разработке",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
                )
                
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике шаблонов: {e}")
            await query.edit_message_text(
                "❌ Ошибка при обработке шаблона",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
            )

    async def handle_unexpected_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неожиданных callback-ов"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "❌ Произошла ошибка. Сессия была сброшена.\n\n"
            "Пожалуйста, начните операцию заново.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back")]])
        )
        return ConversationHandler.END

    async def handle_edit_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора поля для редактирования"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        field = data.replace("edit_field_", "")
        
        # Здесь будет логика для каждого поля
        await query.edit_message_text(f"✏️ Редактирование поля: {field}\n\nЭта функция в разработке...")
        
        return ConversationHandler.END

    async def cancel_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена создания/редактирования шаблона"""
        user_id = update.effective_user.id
        
        # Очищаем временные данные
        context.user_data.pop('template_creation', None)
        context.user_data.pop('template_edit', None)
        context.user_data.pop('template_delete', None)
        
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
                MessageHandler(filters.Regex("^📋 Список шаблонов$"), self.show_template_list),
                MessageHandler(filters.Regex("^➕ Добавить новый$"), self.start_create_template),
                MessageHandler(filters.Regex("^✏️ Редактировать$"), self.start_edit_template),
                MessageHandler(filters.Regex("^🗑️ Удалить$"), self.start_delete_template),
            ],
            states={
                # States for template creation
                TEMPLATE_GROUP: [
                    CallbackQueryHandler(self.template_group_selected, pattern="^(select_group_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                TEMPLATE_SUBGROUP: [
                    CallbackQueryHandler(self.template_subgroup_selected, pattern="^(select_subgroup_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                TEMPLATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.template_name_input)],
                TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.template_text_input)],
                TEMPLATE_IMAGE: [
                    CallbackQueryHandler(self.template_image_choice, pattern="^(add_image|skip_image|back)"),
                    MessageHandler(filters.PHOTO | filters.Document.IMAGE, self.template_image_receive),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                TEMPLATE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.template_time_input)],
                TEMPLATE_DAY: [
                    CallbackQueryHandler(self.template_day_selected, pattern="^(select_day_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                TEMPLATE_FREQUENCY: [
                    CallbackQueryHandler(self.template_frequency_selected, pattern="^(frequency_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                TEMPLATE_SECOND_DAY: [
                    CallbackQueryHandler(self.template_second_day_selected, pattern="^(select_day_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                TEMPLATE_CONFIRM: [
                    CallbackQueryHandler(self.template_confirmation_handler, pattern="^(confirm_template|edit_template)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                
                # States for template editing
                EDIT_TEMPLATE_SELECT: [
                    CallbackQueryHandler(self.template_group_selected, pattern="^(select_group_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                EDIT_TEMPLATE_FIELD: [
                    CallbackQueryHandler(self.handle_edit_field, pattern="^edit_field_"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                
                # States for template deletion
                DELETE_TEMPLATE_GROUP: [
                    CallbackQueryHandler(self.handle_delete_group, pattern="^(select_group_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                DELETE_TEMPLATE_SUBGROUP: [
                    CallbackQueryHandler(self.handle_delete_subgroup, pattern="^(select_subgroup_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                DELETE_TEMPLATE_SELECT: [
                    CallbackQueryHandler(self.handle_delete_template_select, pattern="^(select_template_|back)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
                DELETE_TEMPLATE_CONFIRM: [
                    CallbackQueryHandler(self.handle_delete_confirm, pattern="^(confirm|cancel)"),
                    CallbackQueryHandler(self.handle_unexpected_callback)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_template)],
            name="template_conversation"
        )

# Глобальный экземпляр менеджера шаблонов
template_manager = TemplateManager()
