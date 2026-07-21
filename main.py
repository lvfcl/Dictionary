import random
import sys
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtWidgets import (QApplication, QMessageBox, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextBrowser, QWidget,
                             QComboBox, QSpinBox, QListWidget, QListWidgetItem,
                             QSystemTrayIcon, QMenu, QStyle)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from ui_main import DictionaryUI
from rules_dialog import RulesDialog, RULES_SECTIONS
import database
import api_worker
import audio_manager
import system_integration


class TranslationThread(QThread):
    """Отдельный поток для работы с API, чтобы интерфейс не зависал при запросах."""
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, word):
        super().__init__()
        self.word = word

    def run(self):
        try:
            result = api_worker.get_full_word_data(self.word)
            if result and result[0]:
                self.finished.emit(result)
            else:
                self.error.emit("Слово не найдено или ошибка перевода.")
        except Exception as e:
            self.error.emit(str(e))


class FolderSuggestionThread(QThread):
    """Отдельный поток для запроса к ИИ анализа слов словаря на соответствие теме папки."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, topic, candidates):
        super().__init__()
        self.topic = topic
        self.candidates = candidates

    def run(self):
        try:
            result = api_worker.suggest_matching_words(self.topic, self.candidates)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class FolderSuggestionDialog(QDialog):
    """
    Показывает слова, отобранные ИИ из уже существующего словаря пользователя (как
    подходящие по теме папки), по одному: пользователь решает, добавить слово
    в папку или пропустить его.
    """
    def __init__(self, suggestions, folder_name, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.queue = list(suggestions)
        self.added_count = 0
        self.current = None

        self.setWindowTitle(f"Подходящие слова для папки «{folder_name}»")
        self.resize(480, 400)

        self.init_ui()
        self.next_word()

    def init_ui(self):
        layout = QVBoxLayout()

        self.counter_label = QLabel(self)
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.counter_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(self.counter_label)

        self.word_label = QLabel(self)
        self.word_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(self.word_label)

        self.trans_label = QLabel(self)
        self.trans_label.setFont(QFont("Arial", 13))
        self.trans_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        self.trans_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.trans_label)

        self.ru_label = QLabel(self)
        self.ru_label.setFont(QFont("Arial", 16))
        self.ru_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ru_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(self.ru_label)

        self.examples_browser = QTextBrowser(self)
        self.examples_browser.setMaximumHeight(140)
        self.examples_browser.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(self.examples_browser)

        buttons_layout = QHBoxLayout()

        self.reject_btn = QPushButton("❌ Пропустить", self)
        self.reject_btn.setFixedHeight(42)
        self.reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reject_btn.setStyleSheet(
            "background-color:#ff4d4d; color:white; font-weight:bold; border-radius:4px;"
        )
        self.reject_btn.clicked.connect(self.reject_current)

        self.accept_btn = QPushButton("✔ Добавить в папку", self)
        self.accept_btn.setFixedHeight(42)
        self.accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.accept_btn.setStyleSheet(
            "background-color:#2ECC71; color:white; font-weight:bold; border-radius:4px;"
        )
        self.accept_btn.clicked.connect(self.accept_current)

        buttons_layout.addWidget(self.reject_btn)
        buttons_layout.addWidget(self.accept_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def next_word(self):
        """Показывает следующее слово из очереди подобранных ИИ кандидатов."""
        if not self.queue:
            QMessageBox.information(
                self, "Готово",
                f"Просмотр завершен. Добавлено в папку «{self.folder_name}»: {self.added_count}."
            )
            self.accept()
            return

        self.counter_label.setText(f"Осталось предложений: {len(self.queue)}")
        self.current = self.queue.pop(0)

        self.word_label.setText(self.current.get("french", ""))
        self.trans_label.setText(self.current.get("transcription", ""))
        self.ru_label.setText(self.current.get("russian", ""))

        examples_text = ""
        for ex in self.current.get("examples", []):
            examples_text += f"<b>FR:</b> {ex.get('fr', '')}<br><b>RU:</b> {ex.get('ru', '')}<br><br>"
        self.examples_browser.setHtml(examples_text if examples_text else "Примеров нет.")

    def accept_current(self):
        """Добавляет уже существующее в словаре слово в текущую папку (новая карточка не создается)."""
        if not self.current:
            return

        added = database.add_word_to_folder(self.current.get("french", ""), self.folder_name)
        if added:
            self.added_count += 1

        self.next_word()

    def reject_current(self):
        """Пропускает предложенное слово без добавления в папку."""
        self.next_word()


class AssignFolderDialog(QDialog):
    """Позволяет вручную отметить, в каких папках должно находиться конкретное слово."""
    def __init__(self, french_word, parent=None):
        super().__init__(parent)
        self.french_word = french_word
        self.all_folders = database.load_folders()
        self.word_folders = set(database.get_word_folders(french_word))

        self.setWindowTitle(f"Папки для слова «{french_word}»")
        self.resize(320, 380)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        info_label = QLabel("Отметьте папки, в которые нужно добавить слово:")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(info_label)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("color: #f5a623; font-weight: bold;")
        for folder_name in self.all_folders:
            item = QListWidgetItem(folder_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if folder_name in self.word_folders else Qt.CheckState.Unchecked
            )
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        if not self.all_folders:
            empty_label = QLabel("Папок пока нет. Сначала создайте папку в левой панели.")
            empty_label.setStyleSheet("color: #f5a623; font-weight: bold;")
            empty_label.setWordWrap(True)
            layout.addWidget(empty_label)

        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet("background-color:#4A90E2; color:white; font-weight:bold;")
        save_btn.clicked.connect(self.save_and_close)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def save_and_close(self):
        """Применяет изменения: слово добавляется/убирается из отмеченных/снятых папок."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            folder_name = item.text()
            is_checked = item.checkState() == Qt.CheckState.Checked
            was_checked = folder_name in self.word_folders

            if is_checked and not was_checked:
                database.add_word_to_folder(self.french_word, folder_name)
            elif not is_checked and was_checked:
                database.remove_word_from_folder(self.french_word, folder_name)

        self.accept()


class ReviewSetupDialog(QDialog):
    """Диалог выбора источника слов (все слова или конкретная папка) и размера колоды."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_folder = None
        self.selected_count = 0

        self.setWindowTitle("Настройка сессии повторения")
        self.resize(360, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        source_title = QLabel("Откуда брать слова:")
        source_title.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(source_title)

        self.source_combo = QComboBox()
        self.source_combo.setStyleSheet("color: #f5a623; font-weight: bold;")
        self.source_combo.addItem("Все слова")
        self.source_combo.addItems(database.load_folders())
        self.source_combo.currentIndexChanged.connect(self.update_due_count)
        layout.addWidget(self.source_combo)

        self.due_label = QLabel()
        self.due_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(self.due_label)

        count_title = QLabel("Сколько слов взять в колоду:")
        count_title.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(count_title)

        self.count_spin = QSpinBox()
        self.count_spin.setStyleSheet("color: #f5a623; font-weight: bold;")
        self.count_spin.setMinimum(1)
        layout.addWidget(self.count_spin)

        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        start_btn = QPushButton("Начать")
        start_btn.setStyleSheet("background-color:#2ECC71; color:white; font-weight:bold;")
        start_btn.clicked.connect(self.try_accept)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(start_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.update_due_count()

    def get_due_words(self):
        """Возвращает слова, готовые к повторению сегодня, из выбранного источника."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        source = self.source_combo.currentText()

        if source == "Все слова":
            all_words = database.load_words()
        else:
            all_words = database.get_words_by_folder(source)

        return [w for w in all_words if w.get("next_review", today_str) <= today_str]

    def update_due_count(self):
        """Обновляет счетчик доступных карточек при смене источника."""
        due_count = len(self.get_due_words())
        self.due_label.setText(f"Доступно карточек для повторения: {due_count}")
        self.count_spin.setMaximum(max(due_count, 1))
        self.count_spin.setValue(min(20, due_count) if due_count else 1)
        self.count_spin.setEnabled(due_count > 0)

    def try_accept(self):
        due_count = len(self.get_due_words())
        if due_count == 0:
            QMessageBox.information(
                self, "Готово!", "На сегодня нет слов для повторения в этой колоде. Отдыхайте!"
            )
            return

        source = self.source_combo.currentText()
        self.selected_folder = None if source == "Все слова" else source
        self.selected_count = self.count_spin.value()
        self.accept()


class ReviewDialog(QDialog):
    """Диалоговое окно для интервального повторения слов (Режим Anki)"""
    def __init__(self, limit_count, folder_name=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Интервальное повторение (Anki)")
        self.resize(500, 400)
        
        if folder_name:
            all_words = database.get_words_by_folder(folder_name)
        else:
            all_words = database.load_words()

        today_str = datetime.now().strftime("%Y-%m-%d")
        
        due_words = [w for w in all_words if w.get("next_review", today_str) <= today_str]
        
        if not due_words:
            QMessageBox.information(self, "Готово!", "На сегодня нет слов для повторения. Отдыхайте!")
            self.reject()
            return

        random.shuffle(due_words)
        
        self.queue = due_words[:limit_count]
        self.current_card = None
        
        self.init_ui()
        self.next_card()

    def init_ui(self):
        layout = QVBoxLayout()
        
        self.counter_label = QLabel(self)
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.counter_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        layout.addWidget(self.counter_label)
        
        word_row = QHBoxLayout()
        word_row.addStretch()

        self.word_label = QLabel(self)
        self.word_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        word_row.addWidget(self.word_label)

        self.review_audio_btn = QPushButton("🔊", self)
        self.review_audio_btn.setFixedSize(36, 36)
        self.review_audio_btn.setFont(QFont("Arial", 14))
        self.review_audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.review_audio_btn.setStyleSheet("border: none; background-color: transparent;")
        self.review_audio_btn.clicked.connect(self.play_current_audio)
        word_row.addWidget(self.review_audio_btn)

        word_row.addStretch()
        layout.addLayout(word_row)

        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        
        self.answer_box = QWidget()
        answer_layout = QVBoxLayout(self.answer_box)
        
        self.trans_label = QLabel(self)
        self.trans_label.setFont(QFont("Arial", 14))
        self.trans_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trans_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        answer_layout.addWidget(self.trans_label)
        
        self.ru_label = QLabel(self)
        self.ru_label.setFont(QFont("Arial", 18, QFont.Weight.Medium))
        self.ru_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ru_label.setStyleSheet("color: #f5a623; font-weight: bold;")
        answer_layout.addWidget(self.ru_label)
        
        self.examples_browser = QTextBrowser(self)
        self.examples_browser.setMaximumHeight(120)
        self.examples_browser.setStyleSheet("color: #f5a623; font-weight: bold;")
        answer_layout.addWidget(self.examples_browser)
        
        layout.addWidget(self.answer_box)
        
        self.show_answer_btn = QPushButton("Показать перевод", self)
        self.show_answer_btn.setFont(QFont("Arial", 12))
        self.show_answer_btn.setFixedHeight(40)
        self.show_answer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_answer_btn.clicked.connect(self.show_answer)
        layout.addWidget(self.show_answer_btn)
        
        self.buttons_panel = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_panel)
        
        qualities = [("Забыл", 0, "#ff4d4d"), ("Сложно", 1, "#ff944d"), 
                     ("Хорошо", 2, "#33cc33"), ("Легко", 3, "#3399ff")]
                     
        for text, val, color in qualities:
            btn = QPushButton(text, self)
            btn.setFixedHeight(35)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; border-radius: 4px;")
            btn.clicked.connect(lambda checked, v=val: self.handle_score(v))
            buttons_layout.addWidget(btn)
            
        layout.addWidget(self.buttons_panel)
        self.setLayout(layout)

    def next_card(self):
        """Переходит к следующему слову в очереди."""
        if not self.queue:
            QMessageBox.information(self, "Готово!", "Отличная работа! Сессия завершена, выбранная колода изучена.")
            self.accept()
            return
            
        self.counter_label.setText(f"Осталось карточек в колоде: {len(self.queue)}")
        self.current_card = self.queue.pop(0)
        
        self.word_label.setText(self.current_card.get("french", ""))
        self.trans_label.setText(self.current_card.get("transcription", ""))
        self.ru_label.setText(self.current_card.get("russian", ""))

        self.play_current_audio()
        
        examples_text = ""
        for ex in self.current_card.get("examples", []):
            examples_text += f"<b>FR:</b> {ex['fr']}<br><b>RU:</b> {ex['ru']}<br><br>"
        self.examples_browser.setHtml(examples_text if examples_text else "Примеров контекста нет.")
        
        self.answer_box.hide()
        self.buttons_panel.hide()
        self.show_answer_btn.show()

    def show_answer(self):
        """Открывает скрытую информацию (перевод и контекст)."""
        self.show_answer_btn.hide()
        self.answer_box.show()
        self.buttons_panel.show()

    def play_current_audio(self):
        """Воспроизводит произношение слова текущей карточки."""
        if not self.current_card:
            return
        word = self.current_card.get("french", "")
        path = audio_manager.get_audio_path(word)
        if path:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.media_player.play()

    def handle_score(self, quality):
        """Обрабатывает нажатие на кнопку градации сложности."""
        if not self.current_card:
            return

        updated_card = database.update_card_review(self.current_card, quality)
        
        all_words = database.load_words()
        for i, word in enumerate(all_words):
            if word.get("french") == updated_card["french"]:
                all_words[i] = updated_card
                break
                
        with open("dictionary.json", "w", encoding="utf-8") as f:
            json.dump(all_words, f, ensure_ascii=False, indent=4)
            
        if quality == 0:
            self.queue.append(updated_card)
            
        self.next_card()


class MainApp(DictionaryUI):
    def __init__(self):
        super().__init__()
        
        self.current_word = ""
        self.active_folder = None
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        self.add_button.clicked.connect(self.start_translation)
        self.word_input.returnPressed.connect(self.start_translation)
        
        self.review_button.clicked.connect(self.open_review_mode)
        
        self.table.itemClicked.connect(self.show_word_details)

        self.folder_list.itemClicked.connect(self.on_folder_selected)
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        self.delete_folder_btn.clicked.connect(self.delete_selected_folder)
        self.show_all_words_btn.clicked.connect(self.show_all_words)
        self.populate_folder_btn.clicked.connect(self.open_ai_populate_dialog)
        self.rules_button.clicked.connect(self.open_rules_dialog)

        for index, rule_btn in enumerate(self.rules_category_buttons):
            rule_btn.clicked.connect(lambda checked, idx=index: self.select_rule_category(idx))

        self.load_folders_list()
        self.load_saved_data()

        self.init_tray_icon()
        self.init_autostart_option()
        self.init_background_mode_option()
        self.init_rules_mode_option()
        self.init_tray_icon()
        self.init_autostart_option()
        self.init_background_mode_option()

        # --- НОВАЯ СТРОКА: Инициализация слежения за Ctrl+C ---
        self.clipboard_monitor = system_integration.ClipboardMonitor(QApplication.instance(), self.quick_add_word)


    def init_tray_icon(self):
        """Создает иконку в системном трее, чтобы программа могла тихо работать в фоне."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self.tray_icon.setToolTip("Французский словарь")

        tray_menu = QMenu()

        show_action = QAction("Открыть словарь", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def init_autostart_option(self):
        """Синхронизирует флажок автозапуска с текущим состоянием реестра Windows."""
        if not system_integration.is_autostart_supported():
            self.autostart_checkbox.setEnabled(False)
            self.autostart_checkbox.setToolTip("Автозапуск поддерживается только в Windows.")
            return

        self.autostart_checkbox.setChecked(system_integration.is_autostart_enabled())
        self.autostart_checkbox.stateChanged.connect(self.toggle_autostart)

    def toggle_autostart(self, state):
        """Включает или отключает автозапуск программы вместе с Windows."""
        want_enabled = (state == Qt.CheckState.Checked.value)

        if want_enabled:
            success = system_integration.enable_autostart()
            message = "Автозапуск включен." if success else "Не удалось включить автозапуск."
        else:
            success = system_integration.disable_autostart()
            message = "Автозапуск отключен." if success else "Не удалось отключить автозапуск."

        if not success:
            QMessageBox.warning(self, "Ошибка автозапуска", message)
            self.autostart_checkbox.blockSignals(True)
            self.autostart_checkbox.setChecked(not want_enabled)
            self.autostart_checkbox.blockSignals(False)
        else:
            self.statusBar().showMessage(message, 4000)

    def init_background_mode_option(self):
        """Загружает сохраненную настройку фонового режима и применяет её."""
        saved_settings = database.load_settings()
        background_enabled = saved_settings.get("background_mode", True)

        self.background_mode_checkbox.setChecked(background_enabled)
        self.background_mode_checkbox.stateChanged.connect(self.toggle_background_mode)
        self.apply_background_mode(background_enabled, initial=True)

    def init_rules_mode_option(self):
        """Загружает сохраненную настройку того, как открывать окно с правилами."""
        saved_settings = database.load_settings()
        replace_main = saved_settings.get("rules_replace_main", False)

        self.rules_replace_main_checkbox.setChecked(replace_main)
        self.rules_replace_main_checkbox.stateChanged.connect(self.toggle_rules_mode)

    def toggle_rules_mode(self, state):
        """Сохраняет выбор пользователя: правила отдельным окном или вместо главного."""
        replace_main = (state == Qt.CheckState.Checked.value)

        settings = database.load_settings()
        settings["rules_replace_main"] = replace_main
        database.save_settings(settings)

    def toggle_background_mode(self, state):
        """Включает/выключает фоновый режим (работу программы после закрытия окна) и сохраняет выбор."""
        enabled = (state == Qt.CheckState.Checked.value)
        self.apply_background_mode(enabled)

        settings = database.load_settings()
        settings["background_mode"] = enabled
        database.save_settings(settings)

    def apply_background_mode(self, enabled: bool, initial: bool = False):
        """
        Применяет режим фоновой работы:
        - enabled=True: закрытие окна сворачивает программу в трей, приложение не завершается.
        - enabled=False: закрытие окна полностью завершает программу (обычное поведение).
        """
        self.background_mode = enabled
        QApplication.instance().setQuitOnLastWindowClosed(not enabled)

        if not initial:
            if enabled:
                self.statusBar().showMessage(
                    "Фоновый режим включен: при закрытии окно будет сворачиваться в трей.", 4000
                )
            else:
                self.statusBar().showMessage(
                    "Фоновый режим отключен: закрытие окна теперь полностью завершает программу.", 4000
                )

    def on_tray_activated(self, reason):
        """Разворачивает окно программы по клику/двойному клику на иконку в трее."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_from_tray()

    def show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        """Полностью закрывает программу (в отличие от закрытия окна, которое сворачивает в трей)."""
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """
        Если включен фоновый режим — закрытие окна крестиком сворачивает программу в трей.
        Если фоновый режим выключен — закрытие окна полностью завершает программу (обычное поведение).
        """
        if getattr(self, "background_mode", True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Словарь свернут в трей",
                "Программа продолжает работать в фоне.",
                QSystemTrayIcon.MessageIcon.Information,
                4000
            )
        else:
            self.tray_icon.hide()
            event.accept()

    def play_word_audio(self, word: str):
        """Генерирует (если нужно) и воспроизводит произношение указанного слова."""
        if not word:
            return
        self.statusBar().showMessage(f"Загружаю произношение для '{word}'...")
        path = audio_manager.get_audio_path(word)
        if path:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.media_player.play()
            self.statusBar().clearMessage()
        else:
            self.statusBar().showMessage("Не удалось получить аудио. Проверьте подключение к интернету.", 4000)

    def load_folders_list(self):
        """Обновляет список папок в боковой панели."""
        self.folder_list.clear()
        for folder_name in database.load_folders():
            self.folder_list.addItem(folder_name)

    def create_new_folder(self):
        """Запрашивает название и создает новую папку."""
        name, ok = QInputDialog.getText(self, "Новая папка", "Название папки (например, «Еда», «Путешествия»):")
        if ok and name.strip():
            if database.create_folder(name.strip()):
                self.load_folders_list()
                self.statusBar().showMessage(f"Папка '{name.strip()}' создана.")
            else:
                QMessageBox.information(self, "Внимание", f"Папка '{name.strip()}' уже существует.")

    def delete_selected_folder(self):
        """Удаляет выбранную папку (слова из словаря не удаляются)."""
        item = self.folder_list.currentItem()
        if not item:
            QMessageBox.information(self, "Внимание", "Сначала выберите папку для удаления.")
            return

        folder_name = item.text()
        reply = QMessageBox.question(
            self, "Удаление папки",
            f"Удалить папку <b>{folder_name}</b>? Слова из словаря удалены не будут.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            database.delete_folder(folder_name)
            if self.active_folder == folder_name:
                self.active_folder = None
                self.populate_folder_btn.setEnabled(False)
            self.load_folders_list()
            self.load_saved_data()
            self.statusBar().showMessage(f"Папка '{folder_name}' удалена.")

    def on_folder_selected(self, item):
        """Фильтрует таблицу слов по выбранной папке."""
        self.active_folder = item.text()
        self.populate_folder_btn.setEnabled(True)
        self.load_saved_data()

    def show_all_words(self):
        """Сбрасывает фильтр по папке и показывает весь словарь."""
        self.active_folder = None
        self.folder_list.clearSelection()
        self.populate_folder_btn.setEnabled(False)
        self.load_saved_data()

    def on_folder_button_clicked(self):
        """Открывает диалог ручного добавления/удаления слова из папок."""
        button = self.sender()
        if not button:
            return

        french_word = button.property("word")
        dialog = AssignFolderDialog(french_word, self)
        if dialog.exec():
            self.load_saved_data()

    def open_rules_dialog(self):
        """
        Показывает справочник с правилами французской грамматики.
        В зависимости от настройки self.rules_replace_main_checkbox:
        - выключено (по умолчанию): правила открываются отдельным окном поверх главного
          (там кнопки с названиями правил тоже расположены вертикально);
        - включено: в колонке "подробно о слове" (details_panel) появляется
          вертикальный столбец кнопок с названиями правил; клик по кнопке
          открывает соответствующее правило справа.
        """
        settings = database.load_settings()
        replace_main = settings.get("rules_replace_main", False)

        if replace_main:
            self.rules_buttons_container.show()
            self.select_rule_category(0)
        else:
            self.rules_dialog = RulesDialog(self)
            self.rules_dialog.show()

    def select_rule_category(self, index):
        """Показывает выбранное правило в колонке слова и подсвечивает нажатую кнопку."""
        title, html = RULES_SECTIONS[index]
        self.details_panel.setHtml(html)
        for i, btn in enumerate(self.rules_category_buttons):
            btn.setChecked(i == index)

    def open_ai_populate_dialog(self):
        """Запускает анализ ИИ: какие из уже сохраненных слов подходят по теме текущей папки."""
        if not self.active_folder:
            return

        all_words = database.load_words()
        candidates = [
            {"french": w.get("french", ""), "russian": w.get("russian", "")}
            for w in all_words
            if self.active_folder not in w.get("folders", []) and w.get("french")
        ]

        if not candidates:
            QMessageBox.information(
                self, "Нечего анализировать",
                "Все слова из вашего словаря уже добавлены в эту папку (либо словарь пуст)."
            )
            return

        self.populate_folder_btn.setEnabled(False)
        self.populate_folder_btn.setText("Анализирую...")

        self.suggestion_worker = FolderSuggestionThread(self.active_folder, candidates)
        self.suggestion_worker.finished.connect(self.on_suggestions_ready)
        self.suggestion_worker.error.connect(self.on_suggestions_error)
        self.suggestion_worker.start()

    def on_suggestions_ready(self, matched_french_words):
        """Открывает диалог поочередного просмотра слов словаря, подходящих по теме папки."""
        self.populate_folder_btn.setEnabled(True)
        self.populate_folder_btn.setText("Пополнить с ИИ")

        if not matched_french_words:
            QMessageBox.information(
                self, "Нет результатов",
                "ИИ не нашел среди слов вашего словаря подходящих по смыслу для этой папки."
            )
            return

        # Собираем полные карточки (транскрипция, перевод, примеры) для отобранных ИИ слов
        all_words_by_french = {w.get("french", "").lower(): w for w in database.load_words()}
        full_matches = []
        for french_word in matched_french_words:
            card = all_words_by_french.get(french_word.lower())
            if card:
                full_matches.append(card)

        if not full_matches:
            QMessageBox.information(
                self, "Нет результатов",
                "ИИ не нашел среди слов вашего словаря подходящих по смыслу для этой папки."
            )
            return

        dialog = FolderSuggestionDialog(full_matches, self.active_folder, self)
        dialog.exec()
        self.load_saved_data()

    def on_suggestions_error(self, error_message):
        self.populate_folder_btn.setEnabled(True)
        self.populate_folder_btn.setText("Пополнить с ИИ")
        QMessageBox.warning(self, "Ошибка анализа слов", error_message)

    def on_delete_button_clicked(self):
        """Определяет, у какого слова был нажат крестик, и запускает удаление"""
        button = self.sender()
        if button:
            french_word = button.property("word")
            
            reply = QMessageBox.question(
                self, 
                "Удаление слова", 
                f"Вы уверены, что хотите безвозвратно удалить слово <b>{french_word}</b>?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if database.delete_word(french_word):
                    audio_manager.delete_audio(french_word)
                    self.load_saved_data()
                    self.details_panel.clear()
                    self.rules_buttons_container.hide()
                    self.current_word = ""
                    self.statusBar().showMessage(f"Слово '{french_word}' успешно удалено.")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить слово из базы данных.")

    def keyPressEvent(self, event):
        """Перехватывает нажатие клавиш в главном окне"""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected_items = self.table.selectedItems()
            if selected_items:
                self.confirm_and_delete_word()
        else:
            super().keyPressEvent(event)

    def confirm_and_delete_word(self):
        """Запрашивает подтверждение и удаляет выбранное слово"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
            
        french_word = self.table.item(current_row, 0).text()
        
        reply = QMessageBox.question(
            self, 
            "Удаление слова", 
            f"Вы уверены, что хотите безвозвратно удалить слово <b>{french_word}</b>?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if database.delete_word(french_word):
                audio_manager.delete_audio(french_word)
                self.table.removeRow(current_row)
                
                if hasattr(self, 'details_panel'):
                    self.details_panel.clear()
                    self.rules_buttons_container.hide()
                    self.current_word = ""
                    
                self.statusBar().showMessage(f"Слово '{french_word}' успешно удалено.")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить слово из базы данных.")

    def load_saved_data(self):
        """Загружает слова из файла JSON (либо из активной папки) и выводит их в таблицу."""
        if self.active_folder:
            words = database.get_words_by_folder(self.active_folder)
        else:
            words = database.load_words()

        self.table.setRowCount(0)
        for word in words:
            fr = word.get("french", "")
            trans = word.get("transcription", "")
            ru = word.get("russian", "")
            if fr:
                audio_btn, delete_btn, folder_btn = self.add_row(fr, trans, ru)
                audio_btn.clicked.connect(lambda checked, w=fr: self.play_word_audio(w))
                delete_btn.clicked.connect(self.on_delete_button_clicked)
                folder_btn.clicked.connect(self.on_folder_button_clicked)

    def start_translation(self):
        """Запускает процесс перевода в фоновом режиме."""
        word = self.word_input.text().strip()
        if not word:
            return

        self.add_button.setEnabled(False)
        self.word_input.setEnabled(False)
        self.add_button.setText("Ищу...")

        self.worker = TranslationThread(word)
        self.worker.finished.connect(self.on_translation_success)
        self.worker.error.connect(self.on_translation_error)
        self.worker.start()

    def quick_add_word(self, word: str):
        """Метод вызывается при нажатии на всплывающий кружочек."""
        # Разворачиваем окно, если оно было скрыто в трее
        if self.isHidden():
            self.show_from_tray()
            
        # Вставляем слово в инпут и запускаем перевод
        self.word_input.setText(word)
        self.start_translation()

    def on_translation_success(self, result):
        """Срабатывает, когда API успешно вернул данные слова."""
        fr_word, transcription, ru_word, examples = result

        # Если сейчас открыта конкретная папка, новое слово сразу помещается в нее
        target_folders = [self.active_folder] if self.active_folder else None
        is_saved = database.save_word(fr_word, transcription, ru_word, examples, folders=target_folders)
        
        if is_saved:
            audio_btn, delete_btn, folder_btn = self.add_row(fr_word, transcription, ru_word)
            audio_btn.clicked.connect(lambda checked, w=fr_word: self.play_word_audio(w))
            delete_btn.clicked.connect(self.on_delete_button_clicked)
            folder_btn.clicked.connect(self.on_folder_button_clicked)
            self.render_details_html(fr_word, transcription, ru_word, examples)
            audio_manager.get_audio_path(fr_word)
        else:
            QMessageBox.information(self, "Внимание", f"Слово '{fr_word}' уже есть в вашем словаре!")

        self.reset_input_ui()

    def on_translation_error(self, error_message):
        QMessageBox.warning(self, "Ошибка поиска", error_message)
        self.reset_input_ui()

    def reset_input_ui(self):
        self.word_input.clear()
        self.word_input.setEnabled(True)
        self.add_button.setEnabled(True)
        self.add_button.setText("Добавить")
        self.word_input.setFocus()

    def open_review_mode(self):
        """Открывает диалог выбора источника слов (все / папка) и количества, затем запускает сессию повторения."""
        setup_dialog = ReviewSetupDialog(self)
        if setup_dialog.exec():
            dialog = ReviewDialog(setup_dialog.selected_count, setup_dialog.selected_folder, self)
            dialog.exec()
            self.load_saved_data()

    def show_word_details(self, item):
        """Находит кликнутое слово в базе данных и выводит детальную карточку."""
        self.rules_buttons_container.hide()

        row = item.row()
        french_word = self.table.item(row, 0).text()
        
        words = database.load_words()
        target_word = next((w for w in words if w.get("french") == french_word), None)
        
        if target_word:
            self.render_details_html(
                target_word.get("french", ""),
                target_word.get("transcription", ""),
                target_word.get("russian", ""),
                target_word.get("examples", [])
            )

    def render_details_html(self, word, transcription, translation, examples):
        """Генерирует HTML-разметку для боковой панели описания слова."""
        self.current_word = word

        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 10px;">
            <h1 style="color: #2c3e50; margin-bottom: 2px;">{word}</h1>
            <span style="color: #7f8c8d; font-size: 14px; font-style: italic;">{transcription}</span>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
            
            <h3 style="color: #2980b9; margin-bottom: 5px;">Значение / Перевод:</h3>
            <p style="font-size: 16px; color: #333; background-color: #f8f9fa; padding: 8px; border-left: 3px solid #2980b9;">
                {translation}
            </p>
            
            <h3 style="color: #27ae60; margin-top: 20px; margin-bottom: 5px;">Примеры употребления:</h3>
        """
        
        if examples:
            html += '<ul style="padding-left: 20px; color: #555;">'
            for ex in examples:
                html += f"""
                <li style="margin-bottom: 12px;">
                    <b style="color: #34495e;">{ex['fr']}</b><br>
                    <span style="color: #7f8c8d; font-size: 13px;">{ex['ru']}</span>
                </li>
                """
            html += '</ul>'
        else:
            html += '<p style="color: #95a5a6; font-style: italic;">Примеров для этого слова пока нет.</p>'
            
        html += "</div>"
        self.details_panel.setHtml(html)


if __name__ == "__main__":
    # Гарантируем, что относительные пути (dictionary.json, folders.json, audio_cache)
    # всегда указывают на папку с программой, независимо от того, как она была запущена —
    # вручную, ярлыком или автозагрузкой Windows (у которой рабочая директория может отличаться).
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # закрытие окна сворачивает в трей, а не завершает программу
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())