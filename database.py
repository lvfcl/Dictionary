import os
import json

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
    init_database()
    
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            words = json.load(f)
            return words
    except json.JSONDecodeError:
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
    words = load_words()
    
    for word in words:
        if word['french'].lower() == french.lower():
            print(f"Слово '{french}' уже есть в словаре!")
            return False

    new_word = {
        "french": french.strip(),
        "transcription": transcription.strip(),
        "russian": russian.strip()
    }
    
    words.append(new_word)
    
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(words, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении слова в базу данных: {e}")
        return False


if __name__ == "__main__":
    print("--- Тестирование модуля database.py ---")
    
    success = save_word("bonjour", "[bɔ̃ʒuʁ]", "здравствуйте")
    if success:
        print("Тестовое слово успешно сохранено!")
    else:
        print("Тестовое слово не сохранено (возможно, оно уже есть).")
        
    current_words = load_words()
    print(f"Сейчас в базе данных слов: {len(current_words)}")
    print("Содержимое базы:", current_words)

    