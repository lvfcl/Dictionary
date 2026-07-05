import os
import re
from gtts import gTTS

AUDIO_DIR = "audio_cache"


def _get_safe_filename(word: str) -> str:
    """Создает безопасное имя файла на основе слова (без спецсимволов)."""
    safe = re.sub(r'[^\w\s-]', '', word.strip().lower())
    safe = re.sub(r'\s+', '_', safe)
    return safe or "word"


def ensure_audio_dir():
    """Создает папку для хранения аудиофайлов, если её еще нет."""
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)


def get_audio_path(word: str) -> str:
    """
    Возвращает путь к mp3-файлу с произношением слова на французском.
    Если файл еще не создавался — генерирует его через gTTS и кэширует
    на диске, чтобы не обращаться к сети повторно для уже известных слов.

    :param word: французское слово (можно с артиклем, например "le chat")
    :return: путь к файлу или пустая строка, если генерация не удалась
    """
    word = (word or "").strip()
    if not word:
        return ""

    ensure_audio_dir()
    filename = _get_safe_filename(word)
    filepath = os.path.join(AUDIO_DIR, f"{filename}.mp3")

    if not os.path.exists(filepath):
        try:
            tts = gTTS(text=word, lang='fr')
            tts.save(filepath)
        except Exception as e:
            print(f"Ошибка при генерации аудио для '{word}': {e}")
            return ""

    return filepath


def delete_audio(word: str):
    """Удаляет закэшированный аудиофайл слова (например, при удалении слова из словаря)."""
    filename = _get_safe_filename(word)
    filepath = os.path.join(AUDIO_DIR, f"{filename}.mp3")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Не удалось удалить аудиофайл '{filepath}': {e}")

