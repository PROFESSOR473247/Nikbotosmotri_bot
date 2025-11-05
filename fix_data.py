import json
import os

def fix_users_data():
    """Исправляет структуру данных пользователей"""
    try:
        if os.path.exists('authorized_users.json'):
            with open('authorized_users.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем и конвертируем старый формат
            if 'users' in data and data['users']:
                first_user = next(iter(data['users'].values()))
                if isinstance(first_user, str):
                    print("🔄 Конвертируем старый формат пользователей в новый...")
                    
                    new_users = {}
                    for user_id, username in data['users'].items():
                        new_users[user_id] = {
                            "name": username,
                            "groups": ["hongqi", "turbomatiz"]
                        }
                    
                    data['users'] = new_users
                    
                    with open('authorized_users.json', 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    
                    print("✅ Структура пользователей обновлена!")
                    return True
            
            print("✅ Структура пользователей уже в новом формате")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка при обновлении структуры: {e}")
        return False

def init_required_files():
    """Инициализирует необходимые файлы"""
    required_files = ['template_groups.json', 'templates_data.json']
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"📁 Создаем файл: {file}")
            
            if file == 'template_groups.json':
                default_data = {
                    "groups": {
                        "hongqi": {
                            "name": "🚗 Hongqi",
                            "subgroups": {
                                "inspection": "🔍 Осмотры",
                                "reminders": "⏰ Напоминания"
                            },
                            "allowed_users": ["812934047"]
                        },
                        "turbomatiz": {
                            "name": "🚙 TurboMatiz",
                            "subgroups": {
                                "payments": "💳 Оплаты", 
                                "inspections": "🔍 Осмотры",
                                "cleaning": "🧼 Чистка"
                            },
                            "allowed_users": ["812934047"]
                        }
                    }
                }
            elif file == 'templates_data.json':
                default_data = {"templates": {}}
            
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)
            
            print(f"✅ Файл {file} создан")

if __name__ == '__main__':
    print("🛠️ Исправление структуры данных...")
    fix_users_data()
    init_required_files()
    print("🎉 Все файлы готовы к работе!")
