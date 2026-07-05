"""
Модуль системной интеграции для Windows с визуальной круглой кнопкой.
"""

import sys
import os
import time

APP_NAME = "FrenchDictionaryApp"
DEFAULT_HOTKEY = "ctrl+alt+d"
MAX_SELECTION_LENGTH = 120

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

try:
    import mouse
    _MOUSE_AVAILABLE = True
except ImportError:
    _MOUSE_AVAILABLE = False

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QPushButton, QApplication
from PyQt6.QtGui import QCursor, QEnterEvent


# ------------------------- Автозапуск при включении ПК -------------------------

def _get_run_registry_path():
    return winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    python_dir = os.path.dirname(sys.executable)
    pythonw_path = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw_path):
        pythonw_path = sys.executable

    script_path = os.path.abspath(sys.argv[0])
    return f'"{pythonw_path}" "{script_path}"'


def is_autostart_supported() -> bool:
    return sys.platform == "win32" and _WINREG_AVAILABLE


def is_autostart_enabled() -> bool:
    if not is_autostart_supported():
        return False
    try:
        hive, path = _get_run_registry_path()
        with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except (FileNotFoundError, OSError):
        return False
    except Exception as e:
        print(f"Ошибка при проверке автозапуска: {e}")
        return False


def enable_autostart() -> bool:
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
    return sys.platform == "win32" and _KEYBOARD_AVAILABLE and _PYPERCLIP_AVAILABLE


def get_missing_dependencies() -> list:
    missing = []
    if not _KEYBOARD_AVAILABLE:
        missing.append("keyboard")
    if not _PYPERCLIP_AVAILABLE:
        missing.append("pyperclip")
    return missing


class GlobalWordCapture(QObject):
    word_captured = pyqtSignal(str)

    def __init__(self, hotkey: str = DEFAULT_HOTKEY):
        super().__init__()
        self.hotkey = hotkey
        self._registered = False

    def start(self) -> bool:
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

        for key in ("alt", "ctrl", "d"):
            try:
                keyboard.release(key)
            except Exception:
                pass
        time.sleep(0.05)

        try:
            keyboard.send("ctrl+c")
        except Exception as e:
            print(f"Не удалось скопировать выделенный текст: {e}")
            return

        time.sleep(0.15)

        try:
            selected_text = pyperclip.paste().strip()
        except Exception:
            selected_text = ""

        if selected_text and selected_text != (previous_text or "").strip():
            self.word_captured.emit(selected_text)


# ==================== Всплывающая кнопка-кружок ====================

class RoundAddButton(QPushButton):
    """
    Маленькая круглая кнопка, которая появляется возле курсора.
    При клике испускает сигнал с добавленным словом.
    """
    clicked_word = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.ToolTip |              # Поверх всех окон, без рамки и иконки в таскбаре
            Qt.WindowType.FramelessWindowHint |  # Убираем стандартные границы Windows
            Qt.WindowType.WindowDoesNotAcceptFocus # Не забирает фокус ввода у активного приложения
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Прозрачный фон для круга
        
        # Размеры кружка (30x30 пикселей)
        self.setFixedSize(30, 30)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Стилизация: синий кружок с белым плюсом (можно изменить под свой дизайн)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 15px; /* Половина от 30px делает виджет круглым */
                font-size: 18px;
                font-weight: bold;
                border: 2px solid white;
            }
            QPushButton:hover {
                background-color: #0B7BDA;
            }
        """)
        self.setText("+")
        self.current_text = ""
        
        # Таймер автоматического скрытия (чтобы кружок исчезал через 3 секунды, если его проигнорировали)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
        self.clicked.connect(self._on_clicked)

    def show_at(self, text: str, x: int, y: int):
        """Отображает кнопку чуть правее и выше курсора, чтобы не мешать кликать дальше."""
        self.current_text = text
        # Смещение: +15 пикселей вправо, -10 пикселей вверх от кончика курсора
        self.move(x + 15, y - 10)
        self.show()
        self.hide_timer.start(3000) # Исчезнет через 3000 мс (3 секунды)

    def enterEvent(self, event: QEnterEvent):
        """Если пользователь навел мышь на кружок, отменяем таймер скрытия."""
        self.hide_timer.stop()
        super().enterEvent(event)

    def _on_clicked(self):
        if self.current_text:
            self.clicked_word.emit(self.current_text)
        self.hide()


# ------------------------- Менеджер выделения текста -------------------------

# Сколько секунд максимум может пройти между двумя кликами ЛКМ, чтобы засчитать их
# как двойной клик, и на сколько пикселей курсор может сместиться между кликами.
DOUBLE_CLICK_MAX_INTERVAL = 0.4
DOUBLE_CLICK_MAX_DISTANCE = 6


def is_selection_popup_supported() -> bool:
    return sys.platform == "win32" and _MOUSE_AVAILABLE and _KEYBOARD_AVAILABLE and _PYPERCLIP_AVAILABLE


def get_missing_selection_dependencies() -> list:
    missing = []
    if not _MOUSE_AVAILABLE:
        missing.append("mouse")
    if not _KEYBOARD_AVAILABLE:
        missing.append("keyboard")
    if not _PYPERCLIP_AVAILABLE:
        missing.append("pyperclip")
    return missing


class SelectionPopupWatcher(QObject):
    """
    Отслеживает выделение мышью и координирует появление круглой кнопки.
    """
    # Этот сигнал теперь можно использовать в главном окне приложения:
    # watcher.word_ready_to_add.connect(self.my_add_to_dictionary_function)
    word_ready_to_add = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._hooked = False
        # Время и координаты предыдущего отпускания ЛКМ — по ним сами определяем двойной клик.
        self._last_click_time = 0.0
        self._last_click_pos = (0, 0)
        # Создаем экземпляр кружка
        self.popup_button = RoundAddButton()
        # Связываем клик по кружку с внешним сигналом менеджера
        self.popup_button.clicked_word.connect(self.word_ready_to_add.emit)

    def start(self) -> bool:
        if not is_selection_popup_supported():
            return False
        try:
            # Слушаем КАЖДОЕ отпускание ЛКМ и сами решаем, был ли это двойной клик
            # (по времени и расстоянию между двумя последовательными кликами).
            # Так одиночный клик гарантированно никогда не запускает копирование —
            # в отличие от встроенного mouse.on_double_click, поведение которого
            # мы не контролируем напрямую.
            mouse.on_button(self._on_left_click, buttons=(mouse.LEFT,), types=(mouse.UP,))
            self._hooked = True
            return True
        except Exception as e:
            print(f"Не удалось включить слежение за выделением текста: {e}")
            return False

    def stop(self):
        if self._hooked:
            try:
                mouse.unhook_all()
            except Exception:
                pass
            self._hooked = False
        self.popup_button.close()

    def _on_left_click(self):
        """Срабатывает на КАЖДОЕ отпускание ЛКМ; действие запускаем только если это второй клик подряд."""
        now = time.time()
        try:
            x, y = mouse.get_position()
        except Exception:
            x, y = (0, 0)

        dx = abs(x - self._last_click_pos[0])
        dy = abs(y - self._last_click_pos[1])
        is_double_click = (
            (now - self._last_click_time) <= DOUBLE_CLICK_MAX_INTERVAL
            and dx <= DOUBLE_CLICK_MAX_DISTANCE
            and dy <= DOUBLE_CLICK_MAX_DISTANCE
        )

        self._last_click_time = now
        self._last_click_pos = (x, y)

        if not is_double_click:
            # Одиночный клик — просто запоминаем его как возможное "первое нажатие" и выходим.
            return

        # Обнуляем время, чтобы быстрый третий клик подряд не засчитался
        # еще одним двойным кликом от того же самого первого нажатия.
        self._last_click_time = 0.0

        self._on_double_click(x, y)

    def _on_double_click(self, x, y):
        try:
            previous_text = pyperclip.paste()
        except Exception:
            previous_text = ""

        try:
            keyboard.send("ctrl+c")
        except Exception:
            return

        time.sleep(0.15)

        try:
            selected_text = pyperclip.paste().strip()
        except Exception:
            selected_text = ""

        if not selected_text or selected_text == (previous_text or "").strip():
            return

        if len(selected_text) > MAX_SELECTION_LENGTH:
            return

        # x, y — координаты курсора в момент самого двойного клика (переданы вызывающим
        # кодом), а не после паузы в 150мс, за которую курсор мог успеть сместиться.

        # Вместо простой отправки координат бэкенду, 
        # мы напрямую заставляем UI-кружок появиться на экране в нужной точке.
        # Метод вызовется безопасно в контексте потока Qt.
        QTimer.singleShot(0, lambda: self.popup_button.show_at(selected_text, x, y))


# --- Пример для тестирования (можно запустить напрямую этот файл) ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    watcher = SelectionPopupWatcher()
    if watcher.start():
        print("Слушатель выделения запущен. Выделите текст в любом приложении...")
        
        # Тестовый обработчик: покажет в консоли, что слово успешно «перехвачено» кружком
        watcher.word_ready_to_add.connect(lambda word: print(f"Слово добавлено в словарь: {word}"))
        
        sys.exit(app.exec())
    else:
        print("Ошибка запуска. Проверьте зависимости:", get_missing_selection_dependencies())