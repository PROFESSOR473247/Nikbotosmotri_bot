# ===== ФУНКЦИИ ДЛЯ НОВОГО МЕНЮ ШАБЛОНОВ =====

def get_user_template_access(user_id):
    """Возвращает информацию о доступе пользователя к шаблонам"""
    try:
        accessible_groups = get_user_accessible_groups(user_id)
        all_templates = get_all_templates()
        
        user_templates = {}
        templates_by_group = {}
        
        # Фильтруем шаблоны по доступным группам
        for template_id, template in all_templates.items():
            template_group = template.get('group')
            if template_group in accessible_groups:
                user_templates[template_id] = template
                
                # Группируем по группам
                if template_group not in templates_by_group:
                    templates_by_group[template_group] = []
                templates_by_group[template_group].append((template_id, template))
        
        return {
            'accessible_groups': accessible_groups,
            'user_templates': user_templates,
            'templates_by_group': templates_by_group,
            'total_templates': len(user_templates),
            'total_groups': len(accessible_groups)
        }
    except Exception as e:
        print(f"❌ Ошибка получения доступа пользователя {user_id} к шаблонам: {e}")
        return {
            'accessible_groups': {},
            'user_templates': {},
            'templates_by_group': {},
            'total_templates': 0,
            'total_groups': 0
        }

def format_all_templates_info(user_id):
    """Форматирует информацию о всех шаблонах пользователя"""
    try:
        access_info = get_user_template_access(user_id)
        
        if not access_info['user_templates']:
            return "📭 У вас нет доступных шаблонов"
        
        message = "📋 **Все ваши шаблоны:**\n\n"
        
        # Группируем по группам для лучшего отображения
        for group_id, templates in access_info['templates_by_group'].items():
            group_name = access_info['accessible_groups'].get(group_id, {}).get('name', group_id)
            message += f"**🏷️ {group_name}:**\n"
            
            for i, (template_id, template) in enumerate(templates, 1):
                days_count = len(safe_get_template_value(template, 'days', []))
                has_image = "🖼️" if template.get('image') else ""
                template_name = safe_get_template_value(template, 'name', 'Без названия')
                template_time = safe_get_template_value(template, 'time', 'Не указано')
                
                message += f"  {i}. **{template_name}** {has_image}\n"
                message += f"     ⏰ {template_time} | 📅 {days_count} дней\n"
                message += f"     📄 {template['text'][:50]}...\n\n"
        
        message += f"**Всего:** {access_info['total_templates']} шаблонов в {access_info['total_groups']} группах"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования всех шаблонов: {e}")
        return "❌ Ошибка загрузки информации о шаблонах"

def format_group_templates_detailed(group_id):
    """Детальная информация о шаблонах группы"""
    try:
        templates = get_templates_by_group(group_id)
        
        if not templates:
            return f"📭 В этой группе нет шаблонов"
        
        groups_data = load_groups()
        group_name = groups_data['groups'].get(group_id, {}).get('name', group_id)
        
        message = f"**🏷️ Группа: {group_name}**\n\n"
        
        for i, (template_id, template) in enumerate(templates, 1):
            days_names = safe_format_days_list(template.get('days', []))
            frequency = safe_get_frequency_name(template.get('frequency', 'Не указана'))
            has_image = "✅ Есть" if template.get('image') else "❌ Нет"
            
            message += f"**{i}. {template['name']}**\n"
            message += f"   📄 Текст: {template['text'][:80]}...\n"
            message += f"   🖼️ Изображение: {has_image}\n"
            message += f"   ⏰ Время: {template.get('time', 'Не указано')}\n"
            message += f"   📅 Дни: {', '.join(days_names) if days_names else 'Не указаны'}\n"
            message += f"   🔄 Периодичность: {frequency}\n\n"
        
        return message
    except Exception as e:
        print(f"❌ Ошибка форматирования детальной информации группы {group_id}: {e}")
        return f"❌ Ошибка загрузки информации о группе"