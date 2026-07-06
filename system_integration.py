"""
Модуль системной интеграции для Windows с визуальной круглой кнопкой.
"""

import sys
import os
import time

APP_NAME = "FrenchDictionaryApp"
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
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Прозрачный фон для круга
        
        # Размеры кружка (30x30 пикселей)
        self.setFixedSize(40, 40)
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
        self.current_text = text

        print(f"[DEBUG] Показываем: {text}")
        print(f"[DEBUG] Координаты: {x}, {y}")

        self.move(x + 15, y - 10)

        self.show()
        self.raise_()
        self.activateWindow()

        print("[DEBUG] visible =", self.isVisible())

        self.hide_timer.start(3000)

    def enterEvent(self, event: QEnterEvent):
        """Если пользователь навел мышь на кружок, отменяем таймер скрытия."""
        self.hide_timer.stop()
        super().enterEvent(event)

    def _on_clicked(self):
        if self.current_text:
            self.clicked_word.emit(self.current_text)
        self.hide()


# ------------------------- Режим выделения слов (Alt+W) -------------------------

# Сколько секунд максимум может пройти между двумя кликами ЛКМ, чтобы засчитать их
# как двойной клик (двойной клик — это то, чем пользователь выделяет одно слово),
# и на сколько пикселей курсор может сместиться между кликами.
DOUBLE_CLICK_MAX_INTERVAL = 0.4
DOUBLE_CLICK_MAX_DISTANCE = 6

# Горячая клавиша, которой пользователь включает и выключает режим выделения слов.
DEFAULT_TOGGLE_HOTKEY = "alt+w"


def is_word_selection_mode_supported() -> bool:
    return sys.platform == "win32" and _MOUSE_AVAILABLE and _KEYBOARD_AVAILABLE and _PYPERCLIP_AVAILABLE


def get_missing_word_selection_dependencies() -> list:
    missing = []
    if not _MOUSE_AVAILABLE:
        missing.append("mouse")
    if not _KEYBOARD_AVAILABLE:
        missing.append("keyboard")
    if not _PYPERCLIP_AVAILABLE:
        missing.append("pyperclip")
    return missing


class WordSelectionModeWatcher(QObject):
    """
    Режим "выделения слов мышью", включаемый и выключаемый горячей клавишей Alt+W.

    Пока режим выключен, программа не трогает мышь вообще. Как только пользователь
    нажимает Alt+W, включается слежение за мышью в любом приложении Windows: как
    только пользователь выделяет слово двойным кликом, рядом с курсором появляется
    круглая кнопка с предложением добавить это слово в словарь. Слежение продолжает
    работать (то есть кнопка будет появляться для каждого следующего выделенного
    слова) до тех пор, пока пользователь снова не нажмет Alt+W — тогда слежение
    выключается и мышь больше не отслеживается.
    """
    # Испускается, когда пользователь кликнул по кружку и подтвердил, что хочет
    # добавить показанное слово в словарь.
    word_ready_to_add = pyqtSignal(str)
    # Испускается при включении (True) и выключении (False) режима — например,
    # чтобы главное окно могло обновить подсказку в интерфейсе.
    mode_changed = pyqtSignal(bool)

    def __init__(self, toggle_hotkey: str = DEFAULT_TOGGLE_HOTKEY):
        super().__init__()
        self.toggle_hotkey = toggle_hotkey
        self._hotkey_registered = False
        self._mouse_hooked = False
        self.active = False
        # Время и координаты предыдущего отпускания ЛКМ — по ним сами определяем двойной клик.
        self._last_click_time = 0.0
        self._last_click_pos = (0, 0)
        # Создаем экземпляр кружка
        self.popup_button = RoundAddButton()
        # Связываем клик по кружку с внешним сигналом менеджера
        self.popup_button.clicked_word.connect(self.word_ready_to_add.emit)

    def start(self) -> bool:
        """Регистрирует глобальную горячую клавишу Alt+W. Само слежение за мышью
        при этом еще не включается — оно включится только по первому нажатию Alt+W."""
        if not is_word_selection_mode_supported():
            return False
        try:
            # suppress=True не дает нажатию Alt+W "утечь" в активное окно — иначе
            # эта комбинация дополнительно сработает как обычное нажатие клавиш
            # в текущей программе (что угодно, вплоть до системных сочетаний).
            keyboard.add_hotkey(self.toggle_hotkey, self._toggle_mode, suppress=True)
            self._hotkey_registered = True
            return True
        except Exception as e:
            print(f"Не удалось зарегистрировать горячую клавишу '{self.toggle_hotkey}': {e}")
            return False

    def stop(self):
        """Полностью отключает менеджер: снимает горячую клавишу и слежение за мышью."""
        if self._hotkey_registered:
            try:
                keyboard.remove_hotkey(self.toggle_hotkey)
            except Exception:
                pass
            self._hotkey_registered = False
        self._disable_mouse_tracking()
        self.active = False
        self.popup_button.close()

    def _toggle_mode(self):
        """Срабатывает по нажатию Alt+W: включает режим, если он был выключен, и наоборот."""
        # На всякий случай принудительно "отпускаем" alt и w в трекере библиотеки keyboard.
        # Без этого библиотека иногда продолжает считать Alt зажатым даже после того,
        # как пользователь физически его отпустил, из-за чего следующий keyboard.send("ctrl+c")
        # в _on_word_selected на самом деле уходит в систему как Ctrl+Alt+C — копирование
        # не срабатывает, а активная программа может отреагировать на эту комбинацию
        # по-своему (например, убавить громкость).
        for key in ("alt", "w", "ctrl", "shift", "windows"):
            try:
                keyboard.release(key)
            except Exception:
                pass

        if self.active:
            self._deactivate()
        else:
            self._activate()

    def _activate(self):
        if not self._enable_mouse_tracking():
            return
        self.active = True
        self.mode_changed.emit(True)

    def _deactivate(self):
        self._disable_mouse_tracking()
        self.active = False
        self.mode_changed.emit(False)

    def _enable_mouse_tracking(self) -> bool:
        if self._mouse_hooked:
            return True
        try:
            # Слушаем КАЖДОЕ отпускание ЛКМ и сами решаем, был ли это двойной клик
            # (по времени и расстоянию между двумя последовательными кликами).
            # Так одиночный клик гарантированно никогда не запускает копирование —
            # в отличие от встроенного mouse.on_double_click, поведение которого
            # мы не контролируем напрямую.
            mouse.on_button(self._on_left_click, buttons=(mouse.LEFT,), types=(mouse.UP,))
            self._mouse_hooked = True
            return True
        except Exception as e:
            print(f"Не удалось включить слежение за выделением текста: {e}")
            return False

    def _disable_mouse_tracking(self):
        if self._mouse_hooked:
            try:
                mouse.unhook_all()
            except Exception:
                pass
            self._mouse_hooked = False

    def _on_left_click(self):
        """Срабатывает на КАЖДОЕ отпускание ЛКМ, пока режим включен; действие
        запускаем только если это второй клик подряд (двойной клик)."""
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

        self._on_word_selected(x, y)

    def _on_word_selected(self, x, y):
        try:
            previous_text = pyperclip.paste()
        except Exception:
            previous_text = ""

        # Второй защитный сброс модификаторов прямо перед копированием: если вдруг
        # пользователь до сих пор физически держит Alt (или Ctrl/Shift), Ctrl+C
        # снова превратится в другое сочетание и ничего не скопируется.
        
    # гарантированно отпускаем все модификаторы
            for key in ("alt", "ctrl", "shift", "windows"):
                keyboard.release(key)

            time.sleep(0.02)

            try:
                pyperclip.copy("")
            except Exception:
                pass

            keyboard.send("ctrl+c")

        except Exception:
            return

            time.sleep(0.25)

        # try:
        #     selected_text = pyperclip.paste().strip()
        # except Exception:
        #     selected_text = ""

        # if not selected_text or selected_text == (previous_text or "").strip():
        #     return

        # if len(selected_text) > MAX_SELECTION_LENGTH:
        #     return

        # # x, y — координаты курсора в момент самого двойного клика (переданы вызывающим
        # # кодом), а не после паузы в 150мс, за которую курсор мог успеть сместиться.

        # # Вместо простой отправки координат бэкенду,
        # # мы напрямую заставляем UI-кружок появиться на экране в нужной точке.
        # # Метод вызовется безопасно в контексте потока Qt.
        # QTimer.singleShot(0, lambda: self.popup_button.show_at(selected_text, x, y))


        try:
            selected_text = pyperclip.paste().strip()
            print(f"[DEBUG] Выделено: '{selected_text}'")
        except Exception as e:
            print("[DEBUG] Ошибка буфера:", e)
            selected_text = ""

        if not selected_text:
            print("[DEBUG] Текст пустой")
        return

        print("[DEBUG] Показываем кружок")

        self.popup_button.show_at(
            selected_text,
            x,
            y
        )

print("[DEBUG] show_at вызван")


# --- Пример для тестирования (можно запустить напрямую этот файл) ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    watcher = WordSelectionModeWatcher()
    if watcher.start():
        print("Менеджер режима выделения слов запущен. Нажмите Alt+W, чтобы включить слежение...")

        # Тестовый обработчик: покажет в консоли, что слово успешно «перехвачено» кружком
        watcher.word_ready_to_add.connect(lambda word: print(f"Слово добавлено в словарь: {word}"))
        watcher.mode_changed.connect(lambda on: print("Режим выделения:", "включен" if on else "выключен"))

        sys.exit(app.exec())
    else:
        print("Ошибка запуска. Проверьте зависимости:", get_missing_word_selection_dependencies())
