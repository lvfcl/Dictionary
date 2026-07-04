import os
import re
import json
from openai import OpenAI
from config import key, url

client = OpenAI(
    base_url=url,
    api_key=key
)

def is_russian(text: str) -> bool:
    """ Определяет, написан ли текст на русском языке. """
    return bool(re.search('[а-яА-ЯёЁ]', text))

def get_full_word_data(user_input: str):
    """
    Отправляет запрос к нейросети и получает структурированные данные о слове:
    французское слово (с артиклем), транскрипцию, русский перевод и контекстные примеры.
    """
    user_input = user_input.strip()
    if not user_input:
        return "", "", "", []

    direction = "с русского на французский" if is_russian(user_input) else "с французского на русский"

    system_prompt = (
        "Ты — профессиональный лингвист и словарь французского языка. "
        "Твоя задача — переводить слова и предоставлять информацию строго в формате JSON. "
        "ПРАВИЛА:\n"
        "1. Если слово во французском языке является существительным, ты ОБЯЗАН добавить к нему "
        "соответствующий определенный артикль (le, la или l' для слов на гласную/немую h). "
        "Например: 'яблоко' -> 'la pomme', 'arbre' -> 'l\'arbre', 'стакан' -> 'le verre'.\n"
        "2. Укажи правильную транскрипцию слова в квадратных скобках или между косыми чертами.\n"
        "3. Дай полный перевод (если значений несколько, перечисли их через запятую).\n"
        "4. Сгенерируй ровно 2 живых примера предложений во французском языке с этим словом и их точный перевод на русский.\n"
        "Ответ должен содержать ТОЛЬКО JSON без каких-либо вводных слов или разметки markdown."
    )

    user_prompt = f"Переведи слово '{user_input}' {direction}. Структура JSON должна быть: {{\"french\": \"...\", \"transcription\": \"...\", \"russian\": \"...\", \"examples\": [{{\"fr\": \"...\", \"ru\": \"...\"}}, {{\"fr\": \"...\", \"ru\": \"...\"}}]}}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        
        french = data.get("french", "").strip().lower()
        transcription = data.get("transcription", "[-]").strip()
        russian = data.get("russian", "").strip().lower()
        examples = data.get("examples", [])
        
        return french, transcription, russian, examples

    except Exception as e:
        print(f"Ошибка при запросе к нейросети: {e}")
        return user_input, "[-]", "ошибка перевода", []


if __name__ == "__main__":
    print("--- Тестирование работы словаря через Нейросеть ---")
    res1 = get_full_word_data("стакан")
    print(f"Результат для 'стакан':\nСлово: {res1[0]}\nТранскрипция: {res1[1]}\nПеревод: {res1[2]}\nПримеры: {res1[3]}\n")
    
    res2 = get_full_word_data("яблоко")
    print(f"Результат для 'яблоко':\nСлово: {res2[0]}")