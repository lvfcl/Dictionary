import os
import json
from datetime import datetime, timedelta

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

def save_word(french: str, transcription: str, russian: str, examples: list = None) -> bool:
    """
    Добавляет новое слово с базовыми параметрами интервального повторения.
    """
    try:
        words = load_words()
        
        new_card = {
            "french": french.strip(),
            "transcription": transcription.strip(),
            "russian": russian.strip(),
            "examples": examples if examples else [],
            "interval": 1,
            "ease_factor": 2.5,
            "repetitions": 0,
            "next_review": datetime.now().strftime("%Y-%m-%d")
        }
        
        for word in words:
            if word["french"].lower() == new_card["french"].lower():
                print(f"Слово '{french}' уже есть в словаре.")
                return False
                
        words.append(new_card)
        
        with open("dictionary.json", "w", encoding="utf-8") as f:
            json.dump(words, f, ensure_ascii=False, indent=4)
        return True
        
    except Exception as e:
        print(f"Ошибка при сохранении слова: {e}")
        return False

def update_card_review(word_data: dict, quality: int) -> dict:
    """
    Рассчитывает дату следующего повторения по алгоритму SM-2.
    
    quality: 
        0 - "Забыл" (сброс)
        1 - "Сложно"
        2 - "Хорошо"
        3 - "Легко"
    """
    if quality == 0:
        word_data["repetitions"] = 0
        word_data["interval"] = 1 
        word_data["ease_factor"] = max(1.3, word_data["ease_factor"] - 0.2)
    
    else:
        if word_data["repetitions"] == 0:
            word_data["interval"] = 1
        elif word_data["repetitions"] == 1:
            word_data["interval"] = 3
        else:
            word_data["interval"] = int(word_data["interval"] * word_data["ease_factor"])
        
        word_data["repetitions"] += 1
        
        word_data["ease_factor"] += (0.1 - (3 - quality) * (0.08 + (3 - quality) * 0.02))
        
        if word_data["ease_factor"] < 1.3:
            word_data["ease_factor"] = 1.3

    next_date = datetime.now() + timedelta(days=word_data["interval"])
    word_data["next_review"] = next_date.strftime("%Y-%m-%d")
    
    return word_data


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

    