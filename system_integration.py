"""
Системная интеграция для Windows:
1. Автозапуск программы вместе с Windows (через ветку реестра Run).
2. Глобальный мониторинг буфера обмена для вызова "кружочка" добавления слов.
"""

import sys
import os
import winreg
from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor

IS_WINDOWS = sys.platform == "win32"

APP_NAME = "FrenchDictionaryApp"
RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


# ------------------------- 1. Автозапуск (Windows Run-ключ реестра) -------------------------

def is_autostart_supported() -> bool:
    return IS_WINDOWS

def _get_executable_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script_path = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{script_path}"'

def is_autostart_enabled() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            try:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(value)
            except FileNotFoundError:
                return False
    except Exception as e:
        print(f"Не удалось проверить состояние автозапуска: {e}")
        return False

def enable_autostart() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        command = _get_executable_command()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        return True
    except Exception as e:
        print(f"Не удалось включить автозапуск: {e}")
        return False

def disable_autostart() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        return True
    except Exception as e:
        print(f"Не удалось отключить автозапуск: {e}")
        return False


# ------------------------- 2. Всплывающий кружочек при копировании -------------------------

class FloatingAddButton(QWidget):
    """Прозрачный виджет с круглой кнопкой, который появляется поверх всех окон."""
    word_to_add = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Настройки окна: поверх всех, без рамок, не отбирает фокус
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(50, 50)
        
        self.btn = QPushButton("➕", self)
        self.btn.setFixedSize(40, 40)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Стилизуем под красивый синий кружочек
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border-radius: 20px;
                font-size: 20px;
                font-weight: bold;
                border: 2px solid white;
            }
            QPushButton:hover {
                background-color: #2ECC71;
                border: 2px solid #27AE60;
            }
        """)
        self.btn.move(5, 5)  # Небольшой отступ от краев прозрачного виджета
        self.btn.clicked.connect(self.on_clicked)
        
        self.current_word = ""
        
        # Таймер, чтобы кружок исчезал, если его проигнорировали (через 4 секунды)
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self.hide)
        
    def show_for_word(self, word):
        """Перемещает кружок к курсору мыши и показывает его."""
        self.current_word = word
        pos = QCursor.pos()
        # Показываем чуть правее и ниже курсора
        self.move(pos.x() + 15, pos.y() + 15)
        self.show()
        self.hide_timer.start(4000) 
        
    def on_clicked(self):
        """Если нажали — отправляем сигнал с сохраненным словом."""
        if self.current_word:
            self.word_to_add.emit(self.current_word)
        self.hide()


class ClipboardMonitor:
    """Следит за буфером обмена и вызывает кружочек, если скопировано одно слово."""
    def __init__(self, app_instance, add_callback):
        self.app = app_instance
        self.clipboard = self.app.clipboard()
        
        self.floating_btn = FloatingAddButton()
        self.floating_btn.word_to_add.connect(add_callback)
        
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        self.last_text = self.clipboard.text().strip()
        
    def on_clipboard_change(self):
        text = self.clipboard.text().strip()
        
        # Защита от спама: реагируем только на новый текст
        if not text or text == self.last_text:
            return
            
        self.last_text = text
        
        # Проверяем, что это короткое слово или фраза (не больше 3 слов, не больше 30 символов)
        words_count = len(text.split())
        if words_count <= 3 and len(text) < 30:
            self.floating_btn.show_for_word(text)

