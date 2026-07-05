"""
Модуль системной интеграции для Windows:
1. Автозапуск программы при включении ПК (через ветку реестра Run).
2. Глобальная горячая клавиша, которая позволяет добавить в словарь слово,
   выделенное в ЛЮБОМ приложении Windows (браузер, Word, блокнот и т.д.),
   без открытия окна программы.

Технический нюанс: у сторонних приложений нет способа встроить свой пункт
в системное контекстное меню (ПКМ) чужой программы — это ограничение
самой Windows. Поэтому используется тот же подход, что и в популярных
переводчиках: глобальная горячая клавиша имитирует Ctrl+C для копирования
выделенного текста, читает буфер обмена и показывает всплывающее окно
с предложением добавить слово.
"""

import sys
import os
import time

APP_NAME = "FrenchDictionaryApp"
DEFAULT_HOTKEY = "ctrl+alt+d"

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False

try:
    import keyboard
    _KEYBOARD_AVAILABLE = True
except ImportError:
    _KEYBOARD_AVAILABLE = False

try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except ImportError:
    _PYPERCLIP_AVAILABLE = False

from PyQt6.QtCore import QObject, pyqtSignal


# ------------------------- Автозапуск при включении ПК -------------------------

def _get_run_registry_path():
    return winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_startup_command() -> str:
    """
    Формирует команду для запуска программы из автозагрузки.
    Если программа собрана в .exe (например, через PyInstaller) — используется путь к .exe.
    Если запущена из исходников — используется pythonw.exe (без консольного окна) + путь к скрипту.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    python_dir = os.path.dirname(sys.executable)
    pythonw_path = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable

    script_path = os.path.abspath(sys.argv[0])
    return f'"{pythonw_path}" "{script_path}"'


def is_autostart_supported() -> bool:
    """Автозапуск через реестр поддерживается только в Windows."""
    return sys.platform == "win32" and _WINREG_AVAILABLE


def is_autostart_enabled() -> bool:
    """Проверяет, стоит ли программа сейчас в автозагрузке Windows."""
    if not is_autostart_supported():
        return False
    try:
        hive, path = _get_run_registry_path()
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False
    except Exception as e:
        print(f"Ошибка при проверке автозапуска: {e}")
        return False


def enable_autostart() -> bool:
    """Включает автозапуск программы при включении Windows."""
    if not is_autostart_supported():
        return False
    try:
        hive, path = _get_run_registry_path()
        command = _get_startup_command()
        with winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        return True
    except Exception as e:
        print(f"Ошибка при включении автозапуска: {e}")
        return False


def disable_autostart() -> bool:
    """Отключает автозапуск программы."""
    if not is_autostart_supported():
        return False
    try:
        hive, path = _get_run_registry_path()
        with winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, APP_NAME)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        print(f"Ошибка при отключении автозапуска: {e}")
        return False


# ------------------------- Глобальная горячая клавиша -------------------------

def is_global_hotkey_supported() -> bool:
    """Захват текста из любого приложения работает только на Windows и требует библиотеки keyboard/pyperclip."""
    return sys.platform == "win32" and _KEYBOARD_AVAILABLE and _PYPERCLIP_AVAILABLE


def get_missing_dependencies() -> list:
    """Возвращает названия пакетов, которые нужно установить для работы глобальной горячей клавиши."""
    missing = []
    if not _KEYBOARD_AVAILABLE:
        missing.append("keyboard")
    if not _PYPERCLIP_AVAILABLE:
        missing.append("pyperclip")
    return missing


class GlobalWordCapture(QObject):
    """
    Слушает системную горячую клавишу (по умолчанию Ctrl+Alt+D). При нажатии:
    1. Запоминает текущее содержимое буфера обмена.
    2. Имитирует Ctrl+C, чтобы скопировать то, что пользователь выделил в активном окне.
    3. Если буфер обмена изменился — считает это выделенным словом и испускает сигнал
       word_captured с этим текстом (сигнал безопасно приходит в основной поток Qt,
       даже если сработал из фонового потока библиотеки keyboard).
    """
    word_captured = pyqtSignal(str)

    def __init__(self, hotkey: str = DEFAULT_HOTKEY):
        super().__init__()
        self.hotkey = hotkey
        self._registered = False

    def start(self) -> bool:
        """Регистрирует глобальную горячую клавишу. Возвращает False, если это невозможно."""
        if not is_global_hotkey_supported():
            return False
        try:
            keyboard.add_hotkey(self.hotkey, self._on_hotkey_pressed)
            self._registered = True
            return True
        except Exception as e:
            print(f"Не удалось зарегистрировать горячую клавишу '{self.hotkey}': {e}")
            return False

    def stop(self):
        """Снимает регистрацию горячей клавиши (вызывать при выходе из программы)."""
        if self._registered:
            try:
                keyboard.remove_hotkey(self.hotkey)
            except Exception:
                pass
            self._registered = False

    def _on_hotkey_pressed(self):
        try:
            previous_text = pyperclip.paste()
        except Exception:
            previous_text = ""

        try:
            keyboard.send("ctrl+c")
        except Exception as e:
            print(f"Не удалось скопировать выделенный текст: {e}")
            return

        # Небольшая пауза, чтобы активное приложение успело положить текст в буфер обмена
        time.sleep(0.15)

        try:
            selected_text = pyperclip.paste().strip()
        except Exception:
            selected_text = ""

        if selected_text and selected_text != (previous_text or "").strip():
            self.word_captured.emit(selected_text)
