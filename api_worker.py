import re
import json
from openai import OpenAI
from config import key, url

client = OpenAI(
    base_url=url,
    api_key=key
)

# Слова, начинающиеся с этих букв, требуют артикль l' (элизия перед гласной/немой h).
# Это не работает для "h придыхательного" (le héros, la hache и т.п.) — точный список
# таких слов не определить регулярным выражением, для них нужен словарь исключений.
_VOWEL_START = re.compile(r"^[aeiouyàâäéèêëîïôöùûüh]", re.IGNORECASE)


def is_russian(text: str) -> bool:
    """ Определяет, написан ли текст на русском языке. """
    return bool(re.search('[а-яА-ЯёЁ]', text))


def _apply_article(bare_word: str, gender: str) -> str:
    """
    Механически строит французское существительное с правильным артиклем
    на основе рода, который отдельно назвала нейросеть. Артикль здесь
    подставляется кодом, а не нейросетью — это исключает ошибки вида
    "род определен верно, но артикль подставлен не тот" или лишние пробелы/опечатки.

    :param bare_word: слово без артикля, например "pomme"
    :param gender: "m", "f" или "none" (для не-существительных: глаголов, прилагательных и т.д.)
    """
    bare_word = (bare_word or "").strip()
    if not bare_word:
        return bare_word

    gender = (gender or "").strip().lower()
    if gender not in ("m", "f"):
        return bare_word

    if _VOWEL_START.match(bare_word):
        return f"l'{bare_word}"
    return f"{'le' if gender == 'm' else 'la'} {bare_word}"


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
        "1. Если французское слово является существительным, ты ОБЯЗАН сначала определить "
        "его грамматический род и кратко обосновать его (например, по типичному окончанию "
        "или по известному тебе словарному факту), и только потом указать род в поле \"gender\": "
        "\"m\" для мужского рода, \"f\" для женского. Если слово не существительное "
        "(глагол, прилагательное, наречие и т.д.) — укажи \"none\". "
        "В поле \"word\" укажи само слово БЕЗ артикля.\n"
        "2. Не путай схожие по звучанию или по смыслу слова разного рода — "
        "если сомневаешься между двумя вариантами, выбирай наиболее употребительный "
        "и общеизвестный род этого слова во французском языке.\n"
        "3. Укажи правильную транскрипцию слова в квадратных скобках или между косыми чертами.\n"
        "4. Дай полный перевод (если значений несколько, перечисли их через запятую).\n"
        "5. Сгенерируй ровно 2 живых примера предложений во французском языке с этим словом и их точный перевод на русский.\n"
        "Ответ должен содержать ТОЛЬКО JSON без каких-либо вводных слов или разметки markdown."
    )

    user_prompt = (
        f"Переведи слово '{user_input}' {direction}. Структура JSON должна быть: "
        '{"word": "...", "gender_reasoning": "...", "gender": "m|f|none", '
        '"transcription": "...", "russian": "...", '
        '"examples": [{"fr": "...", "ru": "..."}, {"fr": "...", "ru": "..."}]}'
    )

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)

        bare_word = data.get("word", "").strip().lower()
        gender = data.get("gender", "none")
        french = _apply_article(bare_word, gender)
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
