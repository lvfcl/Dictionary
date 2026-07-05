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


def suggest_matching_words(topic: str, candidates: list):
    """
    Просит нейросеть проанализировать СПИСОК СЛОВ, УЖЕ ЕСТЬ В СЛОВАРЕ пользователя,
    и отобрать среди них те, что подходят по смыслу к теме папки `topic`
    (например, "Еда", "Путешествия", "Эмоции"). Никакие новые слова не придумываются —
    только отбор из переданного списка.

    :param topic: название папки / тема, под которую нужно подобрать слова
    :param candidates: список словарей вида {"french": ..., "russian": ...} —
                       слова из словаря пользователя, которые еще не в этой папке
    :return: список французских слов (строки, ровно как в candidates), которые
             ИИ посчитал подходящими по теме, отсортированный по релевантности
    """
    topic = (topic or "").strip()
    candidates = candidates or []
    if not topic or not candidates:
        return []

    # Нумерованный список "французское слово - русский перевод" для промпта
    numbered_list = "\n".join(
        f"{i + 1}. {c.get('french', '')} — {c.get('russian', '')}"
        for i, c in enumerate(candidates)
    )

    system_prompt = (
        "Ты — профессиональный лингвист и словарь французского языка. "
        "Тебе дают тему (название папки) и пронумерованный список слов, которые уже есть "
        "в словаре пользователя. Твоя задача — проанализировать ТОЛЬКО ЭТИ слова и отобрать "
        "среди них те, что по смыслу относятся к заданной теме. "
        "ПРАВИЛА:\n"
        "1. Никогда не придумывай новые слова — используй строго слова из предоставленного списка, "
        "копируя французское написание слова точно как в списке (посимвольно).\n"
        "2. Отбирай только слова, которые ДЕЙСТВИТЕЛЬНО относятся к теме по смыслу, "
        "не притягивай слова искусственно.\n"
        "3. Если ни одно слово не подходит — верни пустой список.\n"
        "4. Отсортируй результат от наиболее подходящих к наименее подходящим.\n"
        "Ответ должен содержать ТОЛЬКО JSON без каких-либо вводных слов или разметки markdown."
    )

    user_prompt = (
        f"Тема папки: '{topic}'.\n"
        f"Список слов из словаря пользователя:\n{numbered_list}\n\n"
        "Отбери из этого списка французские слова, подходящие теме. "
        'Структура JSON строго такая: {"matches": ["слово1", "слово2", ...]}. '
        "В массив matches помещай ТОЛЬКО французские слова, скопированные из списка выше."
    )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)
        matches = data.get("matches", [])

        # Оставляем только те ответы ИИ, что реально совпадают со словами из списка кандидатов
        candidates_by_lower = {c.get("french", "").strip().lower(): c.get("french", "") for c in candidates}
        cleaned = []
        seen = set()
        for word in matches:
            key = (word or "").strip().lower()
            if key in candidates_by_lower and key not in seen:
                cleaned.append(candidates_by_lower[key])
                seen.add(key)

        return cleaned

    except Exception as e:
        print(f"Ошибка при подборе слов для папки '{topic}': {e}")
        return []


if __name__ == "__main__":
    print("--- Тестирование работы словаря через Нейросеть ---")
    res1 = get_full_word_data("стакан")
    print(f"Результат для 'стакан':\nСлово: {res1[0]}\nТранскрипция: {res1[1]}\nПеревод: {res1[2]}\nПримеры: {res1[3]}\n")
    
    res2 = get_full_word_data("яблоко")
    print(f"Результат для 'яблоко':\nСлово: {res2[0]}")