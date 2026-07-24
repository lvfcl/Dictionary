"""
Генерация примеров употребления слова через LLM (например, Gemini через тот
же OpenAI-совместимый прокси, что использовался в исходном api_worker.py).

Раздел труда:
  - перевод слова, род, транскрипция — локальная модель + локальная база
    (offline_word_lookup.py), работает всегда, без сети
  - примеры употребления — генерирует внешняя нейросеть (этот модуль),
    работает только при наличии интернета

Логика (по требованию): сначала быстро проверяем, есть ли вообще интернет
(не дожидаясь таймаута самого API-запроса), и только потом обращаемся к LLM.
Если сети нет ИЛИ LLM не вернула примеры — сообщаем "не готово, попробовать
позже" (examples_pending=True), не выдумывая ничего взамен.
"""

import json
import socket

from openai import OpenAI
from config import key, url

client = OpenAI(base_url=url, api_key=key)

MAX_EXAMPLES = 2


def check_internet_connection(timeout: float = 2.0) -> bool:
    """
    Быстрая проверка интернета без обращения к самому LLM-провайдеру —
    пробуем открыть TCP-соединение до публичного DNS-сервера Google (8.8.8.8:53).
    Не идеально (в некоторых сетях 53-й порт может быть закрыт при работающем
    интернете), но для большинства обычных сетей — быстрый и надёжный способ,
    который не ждёт долгого таймаута HTTPS-запроса к API.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False


def generate_examples_llm(french_word: str, russian_word: str = ""):
    """
    Просит LLM сгенерировать короткие примеры употребления французского слова
    вместе с переводом на русский.

    Возвращает список [{"fr": "...", "ru": "..."}] или [] при любой ошибке
    (сеть пропала между проверкой и запросом, провайдер недоступен,
    некорректный ответ и т.п.) — пустой список означает "не получилось",
    а не "примеров не существует".
    """
    french_word = (french_word or "").strip()
    if not french_word:
        return []

    system_prompt = (
        "Ты — профессиональный лингвист и словарь французского языка. "
        "Твоя задача — сгенерировать короткие, естественные примеры "
        "употребления заданного французского слова в живой речи, каждый "
        "не длиннее одного простого предложения. "
        "Ответ должен содержать ТОЛЬКО JSON без вводных слов и разметки markdown."
    )

    user_prompt = (
        f"Слово: '{french_word}' (перевод на русский: '{russian_word}'). "
        f"Сгенерируй ровно {MAX_EXAMPLES} коротких примера предложений во "
        "французском языке с этим словом и их точный перевод на русский. "
        'Структура JSON строго такая: {"examples": [{"fr": "...", "ru": "..."}, ...]}'
    )

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        examples = data.get("examples", [])

        cleaned = []
        for ex in examples[:MAX_EXAMPLES]:
            fr = (ex.get("fr") or "").strip()
            ru = (ex.get("ru") or "").strip()
            if fr and ru:
                cleaned.append({"fr": fr, "ru": ru})

        return cleaned

    except Exception as e:
        print(f"Ошибка при генерации примеров для '{french_word}': {e}")
        return []


def get_examples_for_word(french_bare: str, russian_word: str = ""):
    """
    Возвращает (examples, examples_pending) — в том же формате, что ждёт
    offline_word_lookup.py / database.sync_pending_examples.
    """
    if not check_internet_connection():
        return [], True

    examples = generate_examples_llm(french_bare, russian_word)

    if not examples:
        # либо LLM ничего не вернула, либо сеть пропала между проверкой
        # и самим запросом — в обоих случаях просто пробуем позже
        return [], True

    return examples, False
