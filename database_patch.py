"""
ЭТО ПАТЧ, А НЕ ПОЛНЫЙ ФАЙЛ.

Ниже — только новые/изменённые части, которые нужно перенести в ваш
существующий database.py. Показываю их отдельно, а не пересоздаю весь файл
целиком, чтобы не потерять то, что вы могли поменять сами.
"""

# =====================================================================
# 1. В функции load_words() — рядом с существующей строкой
#        word.setdefault("folders", [])
#    добавить:

        word.setdefault("examples_pending", False)


# =====================================================================
# 2. В функции save_word() — добавить новый параметр и поле в new_card:

def save_word(french: str, transcription: str, russian: str, examples: list = None,
              folders: list = None, examples_pending: bool = False) -> bool:
    """
    (сигнатура дополнена параметром examples_pending)
    examples_pending=True значит "интернета не было в момент поиска, примеры
    нужно дозаполнить позже" — их заполнит sync_pending_examples().
    """
    try:
        words = load_words()

        new_card = {
            "french": french.strip(),
            "transcription": transcription.strip(),
            "russian": russian.strip(),
            "examples": examples if examples else [],
            "examples_pending": examples_pending,
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


# =====================================================================
# 3. Новые функции — добавить в конец файла (после update_card_review
#    или в любом удобном месте):

def get_words_with_pending_examples() -> list:
    """Возвращает слова, у которых ещё не найдены примеры (сохранялись без сети)."""
    words = load_words()
    return [w for w in words if w.get("examples_pending")]


def update_word_examples(french_word: str, examples: list) -> bool:
    """Записывает найденные примеры для слова и снимает флаг ожидания."""
    words = load_words()
    updated = False

    for word in words:
        if word.get("french", "").lower() == french_word.lower():
            word["examples"] = examples
            word["examples_pending"] = False
            updated = True
            break

    if updated:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(words, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Ошибка при обновлении примеров для '{french_word}': {e}")
            return False

    return False


def sync_pending_examples(fetch_examples_fn) -> int:
    """
    Проходит по всем словам с examples_pending=True и пытается дозаполнить
    примеры. Вызывать при старте приложения и/или по таймеру, когда есть сеть.

    :param fetch_examples_fn: функция вида (french_bare: str) -> (examples, still_pending),
        например offline_word_lookup.get_examples_for_word — передаётся снаружи,
        чтобы database.py не тянул за собой модели/сеть как жёсткую зависимость.
    :return: сколько слов удалось успешно дозаполнить
    """
    pending = get_words_with_pending_examples()
    filled_count = 0

    for word in pending:
        # для "чистого" (без артикля) слова прогоняем через тот же экстрактор,
        # что и при первом поиске
        bare_word = word["french"].split(" ", 1)[-1].lstrip("'")  # грубо убираем le/la/l'
        examples, still_pending = fetch_examples_fn(bare_word)

        if not still_pending:
            update_word_examples(word["french"], examples)
            if examples:
                filled_count += 1

    return filled_count
