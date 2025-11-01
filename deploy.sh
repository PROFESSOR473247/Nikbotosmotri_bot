#!/bin/bash

echo "=== Starting deployment process ==="

# Исправляем отступы в Python файлах
echo "Fixing indentation in Python files..."
find . -name "*.py" -exec python -c "
import re
import sys

for filename in sys.argv[1:]:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Заменяем табы на 4 пробела
        content = content.replace('\t', '    ')
        
        # Удаляем лишние пробелы в конце строк
        content = re.sub(r' +$', '', content, flags=re.MULTILINE)
        
        # Удаляем специальные невидимые символы
        content = content.replace('\u00a0', ' ')  # non-breaking space
        content = content.replace('\ufeff', '')   # BOM
        
        # Записываем обратно
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'Fixed: {filename}')
    except Exception as e:
        print(f'Error fixing {filename}: {e}')
" {} \;

echo "=== Starting bot ==="
python bot.py
