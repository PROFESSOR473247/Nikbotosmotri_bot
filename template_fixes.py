"""
Файл с исправлениями для функций шаблонов
"""

from template_manager import get_templates_by_group

def get_template_by_name_and_group(template_name, group_id):
    """Возвращает шаблон по имени и группе"""
    try:
        templates = get_templates_by_group(group_id)
        for template_id, template in templates:
            if template.get('name') == template_name:
                return template_id, template
        return None, None
    except Exception as e:
        print(f"❌ Ошибка поиска шаблона по имени {template_name} в группе {group_id}: {e}")
        return None, None

def update_template(template_id, template_data):
    """Обновляет шаблон"""
    from template_manager import save_template
    try:
        template_data['id'] = template_id
        return save_template(template_data)
    except Exception as e:
        print(f"❌ Ошибка обновления шаблона {template_id}: {e}")
        return False

def delete_image(image_path):
    """Удаляет изображение"""
    import os
    try:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
            print(f"✅ Изображение удалено: {image_path}")
            return True
        return False
    except Exception as e:
        print(f"❌ Ошибка удаления изображения: {e}")
        return False
