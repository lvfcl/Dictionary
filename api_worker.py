import requests
from bs4 import BeautifulSoup
import re

def is_russian(text: str) -> bool:
    """
    Определяет, написан ли текст на русском языке.
    Проверяет наличие хотя бы одного символа кириллицы.
    """
    return bool(re.search('[а-яА-ЯёЁ]', text))

def get_translation_mymemory(text: str, source_lang: str, target_lang: str) -> str:
    """
    Отправляет запрос к бесплатному API MyMemory для перевода слова.
    """
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source_lang}|{target_lang}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            translated_text = data["responseData"]["translatedText"]
            return translated_text.strip().lower()
    except Exception as e:
        print(f"Ошибка при запросе к MyMemory API: {e}")
    return ""

def fetch_transcription_from_wiktionary(fr_word: str) -> str:
    """
    Обновленный парсер французского Викисловаря.
    Ищет транскрипцию в тегах 'API' или выдергивает текст между косыми чертами \...\
    """
    word_url = fr_word.lower().strip()
    url = f"https://fr.wiktionary.org/wiki/{word_url}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            api_tags = soup.find_all(class_='API')
            for tag in api_tags:
                text = tag.text.strip()
                if text and ('\\' in text or '/' in text or len(text) > 0):
                    clean_text = text.replace('\\', '').replace('/', '')
                    return f"[{clean_text}]"
            
            page_text = soup.get_text()
            match = re.search(r'\\([^\\]+)\\', page_text)
            if match:
                return f"[{match.group(1).strip()}]"
                
    except Exception as e:
        print(f"Ошибка при парсинге транскрипции: {e}")
        
    return "[not found]"

def get_full_word_data(user_input: str):
    """
    Главная функция модуля. 
    Принимает ввод пользователя, определяет язык, делает запросы
    и возвращает кортеж: (французское_слово, транскрипция, русский_перевод)
    
    Если ничего не найдено, возвращает None.
    """
    clean_input = user_input.strip()
    if not clean_input:
        return None

    if is_russian(clean_input):
        ru_word = clean_input
        print(f"Обнаружен русский язык. Ищем перевод для: '{ru_word}'...")
        
        fr_word = get_translation_mymemory(ru_word, "ru", "fr")
        
        if not fr_word:
            return None
    else:
        fr_word = clean_input
        print(f"Обнаружен французский язык. Ищем перевод для: '{fr_word}'...")
        ru_word = get_translation_mymemory(fr_word, "fr", "ru")

    print(f"Запрашиваем транскрипцию для французского слова: '{fr_word}'...")
    transcription = fetch_transcription_from_wiktionary(fr_word)
    return fr_word.lower(), transcription, ru_word.lower()


# Блок для изолированного тестирования модуля
if __name__ == "__main__":
    print("--- Тестирование модуля api_worker.py ---")
    
    print("\nТест 1 (Ввод: 'chat'):")
    res1 = get_full_word_data("chat")
    print("Результат:", res1)
    
    print("\nТест 2 (Ввод: 'собака'):")
    res2 = get_full_word_data("собака")
    print("Результат:", res2)

    