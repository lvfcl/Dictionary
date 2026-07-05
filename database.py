import os
import json
from datetime import datetime, timedelta

DB_FILE = "dictionary.json"
FOLDERS_FILE = "folders.json"
SETTINGS_FILE = "settings.json"

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
            # Для слов, сохраненных до появления папок, гарантируем наличие ключа "folders"
            for word in words:
                word.setdefault("folders", [])
            return words
    except json.JSONDecodeError:
        print("Предупреждение: Файл базы данных поврежден или пуст. Возвращен пустой список.")
        return []
    except Exception as e:
        print(f"Не удалось прочитать базу данных: {e}")
        return []

def save_word(french: str, transcription: str, russian: str, examples: list = None, folders: list = None) -> bool:
    """
    Добавляет новое слово с базовыми параметрами интервального повторения.

    :param folders: список названий папок, в которые сразу нужно поместить слово
    """
    try:
        words = load_words()
        
        new_card = {
            "french": french.strip(),
            "transcription": transcription.strip(),
            "russian": russian.strip(),
            "examples": examples if examples else [],
            "folders": folders if folders else [],
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

def delete_word(french_word: str) -> bool:
    """
    Удаляет слово из JSON-базы по его французскому написанию.
    """
    try:
        words = load_words()
        filtered_words = [w for w in words if w.get("french", "").lower() != french_word.lower()]
        
        if len(words) == len(filtered_words):
            return False
            
        with open("dictionary.json", "w", encoding="utf-8") as f:
            json.dump(filtered_words, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка при удалении слова из базы: {e}")
        return False


# ------------------------- Работа с папками (категориями слов) -------------------------

def init_folders_database():
    """Создает файл со списком папок, если его еще нет."""
    if not os.path.exists(FOLDERS_FILE):
        try:
            with open(FOLDERS_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при создании файла папок: {e}")


def load_folders() -> list:
    """Возвращает список названий всех папок."""
    init_folders_database()
    try:
        with open(FOLDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []
    except Exception as e:
        print(f"Не удалось прочитать файл папок: {e}")
        return []


def _save_folders_list(folders: list) -> bool:
    try:
        with open(FOLDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(folders, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении списка папок: {e}")
        return False


def create_folder(name: str) -> bool:
    """Создает новую папку с указанным названием (без дублей)."""
    name = (name or "").strip()
    if not name:
        return False

    folders = load_folders()
    if any(f.lower() == name.lower() for f in folders):
        return False

    folders.append(name)
    return _save_folders_list(folders)


def delete_folder(name: str) -> bool:
    """Удаляет папку и убирает ссылку на нее у всех слов (сами слова не удаляются)."""
    folders = load_folders()
    filtered = [f for f in folders if f.lower() != name.lower()]

    if len(filtered) == len(folders):
        return False

    _save_folders_list(filtered)

    words = load_words()
    changed = False
    for word in words:
        if name in word.get("folders", []):
            word["folders"].remove(name)
            changed = True

    if changed:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(words, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при обновлении слов после удаления папки: {e}")

    return True


def add_word_to_folder(french_word: str, folder_name: str) -> bool:
    """Добавляет уже существующее слово словаря в указанную папку."""
    words = load_words()
    updated = False

    for word in words:
        if word.get("french", "").lower() == french_word.lower():
            if folder_name not in word.get("folders", []):
                word.setdefault("folders", []).append(folder_name)
                updated = True
            break

    if updated:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(words, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Ошибка при добавлении слова в папку: {e}")
            return False

    return updated


def remove_word_from_folder(french_word: str, folder_name: str) -> bool:
    """Убирает слово из указанной папки (само слово остается в словаре)."""
    words = load_words()
    updated = False

    for word in words:
        if word.get("french", "").lower() == french_word.lower():
            if folder_name in word.get("folders", []):
                word["folders"].remove(folder_name)
                updated = True
            break

    if updated:
        try:
            with open(DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(words, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Ошибка при удалении слова из папки: {e}")
            return False

    return updated


def get_words_by_folder(folder_name: str) -> list:
    """Возвращает список слов, находящихся в указанной папке."""
    words = load_words()
    return [w for w in words if folder_name in w.get("folders", [])]


def get_word_folders(french_word: str) -> list:
    """Возвращает список папок, в которых находится указанное слово."""
    words = load_words()
    for word in words:
        if word.get("french", "").lower() == french_word.lower():
            return word.get("folders", [])
    return []


# ------------------------- Настройки приложения (settings.json) -------------------------

def load_settings() -> dict:
    """Возвращает словарь пользовательских настроек (например, фоновый режим)."""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Не удалось прочитать файл настроек: {e}")
        return {}


def save_settings(settings: dict) -> bool:
    """Сохраняет словарь пользовательских настроек в settings.json."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")
        return False

