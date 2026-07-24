"""
Полностью офлайн-замена api_worker.py — кроме примеров употребления.

  1. Слово переводится локальной моделью (CTranslate2).
  2. Род и транскрипция берутся из локальной базы local_word_db.json
     (собранной заранее из дампа Wiktionary, шаги A и B) — это не требует сети.
  3. Примеры употребления генерирует внешняя LLM (Gemini через тот же
     OpenAI-совместимый прокси, что и в исходном api_worker.py) — модуль
     examples_llm.py. Это требует интернета в момент запроса.

Если интернета нет прямо сейчас (или LLM не смогла ответить) — поле examples
остаётся пустым, а флаг examples_pending говорит вызывающему коду "нужно
попробовать ещё раз позже, когда сеть появится" (см. sync_pending_examples
в database.py).
"""

import json
import re
import os

import ctranslate2
import transformers

from examples_llm import get_examples_for_word as _get_examples_for_word

_VOWEL_START = re.compile(r"^[aeiouyàâäéèêëîïôöùûüh]", re.IGNORECASE)

_DB_PATH = os.path.join(os.path.dirname(__file__), "local_word_db.json")
_MODEL_FR_RU = os.path.join(os.path.dirname(__file__), "model-fr-ru-ct2")
_MODEL_RU_FR = os.path.join(os.path.dirname(__file__), "model-ru-fr-ct2")

_word_db = None
_translator_fr_ru = None
_translator_ru_fr = None
_tokenizer_fr_ru = None
_tokenizer_ru_fr = None


def _lazy_init():
    """Модели и база грузятся один раз при первом использовании, а не при импорте."""
    global _word_db, _translator_fr_ru, _translator_ru_fr, _tokenizer_fr_ru, _tokenizer_ru_fr

    if _word_db is None:
        with open(_DB_PATH, encoding="utf-8") as f:
            _word_db = json.load(f)

    if _translator_fr_ru is None:
        _translator_fr_ru = ctranslate2.Translator(_MODEL_FR_RU)
        _tokenizer_fr_ru = transformers.AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-fr-ru")

    if _translator_ru_fr is None:
        _translator_ru_fr = ctranslate2.Translator(_MODEL_RU_FR)
        _tokenizer_ru_fr = transformers.AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ru-fr")


def is_russian(text: str) -> bool:
    return bool(re.search('[а-яА-ЯёЁ]', text))


def _translate(text: str, direction: str) -> str:
    if direction == "ru-fr":
        tokenizer, translator = _tokenizer_ru_fr, _translator_ru_fr
    else:
        tokenizer, translator = _tokenizer_fr_ru, _translator_fr_ru

    tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(text))
    result = translator.translate_batch([tokens])
    out_tokens = result[0].hypotheses[0]
    return tokenizer.convert_tokens_to_string(out_tokens).strip()


def _apply_article(bare_word: str, gender: str) -> str:
    bare_word = (bare_word or "").strip()
    if not bare_word or gender not in ("m", "f"):
        return bare_word
    if _VOWEL_START.match(bare_word):
        return f"l'{bare_word}"
    return f"{'le' if gender == 'm' else 'la'} {bare_word}"


def get_examples_for_word(french_bare: str, russian_word: str = ""):
    """
    Тонкая обёртка над examples_llm.get_examples_for_word — LLM сама
    возвращает готовые пары {"fr": ..., "ru": ...}, переводить их локальной
    моделью дополнительно не нужно (в отличие от старого варианта со
    скрапингом Wiktionary, где примеры были только на французском).

    Возвращает (examples, examples_pending) — см. examples_llm.py.
    """
    return _get_examples_for_word(french_bare, russian_word)


def get_full_word_data(user_input: str):
    """
    Возвращает: (french, transcription, russian, examples, examples_pending)

    ВНИМАНИЕ: сигнатура отличается от старой версии (было 4 значения) —
    добавился examples_pending. Не забудьте поправить код, который
    распаковывает результат этой функции (например, в main.py/ui_main.py).
    """
    _lazy_init()

    user_input = user_input.strip()
    if not user_input:
        return "", "", "", [], False

    if is_russian(user_input):
        russian = user_input.lower()
        french_bare = _translate(user_input, "ru-fr").lower()
    else:
        french_bare = user_input.lower()
        russian = _translate(user_input, "fr-ru").lower()

    entry = _word_db.get(french_bare)

    if entry:
        gender = entry.get("gender")
        transcription = f"[{entry['ipa']}]" if entry.get("ipa") else "[-]"
    else:
        # слова нет в локальной базе Wiktionary — не выдумываем род,
        # честно отдаём то, что реально знаем (перевод)
        gender = None
        transcription = "[-]"

    examples, examples_pending = get_examples_for_word(french_bare, russian)

    french = _apply_article(french_bare, gender) if gender else french_bare

    return french, transcription, russian, examples, examples_pending
