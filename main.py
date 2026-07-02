import sys
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMessageBox, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextBrowser, QWidget)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

from ui_main import DictionaryUI
import database
import api_worker


class TranslationThread(QThread):
    """Отдельный поток для работы с API."""
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, word):
        super().__init__()
        self.word = word

    def run(self):
        try:
            result = api_worker.get_full_word_data(self.word)
            if result[0]:
                self.finished.emit(result)
            else:
                self.error.emit("Слово не найдено или ошибка перевода.")
        except Exception as e:
            self.error.emit(str(e))


class ReviewDialog(QDialog):
    """Окно для интервального повторения слов (Режим Anki)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Интервальное повторение (Anki)")
        self.resize(500, 400)
        
        all_words = database.load_words()
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        self.queue = [w for w in all_words if w.get("next_review", today_str) <= today_str]
        self.current_card = None
        
        self.init_ui()
        self.next_card()

    def init_ui(self):
        layout = QVBoxLayout()
        
        self.counter_label = QLabel(self)
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.counter_label)
        
        self.word_label = QLabel(self)
        self.word_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.word_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.word_label)
        
        self.answer_box = QWidget()
        answer_layout = QVBoxLayout(self.answer_box)
        
        self.trans_label = QLabel(self)
        self.trans_label.setFont(QFont("Arial", 14))
        self.trans_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trans_label.setStyleSheet("color: gray;")
        answer_layout.addWidget(self.trans_label)
        
        self.ru_label = QLabel(self)
        self.ru_label.setFont(QFont("Arial", 18, QFont.Weight.Medium))
        self.ru_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        answer_layout.addWidget(self.ru_label)
        
        self.examples_browser = QTextBrowser(self)
        self.examples_browser.setMaximumHeight(120)
        answer_layout.addWidget(self.examples_browser)
        
        layout.addWidget(self.answer_box)
        
        self.show_answer_btn = QPushButton("Показать перевод", self)
        self.show_answer_btn.setFont(QFont("Arial", 12))
        self.show_answer_btn.setFixedHeight(40)
        self.show_answer_btn.clicked.connect(self.show_answer)
        layout.addWidget(self.show_answer_btn)
        
        self.buttons_panel = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_panel)
        
        qualities = [("Забыл", 0, "#ff4d4d"), ("Сложно", 1, "#ff944d"), 
                     ("Хорошо", 2, "#33cc33"), ("Легко", 3, "#3399ff")]
                     
        for text, val, color in qualities:
            btn = QPushButton(text, self)
            btn.setFixedHeight(35)
            btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
            btn.clicked.connect(lambda checked, v=val: self.handle_score(v))
            buttons_layout.addWidget(btn)
            
        layout.addWidget(self.buttons_panel)
        self.setLayout(layout)

    def next_card(self):
        """Переходит к следующему слову в очереди"""
        if not self.queue:
            QMessageBox.information(self, "Готово!", "Отличная работа! На сегодня все слова повторены.")
            self.accept()
            return
            
        self.counter_label.setText(f"Осталось карточек: {len(self.queue)}")
        self.current_card = self.queue.pop(0)
        
        self.word_label.setText(self.current_card.get("french", ""))
        self.trans_label.setText(self.current_card.get("transcription", ""))
        self.ru_label.setText(self.current_card.get("russian", ""))
        
        examples_text = ""
        for ex in self.current_card.get("examples", []):
            examples_text += f"<b>FR:</b> {ex['fr']}<br><b>RU:</b> {ex['ru']}<br><br>"
        self.examples_browser.setHtml(examples_text if examples_text else "Примеров контекста нет.")
        
        self.answer_box.hide()
        self.buttons_panel.hide()
        self.show_answer_btn.show()

    def show_answer(self):
        """Открывает скрытую информацию (перевод и контекст)"""
        self.show_answer_btn.hide()
        self.answer_box.show()
        self.buttons_panel.show()

    def handle_score(self, quality):
        """Обрабатывает нажатие на кнопку градации сложности"""
        updated_card = database.update_card_review(self.current_card, quality)
        
        all_words = database.load_words()
        for i, word in enumerate(all_words):
            if word["french"] == updated_card["french"]:
                all_words[i] = updated_card
                break
                
        import json
        with open("dictionary.json", "w", encoding="utf-8") as f:
            json.dump(all_words, f, ensure_ascii=False, indent=4)
            
        if quality == 0:
            self.queue.append(updated_card)
            
        self.next_card()


class MainApp(DictionaryUI):
    def __init__(self):
        super().__init__()
        
        self.add_button.clicked.connect(self.start_translation)
        self.word_input.returnPressed.connect(self.start_translation)
        
        self.review_button = QPushButton("Учить слова", self)
        self.review_button.setFixedHeight(35)
        self.review_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.review_button.clicked.connect(self.open_review_mode)
        
        if self.centralWidget() and self.centralWidget().layout():
            self.centralWidget().layout().addWidget(self.review_button)
        
        self.load_saved_data()

    def load_saved_data(self):
        """Загружает слова из файла JSON и выводит их в таблицу при запуске"""
        words = database.load_words()
        if hasattr(self, 'table') and hasattr(self, 'add_row'):
            for word in words:
                fr = word.get("french", "")
                trans = word.get("transcription", "")
                ru = word.get("russian", "")
                if fr:
                    self.add_row(fr, trans, ru)

    def start_translation(self):
        """Запускает процесс перевода в фоновом режиме"""
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

    def on_translation_success(self, result):
        """Срабатывает, когда API успешно вернул данные слова"""
        fr_word, transcription, ru_word, examples = result
        
        is_saved = database.save_word(fr_word, transcription, ru_word, examples)
        
        if is_saved:
            self.add_row(fr_word, transcription, ru_word)
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
        """Открывает диалоговое окно режима заучивания"""
        dialog = ReviewDialog(self)
        dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    main_window = MainApp()
    main_window.show()
    
    sys.exit(app.exec())