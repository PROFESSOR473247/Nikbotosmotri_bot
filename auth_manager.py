import json
import os
from database import db

class AuthManager:
    def __init__(self):
        self.superadmin_id = 812934047  # Ваш ID суперадминистратора
        self.roles = ['guest', 'user', 'admin', 'superadmin']
        print("🔐 AuthManager инициализирован")

    def get_user_role(self, user_id):
        """Возвращает роль пользователя"""
        try:
            conn = db.get_connection()
            if not conn:
                print("❌ Не удалось подключиться к базе данных для получения роли")
                return 'guest'
            
            cursor = conn.cursor()
            cursor.execute('SELECT role FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                return result[0]
            else:
                # Если пользователь не найден, создаем запись гостя
                self._create_user_record(user_id, 'Неизвестный', 'guest')
                return 'guest'
                
        except Exception as e:
            print(f"❌ Ошибка получения роли пользователя {user_id}: {e}")
            return 'guest'

    def _create_user_record(self, user_id, username, role='guest'):
        """Создает запись пользователя в базе данных"""
        try:
            from telegram import Update
            from handlers.start_handlers import get_user_display_name
            
            # Получаем информацию о пользователе
            full_name = get_user_display_name(user_id)
            
            conn = db.get_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name
            ''', (user_id, username, full_name, role))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Создана запись пользователя {user_id} с ролью {role}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания записи пользователя {user_id}: {e}")
            return False

    def update_user_role_if_needed(self, user_id):
        """Гарантирует, что суперадмин всегда имеет права администратора"""
        if user_id == self.superadmin_id:
            current_role = self.get_user_role(user_id)
            if current_role != 'superadmin' and current_role != 'admin':
                success, message = db.update_user_role(user_id, 'superadmin')
                if success:
                    print(f"👑 Восстановлены права суперадмина для {user_id}")
                else:
                    print(f"❌ Ошибка восстановления прав суперадмина: {message}")
            return True
        return False

    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором"""
        role = self.get_user_role(user_id)
        return role in ['admin', 'superadmin']

    def is_superadmin(self, user_id):
        """Проверяет, является ли пользователь суперадмином"""
        return user_id == self.superadmin_id

    def can_manage_users(self, user_id):
        """Проверяет, может ли пользователь управлять пользователями"""
        return self.is_admin(user_id)

    def can_manage_templates(self, user_id):
        """Проверяет, может ли пользователь управлять шаблонами"""
        return True  # Все авторизованные пользователи могут управлять шаблонами

    def can_manage_tasks(self, user_id):
        """Проверяет, может ли пользователь управлять задачами"""
        return True  # Все авторизованные пользователи могут управлять задачами

    def can_access_admin_panel(self, user_id):
        """Проверяет, есть ли у пользователя доступ к админ-панели"""
        return self.is_admin(user_id)

    def get_user_permissions(self, user_id):
        """Возвращает все разрешения пользователя"""
        role = self.get_user_role(user_id)
        
        permissions = {
            'role': role,
            'manage_users': self.can_manage_users(user_id),
            'manage_templates': self.can_manage_templates(user_id),
            'manage_tasks': self.can_manage_tasks(user_id),
            'access_admin_panel': self.can_access_admin_panel(user_id),
            'is_superadmin': self.is_superadmin(user_id)
        }
        
        return permissions

    def register_user(self, user_id, username, full_name, role='guest'):
        """Регистрирует нового пользователя"""
        try:
            success, message = db.add_user(user_id, username, full_name, role)
            if success:
                print(f"✅ Зарегистрирован пользователь {user_id} с ролью {role}")
            else:
                print(f"❌ Ошибка регистрации пользователя {user_id}: {message}")
            return success, message
        except Exception as e:
            print(f"❌ Ошибка регистрации пользователя {user_id}: {e}")
            return False, f"Ошибка регистрации: {e}"

    def update_user_role(self, user_id, new_role):
        """Обновляет роль пользователя"""
        if new_role not in self.roles:
            return False, f"Неверная роль. Допустимые роли: {', '.join(self.roles)}"
        
        # Суперадмин не может быть понижен
        if user_id == self.superadmin_id and new_role != 'superadmin':
            return False, "Нельзя изменить роль суперадминистратора"
        
        success, message = db.update_user_role(user_id, new_role)
        if success:
            print(f"✅ Роль пользователя {user_id} изменена на {new_role}")
        else:
            print(f"❌ Ошибка изменения роли пользователя {user_id}: {message}")
        return success, message

    def delete_user(self, user_id):
        """Удаляет пользователя"""
        # Суперадмин не может быть удален
        if user_id == self.superadmin_id:
            return False, "Нельзя удалить суперадминистратора"
        
        success, message = db.delete_user(user_id)
        if success:
            print(f"✅ Пользователь {user_id} удален")
        else:
            print(f"❌ Ошибка удаления пользователя {user_id}: {message}")
        return success, message

    def get_all_users(self):
        """Возвращает всех пользователей"""
        try:
            users = db.get_all_users()
            print(f"✅ Получено {len(users)} пользователей")
            return users
        except Exception as e:
            print(f"❌ Ошибка получения списка пользователей: {e}")
            return []

    def grant_chat_access(self, user_id, chat_id):
        """Предоставляет доступ пользователю к чату"""
        success, message = db.grant_chat_access(user_id, chat_id)
        if success:
            print(f"✅ Пользователю {user_id} предоставлен доступ к чату {chat_id}")
        else:
            print(f"❌ Ошибка предоставления доступа к чату: {message}")
        return success, message

    def revoke_chat_access(self, user_id, chat_id):
        """Отзывает доступ пользователя к чату"""
        success, message = db.revoke_chat_access(user_id, chat_id)
        if success:
            print(f"✅ У пользователя {user_id} отозван доступ к чату {chat_id}")
        else:
            print(f"❌ Ошибка отзыва доступа к чату: {message}")
        return success, message

    def grant_template_group_access(self, user_id, group_id):
        """Предоставляет доступ пользователю к группе шаблонов"""
        success, message = db.grant_template_group_access(user_id, group_id)
        if success:
            print(f"✅ Пользователю {user_id} предоставлен доступ к группе {group_id}")
        else:
            print(f"❌ Ошибка предоставления доступа к группе: {message}")
        return success, message

    def revoke_template_group_access(self, user_id, group_id):
        """Отзывает доступ пользователя к группе шаблонов"""
        success, message = db.revoke_template_group_access(user_id, group_id)
        if success:
            print(f"✅ У пользователя {user_id} отозван доступ к группе {group_id}")
        else:
            print(f"❌ Ошибка отзыва доступа к группе: {message}")
        return success, message

    def get_user_chat_access(self, user_id):
        """Возвращает чаты, к которым у пользователя есть доступ"""
        try:
            chats = db.get_user_chat_access(user_id)
            print(f"✅ Пользователь {user_id} имеет доступ к {len(chats)} чатам")
            return chats
        except Exception as e:
            print(f"❌ Ошибка получения доступа к чатам: {e}")
            return []

    def get_user_template_group_access(self, user_id):
        """Возвращает группы шаблонов, к которым у пользователя есть доступ"""
        try:
            groups = db.get_user_template_group_access(user_id)
            print(f"✅ Пользователь {user_id} имеет доступ к {len(groups)} группам")
            return groups
        except Exception as e:
            print(f"❌ Ошибка получения доступа к группам: {e}")
            return []

    def validate_user_access(self, user_id, required_role='user'):
        """Проверяет, имеет ли пользователь достаточные права"""
        user_role = self.get_user_role(user_id)
        
        role_hierarchy = {
            'guest': 0,
            'user': 1,
            'admin': 2,
            'superadmin': 3
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level

    def get_user_stats(self, user_id):
        """Возвращает статистику пользователя"""
        try:
            role = self.get_user_role(user_id)
            chat_access = len(self.get_user_chat_access(user_id))
            group_access = len(self.get_user_template_group_access(user_id))
            
            stats = {
                'user_id': user_id,
                'role': role,
                'chat_access_count': chat_access,
                'group_access_count': group_access,
                'is_superadmin': self.is_superadmin(user_id),
                'is_admin': self.is_admin(user_id)
            }
            
            return stats
        except Exception as e:
            print(f"❌ Ошибка получения статистики пользователя {user_id}: {e}")
            return None

    def initialize_superadmin(self):
        """Инициализирует суперадминистратора при запуске"""
        try:
            # Гарантируем, что суперадмин существует и имеет правильную роль
    def get_user_display_name(user_id):
        """Простая заглушка для получения имени пользователя"""
            return f"User {user_id}"
            
            full_name = get_user_display_name(self.superadmin_id)
            success, message = self.register_user(
                self.superadmin_id, 
                'superadmin', 
                full_name, 
                'superadmin'
            )
            
            if success:
                print(f"👑 Суперадминистратор инициализирован: {self.superadmin_id}")
            else:
                print(f"⚠️ Суперадминистратор уже существует: {message}")
                
            return success
        except Exception as e:
            print(f"❌ Ошибка инициализации суперадминистратора: {e}")
            return False

# Глобальный экземпляр менеджера аутентификации
auth_manager = AuthManager()

# Инициализация при импорте
print("🔐 AuthManager загружен и готов к работе")
auth_manager.initialize_superadmin()
