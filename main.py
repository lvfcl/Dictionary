import os
import sys
import json
from datetime import datetime
import random 

from PyQt6.QtWidgets import QInputDialog
from PyQt6.QtWidgets import (QApplication, QMessageBox, QDialog, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextBrowser, QWidget)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QUrl  # <-- Добавлен QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput  # <-- КРИТИЧНО ДЛЯ ЗВУКА

from gtts import gTTS
from ui_main import DictionaryUI
import database
import api_worker


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


class ReviewDialog(QDialog):
    """Диалоговое окно для интервального повторения слов (Режим Anki)"""
    def __init__(self, limit_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Интервальное повторение (Anki)")
        self.resize(500, 400)
        
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
        
        # Подключаем сигналы к кнопкам и таблице
        self.add_button.clicked.connect(self.start_translation)
        self.word_input.returnPressed.connect(self.start_translation)
        self.review_button.clicked.connect(self.open_review_mode)
        self.table.itemClicked.connect(self.show_word_details)
        
        # Перехватываем ссылки-динамики внутри HTML панели
        self.details_panel.setOpenLinks(False)
        self.details_panel.anchorClicked.connect(self.handle_html_click)
        
        # Инициализируем нативный плеер PyQt6 для звука
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        self.load_saved_data()

    def load_saved_data(self):
        """Загружает слова из файла JSON и выводит их в таблицу при запуске."""
        words = database.load_words()
        self.table.setRowCount(0)
        for word in words:
            fr = word.get("french", "")
            trans = word.get("transcription", "")
            ru = word.get("russian", "")
            if fr:
                btn = self.add_row(fr, trans, ru)
                btn.clicked.connect(self.on_delete_button_clicked)

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

    def on_translation_success(self, result):
        """Срабатывает, когда API успешно вернул данные слова."""
        fr_word, transcription, ru_word, examples = result
        is_saved = database.save_word(fr_word, transcription, ru_word, examples)
        
        if is_saved:
            btn = self.add_row(fr_word, transcription, ru_word)
            btn.clicked.connect(self.on_delete_button_clicked)
            self.render_details_html(fr_word, transcription, ru_word, examples)
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

    def show_word_details(self, item):
        """Находит слово в базе и рендерит HTML карточку со звуком"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return
        french_word = self.table.item(current_row, 0).text()
        
        words = database.load_words()
        for word in words:
            if word.get("french", "").lower() == french_word.lower():
                self.render_details_html(
                    word.get("french", ""),
                    word.get("transcription", ""),
                    word.get("russian", ""),
                    word.get("examples", [])
                )
                break

    def render_details_html(self, word, transcription, translation, examples):
        """Генерирует HTML-разметку для боковой панели с кнопкой аудио-динамика."""
        clean_word = word.replace("le ", "").replace("la ", "").replace("l'", "").strip()
        
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 10px;">
            <table style="width: 100%; border: none; margin-bottom: 2px;">
                <tr>
                    <td style="vertical-align: middle;">
                        <h1 style="color: #2c3e50; margin: 0; padding: 0;">{word}</h1>
                    </td>
                    <td style="text-align: right; vertical-align: middle; width: 40px;">
                        <a href="play_audio:{clean_word}" style="text-decoration: none; font-size: 24px; color: #4A90E2;">🔊</a>
                    </td>
                </tr>
            </table>
            
            <span style="color: #7f8c8d; font-size: 14px; font-style: italic;">{transcription}</span>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
            
            <h3 style="color: #2980b9; margin-bottom: 5px;">Значение / Перевод:</h3>
            <p style="font-size: 16px; color: #333; background-color: #f8f9fa; padding: 8px; border-left: 3px solid #2980b9; margin-top: 0;">
                {translation}
            </p>
            
            <h3 style="color: #27ae60; margin-top: 20px; margin-bottom: 5px;">Примеры употребления:</h3>
        """
        
        if examples:
            html += '<ul style="padding-left: 20px; color: #555; margin-top: 0;">'
            for ex in examples:
                html += f"""
                <li style="margin-bottom: 12px;">
                    <b style="color: #34495e;">{ex['fr']}</b> 
                    <a href="play_audio:{ex['fr']}" style="text-decoration: none; font-size: 14px; color: #4A90E2;">🔊</a><br>
                    <span style="color: #7f8c8d; font-size: 13px;">{ex['ru']}</span>
                </li>
                """
            html += '</ul>'
        else:
            html += '<p style="color: #95a5a6; font-style: italic;">Примеров для этого слова пока нет.</p>'
            
        html += "</div>"
        self.details_panel.setHtml(html)

    def handle_html_click(self, url):
        """Перехватывает клик по динамику 🔊 в HTML панели и запускает озвучку"""
        url_str = url.toString()
        if url_str.startswith("play_audio:"):
            text_to_speak = url_str.replace("play_audio:", "")
            self.speak_french(text_to_speak)

    def speak_french(self, text):
        """Генерирует аудио через gTTS и воспроизводит его средствами PyQt6"""
        try:
            text = text.strip()
            # Чтобы избежать блокировки одного и того же файла, используем случайный ID в названии
            filename = f"tts_{random.randint(1000, 9999)}.mp3"
            
            # Останавливаем плеер перед загрузкой нового файла
            self.player.stop()
            
            # Генерируем аудио с французским произношением
            tts = gTTS(text=text, lang='fr', slow=False)
            tts.save(filename)
            
            # Воспроизводим полученный файл встроенным плеером PyQt6
            file_url = QUrl.fromLocalFile(os.path.abspath(filename))
            self.player.setSource(file_url)
            self.player.play()
            
            # Старые временные файлы можно будет почистить при закрытии приложения,
            # сейчас главное, что они уникальны и не блокируют друг друга
        except Exception as e:
            print(f"Ошибка воспроизведения звука: {e}")

    def on_delete_button_clicked(self):
        button = self.sender()
        if button:
            french_word = button.property("word")
            reply = QMessageBox.question(
                self, "Удаление слова", 
                f"Вы уверены, что хотите безвозвратно удалить слово <b>{french_word}</b>?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if database.delete_word(french_word):
                    self.load_saved_data()
                    self.details_panel.clear()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить слово из базы данных.")

    def open_review_mode(self):
        """Запрашивает количество карточек по аналогии с Anki и запускает повторение."""
        all_words = database.load_words()
        today_str = datetime.now().strftime("%Y-%m-%d")
        due_count = len([w for w in all_words if w.get("next_review", today_str) <= today_str])
        
        if due_count == 0:
            QMessageBox.information(self, "Готово!", "На сегодня нет слов для повторения. Отдыхайте!")
            return

        limit, ok = QInputDialog.getInt(
            self, "Размер колоды", 
            f"Доступно карточек для повторения: {due_count}\nСколько карточек взять в колоду?", 
            value=min(20, due_count), min=1, max=due_count
        )
        
        if ok:
            dialog = ReviewDialog(limit, self)
            dialog.exec()
            self.load_saved_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())