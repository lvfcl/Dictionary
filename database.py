import os
import json

# Константа — имя файла, где будут храниться наши слова
# Файл создастся в той же папке, где лежит сам скрипт
DB_FILE = "dictionary.json"

def init_database():
    """
    Инициализация базы данных.
    Проверяет, существует ли файл. Если нет — создает его с пустым списком [].
    """
    if not os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            print(f"База данных успешно создана: {DB_FILE}")
        except Exception as e:
            print(f"Ошибка при создании файла базы данных: {e}")

def load_words():
    """
    Загружает и возвращает список всех слов из файла JSON.
    Если файла нет, сначала инициализирует его.
    
    :return: list - список словарей, например: [{"french": "chat", "transcription": "[ʃa]", "russian": "кот"}]
    """
    init_database()  # На всякий случай проверяем, есть ли файл
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            words = json.load(f)
            return words
    except json.JSONDecodeError:
        # Если файл повредился или пуст (не содержит даже []), возвращаем пустой список
        print("Предупреждение: Файл базы данных поврежден или пуст. Возвращен пустой список.")
        return []
    except Exception as e:
        print(f"Не удалось прочитать базу данных: {e}")
        return []

def save_word(french: str, transcription: str, russian: str) -> bool:
    """
    Добавляет новое слово в базу данных JSON.
    
    :param french: Слово на французском языке
    :param transcription: Транскрипция слова
    :param russian: Перевод на русский язык
    :return: bool - True, если сохранение прошло успешно, иначе False
    """
    # 1. Загружаем уже существующие слова
    words = load_words()
    
    # 2. Проверяем дубликаты, чтобы не добавлять одно и то же слово дважды
    for word in words:
        if word['french'].lower() == french.lower():
            print(f"Слово '{french}' уже есть в словаре!")
            return False  # Сообщаем, что слово не добавлено (дубликат)

    # 3. Формируем структуру нового слова
    new_word = {
        "french": french.strip(),
        "transcription": transcription.strip(),
        "russian": russian.strip()
    }
    
    # 4. Добавляем новое слово в общий список
    words.append(new_word)
    
    # 5. Перезаписываем файл JSON с обновленным списком
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            # ensure_ascii=False нужно, чтобы русские и французские буквы (с акцентами вроде é, à)
            # записывались как нормальный текст, а не в виде кодов \u043a\u043e\u0442
            # indent=4 делает красивые отступы в файле для читаемости
            json.dump(words, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении слова в базу данных: {e}")
        return False


# Блок для ручного тестирования модуля (запустится только при прямом запуске этого файла)
if __name__ == "__main__":
    print("--- Тестирование модуля database.py ---")
    
    # Пробуем сохранить тестовое слово
    success = save_word("bonjour", "[bɔ̃ʒuʁ]", "здравствуйте")
    if success:
        print("Тестовое слово успешно сохранено!")
    else:
        print("Тестовое слово не сохранено (возможно, оно уже есть).")
        
    # Пробуем прочитать базу данных
    current_words = load_words()
    print(f"Сейчас в базе данных слов: {len(current_words)}")
    print("Содержимое базы:", current_words)

    