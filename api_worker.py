import requests 
from bs4 import BeautifulSoup 
import re 

def is_russian(text: str) -> bool:
    """ Определяет, написан ли текст на русском языке. """
    return bool(re.search('[а-яА-ЯёЁ]', text))

def get_translation_mymemory(text: str, source_lang: str, target_lang: str) -> str:
    """ Отправляет запрос к бесплатному API MyMemory для перевода слова. """
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
    """ Ищет транскрипцию во французском Викисловаре. """
    word_url = fr_word.lower().strip() 
    url = f"https://fr.wiktionary.org/wiki/{word_url}" 
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' 
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Ищем стандартный тег транскрипции во французском Викисловаре
            span = soup.find("span", class_="API")
            if span:
                return span.text.strip()
            
            # Альтернативный поиск по тексту между косыми чертами
            text = soup.get_text()
            match = re.search(r'/([^/\s]+)/', text)
            if match:
                return f"[{match.group(1)}]"
    except Exception as e:
        print(f"Ошибка парсинга Викисловаря: {e}")
    return "[-]"

def fetch_context_examples(word: str, src_lang: str = "fr", tgt_lang: str = "ru") -> list:
    """
    Парсит сайт Reverso Context для получения примеров предложений.
    Возвращает список словарей: [{'fr': '...', 'ru': '...'}, ...]
    """
    word_url = word.lower().strip()
    url = f"https://context.reverso.net/translation/french-russian/{word_url}"
    
    # Reverso Context блокирует запросы без валидного User-Agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    examples = []
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим блоки с примерами предложений
            src_sentences = soup.find_all('div', class_='src')
            trg_sentences = soup.find_all('div', class_='trg')
            
            # Берём максимум 2-3 примера, как заказывали
            for src, trg in zip(src_sentences[:2], trg_sentences[:2]):
                # Очищаем текст от лишних пробелов и переносов строк
                fr_text = src.get_text().strip()
                ru_text = trg.get_text().strip()
                
                if fr_text and ru_text:
                    examples.append({
                        "fr": fr_text,
                        "ru": ru_text
                    })
    except Exception as e:
        print(f"Ошибка при парсинге Reverso Context: {e}")
        
    return examples

def get_full_word_data(user_input: str):
    """
    Главная функция модуля. Принимает ввод пользователя, определяет язык,
    делает запросы и возвращает кортеж:
    (французское_слово, транскрипция, русский_перевод, список_примеров)
    """
    user_input = user_input.strip()
    if not user_input:
        return "", "", "", []

    if is_russian(user_input):
        # Если ввели на русском — ищем французское слово
        russian = user_input
        french = get_translation_mymemory(russian, "ru", "fr")
        transcription = fetch_transcription_from_wiktionary(french) if french else "[-]"
    else:
        # Если ввели на французском — ищем русский перевод
        french = user_input
        russian = get_translation_mymemory(french, "fr", "ru")
        transcription = fetch_transcription_from_wiktionary(french)

    # Тянем контекст (предложения) для французского слова
    examples = []
    if french:
        examples = fetch_context_examples(french)

    return french, transcription, russian, examples

# Блок для изолированного тестирования модуля
if __name__ == "__main__":
    print("--- Тестирование модуля api_worker.py ---")
    word = "chat"
    print(f"Тестируем слово: {word}")
    res = get_full_word_data(word)
    print("Результат:")
    print(f"Фр: {res[0]}")
    print(f"Транскрипция: {res[1]}")
    print(f"Рус: {res[2]}")
    print(f"Примеры: {res[3]}")