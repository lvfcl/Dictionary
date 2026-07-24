"""
Живой (онлайн) поиск примеров употребления слова на fr.wiktionary.org.

В отличие от local_word_db.json (собранного заранее из дампа), здесь мы
обращаемся к сайту Викисловаря напрямую по одному слову за раз — то есть
эта функция работает, только когда есть интернет.

Если сети нет (или сайт не отвечает, или слова там нет) — функция должна
НЕ бросать исключение наружу, а вернуть None. Это специально отличается от
"нашли слово, но примеров нет" (пустой список []) — вызывающий код должен
уметь отличить "поискали и не нашли" от "не смогли поискать вообще".
"""

import re
import requests

WIKTIONARY_API = "https://fr.wiktionary.org/w/api.php"
REQUEST_TIMEOUT = 4  # секунды — если сайт не отвечает быстро, не блокируем UI надолго

# Wikimedia (в том числе Wiktionary) по правилам API этикета требует
# осмысленный User-Agent и может блокировать/резать запросы с дефолтным
# User-Agent библиотеки requests. См. https://meta.wikimedia.org/wiki/User-Agent_policy
_HEADERS = {
    "User-Agent": "FrenchDictionaryApp/1.0 (personal non-commercial dictionary app; contact: your-email@example.com)"
}

MAX_EXAMPLES = 2
MAX_EXAMPLE_CHARS = 160

# французские примеры в вики-разметке обычно оформлены как под-пункт "#*"
# с текстом в двойных апострофах: #* ''Une phrase d'exemple.''
_EXAMPLE_LINE_RE = re.compile(r"^#\*\s*''(.+?)''", re.MULTILINE)
_WIKILINK_RE = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")  # [[mot|texte]] -> texte
_TEMPLATE_RE = re.compile(r"\{\{[^}]*\}\}")  # убираем служебные шаблоны типа {{source|...}}


def _clean_wikitext(text: str) -> str:
    text = _WIKILINK_RE.sub(r"\1", text)
    text = _TEMPLATE_RE.sub("", text)
    return text.strip()


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return parts[0].strip() if parts else text.strip()


def fetch_examples_online(word: str):
    """
    Возвращает список примеров вида [{"fr": "..."}] или None, если поиск
    не удался технически (нет сети, таймаут, сайт недоступен).
    Пустой список [] означает "спросили сайт, слова/примеров там нет".
    """
    word = (word or "").strip()
    if not word:
        return []

    params = {
        "action": "parse",
        "page": word,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }

    try:
        response = requests.get(WIKTIONARY_API, params=params, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        # нет интернета, таймаут, DNS не резолвится и т.п. — сообщаем вызывающему
        # коду, что нужно попробовать позже, а не что "примеров нет"
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if "error" in data:
        # страницы для этого слова во французском Викисловаре просто нет
        return []

    wikitext = data.get("parse", {}).get("wikitext", "")
    if not wikitext:
        return []

    candidates = []
    for match in _EXAMPLE_LINE_RE.finditer(wikitext):
        raw = _clean_wikitext(match.group(1))
        sentence = _first_sentence(raw)
        if sentence and len(sentence) <= MAX_EXAMPLE_CHARS:
            candidates.append(sentence)
        if len(candidates) >= MAX_EXAMPLES:
            break

    return [{"fr": s} for s in candidates]
