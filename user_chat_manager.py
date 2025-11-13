import logging
from database import db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserChatManager:
    def __init__(self):
        self.db = db
    
    def get_connection(self):
        return self.db.get_connection()
    
    # ===== МЕТОДЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ =====
    
    def add_user(self, user_id, username, full_name, role='guest'):
        """Добавляет нового пользователя"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (user_id, username, full_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    role = EXCLUDED.role
            ''', (user_id, username, full_name, role))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Пользователь {user_id} добавлен/обновлен")
            return True, "Пользователь успешно добавлен"
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка добавления пользователя: {e}"
    
    def get_all_users(self):
        """Возвращает всех пользователей"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.role, u.created_at, u.is_active,
                       COUNT(DISTINCT uc.chat_id) as chat_count,
                       COUNT(DISTINCT ut.group_id) as group_count
                FROM users u
                LEFT JOIN user_chat_access uc ON u.user_id = uc.user_id
                LEFT JOIN user_template_group_access ut ON u.user_id = ut.user_id
                GROUP BY u.user_id
                ORDER BY u.created_at DESC
            ''')
            
            rows = cursor.fetchall()
            users = []
            
            for row in rows:
                user = {
                    'user_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'role': row[3],
                    'created_at': row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    'is_active': row[5],
                    'chat_count': row[6],
                    'group_count': row[7]
                }
                users.append(user)
            
            cursor.close()
            conn.close()
            
            return users
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def delete_user(self, user_id):
        """Удаляет пользователя"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            # Удаляем связи пользователя
            cursor.execute('DELETE FROM user_chat_access WHERE user_id = %s', (user_id,))
            cursor.execute('DELETE FROM user_template_group_access WHERE user_id = %s', (user_id,))
            
            # Удаляем пользователя
            cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Пользователь {user_id} удален")
            return True, "Пользователь успешно удален"
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления пользователя: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка удаления пользователя: {e}"
    
    def update_user_role(self, user_id, new_role):
        """Обновляет роль пользователя"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('UPDATE users SET role = %s WHERE user_id = %s', (new_role, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Роль пользователя {user_id} обновлена на {new_role}")
            return True, "Роль пользователя обновлена"
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления роли пользователя: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка обновления роли: {e}"
    
    # ===== МЕТОДЫ ДЛЯ TELEGRAM ЧАТОВ =====
    
    def add_telegram_chat(self, chat_id, chat_name, original_name=None):
        """Добавляет новый Telegram чат"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO telegram_chats (chat_id, chat_name, original_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET
                    chat_name = EXCLUDED.chat_name,
                    original_name = EXCLUDED.original_name
            ''', (chat_id, chat_name, original_name))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Telegram чат {chat_id} добавлен/обновлен")
            return True, "Telegram чат успешно добавлен"
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления Telegram чата: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка добавления чата: {e}"
    
    def get_all_chats(self):
        """Возвращает все Telegram чаты"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tc.chat_id, tc.chat_name, tc.original_name, tc.created_at, tc.is_active,
                       COUNT(uc.user_id) as user_count
                FROM telegram_chats tc
                LEFT JOIN user_chat_access uc ON tc.chat_id = uc.chat_id
                GROUP BY tc.chat_id
                ORDER BY tc.created_at DESC
            ''')
            
            rows = cursor.fetchall()
            chats = []
            
            for row in rows:
                chat = {
                    'chat_id': row[0],
                    'chat_name': row[1],
                    'original_name': row[2],
                    'created_at': row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else None,
                    'is_active': row[4],
                    'user_count': row[5]
                }
                chats.append(chat)
            
            cursor.close()
            conn.close()
            
            return chats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения чатов: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def delete_chat(self, chat_id):
        """Удаляет Telegram чат"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            # Удаляем связи чата
            cursor.execute('DELETE FROM user_chat_access WHERE chat_id = %s', (chat_id,))
            
            # Удаляем чат
            cursor.execute('DELETE FROM telegram_chats WHERE chat_id = %s', (chat_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Telegram чат {chat_id} удален")
            return True, "Telegram чат успешно удален"
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления чата: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка удаления чата: {e}"
    
    # ===== МЕТОДЫ ДЛЯ УПРАВЛЕНИЯ ДОСТУПОМ =====
    
    def grant_chat_access(self, user_id, chat_id):
        """Предоставляет доступ пользователю к чату"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_chat_access (user_id, chat_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, chat_id) DO NOTHING
            ''', (user_id, chat_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Пользователю {user_id} предоставлен доступ к чату {chat_id}")
            return True, "Доступ к чату предоставлен"
            
        except Exception as e:
            logger.error(f"❌ Ошибка предоставления доступа к чату: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка предоставления доступа: {e}"
    
    def revoke_chat_access(self, user_id, chat_id):
        """Отзывает доступ пользователя к чату"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_chat_access WHERE user_id = %s AND chat_id = %s', (user_id, chat_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ У пользователя {user_id} отозван доступ к чату {chat_id}")
            return True, "Доступ к чату отозван"
            
        except Exception as e:
            logger.error(f"❌ Ошибка отзыва доступа к чату: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка отзыва доступа: {e}"
    
    def grant_template_group_access(self, user_id, group_id):
        """Предоставляет доступ пользователю к группе шаблонов"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_template_group_access (user_id, group_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, group_id) DO NOTHING
            ''', (user_id, group_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Пользователю {user_id} предоставлен доступ к группе {group_id}")
            return True, "Доступ к группе предоставлен"
            
        except Exception as e:
            logger.error(f"❌ Ошибка предоставления доступа к группе: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка предоставления доступа: {e}"
    
    def revoke_template_group_access(self, user_id, group_id):
        """Отзывает доступ пользователя к группе шаблонов"""
        conn = self.get_connection()
        if not conn:
            return False, "Ошибка подключения к базе данных"
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_template_group_access WHERE user_id = %s AND group_id = %s', (user_id, group_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"✅ У пользователя {user_id} отозван доступ к группе {group_id}")
            return True, "Доступ к группе отозван"
            
        except Exception as e:
            logger.error(f"❌ Ошибка отзыва доступа к группе: {e}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            return False, f"Ошибка отзыва доступа: {e}"
    
    def get_user_chat_access(self, user_id):
        """Возвращает чаты, к которым у пользователя есть доступ"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tc.chat_id, tc.chat_name 
                FROM telegram_chats tc
                JOIN user_chat_access uc ON tc.chat_id = uc.chat_id
                WHERE uc.user_id = %s AND tc.is_active = TRUE
            ''', (user_id,))
            
            rows = cursor.fetchall()
            chats = [{'chat_id': row[0], 'chat_name': row[1]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return chats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения доступа к чатам: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def get_user_template_group_access(self, user_id):
        """Возвращает группы шаблонов, к которым у пользователя есть доступ"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tg.id, tg.name 
                FROM template_groups tg
                JOIN user_template_group_access ut ON tg.id = ut.group_id
                WHERE ut.user_id = %s
            ''', (user_id,))
            
            rows = cursor.fetchall()
            groups = [{'id': row[0], 'name': row[1]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return groups
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения доступа к группам: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def get_chat_users(self, chat_id):
        """Возвращает пользователей, имеющих доступ к чату"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.role
                FROM users u
                JOIN user_chat_access uc ON u.user_id = uc.user_id
                WHERE uc.chat_id = %s AND u.is_active = TRUE
            ''', (chat_id,))
            
            rows = cursor.fetchall()
            users = [{'user_id': row[0], 'username': row[1], 'full_name': row[2], 'role': row[3]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return users
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей чата: {e}")
            try:
                conn.close()
            except:
                pass
            return []
    
    def get_group_users(self, group_id):
        """Возвращает пользователей, имеющих доступ к группе шаблонов"""
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.user_id, u.username, u.full_name, u.role
                FROM users u
                JOIN user_template_group_access ut ON u.user_id = ut.user_id
                WHERE ut.group_id = %s AND u.is_active = TRUE
            ''', (group_id,))
            
            rows = cursor.fetchall()
            users = [{'user_id': row[0], 'username': row[1], 'full_name': row[2], 'role': row[3]} for row in rows]
            
            cursor.close()
            conn.close()
            
            return users
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения пользователей группы: {e}")
            try:
                conn.close()
            except:
                pass
            return []

# Глобальный экземпляр менеджера
user_chat_manager = UserChatManager()
