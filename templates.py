import json
import os
from database import load_templates, save_templates
from datetime import datetime

# For backward compatibility, we'll keep the TEMPLATES dict
# but now it will be loaded from JSON

def get_templates():
    """Get templates from JSON storage"""
    templates_data = load_templates()
    return templates_data.get("templates", {})

def save_template(template_id, template_data):
    """Save template to JSON storage"""
    templates_data = load_templates()
    templates_data["templates"][template_id] = template_data
    return save_templates(templates_data)

def delete_template(template_id):
    """Delete template from JSON storage"""
    templates_data = load_templates()
    if template_id in templates_data["templates"]:
        # Remove associated image if exists
        template = templates_data["templates"][template_id]
        if "image" in template and os.path.exists(template["image"]):
            try:
                os.remove(template["image"])
            except Exception as e:
                print(f"Error removing template image: {e}")
        
        del templates_data["templates"][template_id]
        return save_templates(templates_data)
    return False

# Initialize with default templates if empty
def init_default_templates():
    templates_data = load_templates()
    if not templates_data.get("templates"):
        default_templates = {
            # Hongqi шаблоны
            "hongqi_template1": {
                "name": "Дистанционный осмотр H5",
                "text": """Добрый день! 
ЗАВТРА УТРОМ (до 12:00)
Прошу скинуть фотографии:
▫️уровня антифриза
▫️тормозной жидкости
▫️масла на щупе
▫️панели приборов с пробегом
▫️панель приборов с давлением шин
▫️глубину протектора шин (4 колеса с торца) 
▫️4 фото авто (со всех сторон) 

Масло проверяем на холодную. Либо паркуемся где нибудь на обед, глушим машину, и минут через десять замеряем за заглушенную""",
                'image': 'images/hongqi_inspection.jpg',
                'group': 'Hongqi 476 group',
                'subgroup': 'Осмотры'
            },

            "hongqi_template2": {
                "name": "Напоминание об осмотре",
                "text": "Напоминаю о проведении дистанционного осмотра, инструкция выше",
                'image': 'images/hongqi_reminder.jpg',
                'group': 'Hongqi 476 group',
                'subgroup': 'Осмотры'
            },

            # TurboMatiz шаблоны
            "turbomatiz_template1": {
                "name": "Оплата аренды",
                "text": """Добрый день, господа!

Сегодня воскресенье, а это значит что завтра (в понедельник) в 12:00 необходимо оплатить аренду согласно тарифам.
Реквизиты: +7 921 572 11 40 Мамурджонов Аминджон Мамурджонович, Альфа банк

Так же с 9:00 до 12:00 понедельника прошу скинуть фотографии с одометров с вашим текущим пробегом и квитанцию/скриншот оплаты накопившихся штрафов в рабочую группу телеграмм

Просим действовать своевременно для более комфортного сотрудничества.""",
                'image': 'images/turbomatiz_payment.jpg',
                'group': 'Matiz 476 group',
                'subgroup': 'Платежи'
            },

            "turbomatiz_template2": {
                "name": "Осмотр автомобилей",
                "text": """Добрый день, господа!

Завтра до 23:59 прошу вас произвести осмотр ваших автомобилей.

Прошу скинуть фотографии уровня антифриза, тормозной жидкости, масла и панели приборов!!!

Масло проверяем на холодную, до первого запуска двигателя за день.

Инструкция: 
1. Вытащить щуп
2. Протереть его (тканью которая не оставляет ворс!!!)
3. Вставить щуп обратно до упора
4. Вытащить его и сделать фото уровня (должно быть в норме)

Фото-отчет отправлять в рабочую телеграмм-группу

Фото-осмотр производим каждую среду и субботу!!!""",
                 'image': 'images/turbomatiz_inspection.jpg',
                 'group': 'Matiz 476 group',
                 'subgroup': 'Осмотры'
            },

            "turbomatiz_template3": {
                "name": "Чистка автомобиля",
                "text": """Добрый день, господа!

Если в течении последних 4 дней вы еще не скинули фото чистого автомобиля, тогда прошу вас сегодня или завтра заехать на авто-мойку, помыть автомобиль на котором вы работаете и скинуть фотографии чистого автомобиля до 00:00 часов завтрашнего дня в рабочую телеграмм-группу

Формат фотографии 1 фото : автомобиль спереди + слева 
2 фото : автомобиль сзади + справа 
3 и 4 фото : коврики в салоне 

Данное мероприятие будет проводиться раз в 2 недели в целях вашей комфортной работы на чистом автомобиле и сохранении ЛКП в должном состоянии.

Мойка автомобиля производится за счет водителя, согласно договору. Можно использовать мойку самообслуживания.
Водители которые работают на брендированных автомобилях получают компенсацию моек в размере 2200₽/месяц""",
                'image': 'images/turbomatiz_clean.jpg',
                'group': 'Matiz 476 group',
                'subgroup': 'Чистка'
            }
        }
        
        templates_data["templates"] = default_templates
        save_templates(templates_data)

# Initialize default templates on import
init_default_templates()

# For backward compatibility
TEMPLATES = get_templates()
