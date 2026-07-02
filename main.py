import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

from ui_main import DictionaryUI
import database
import api_worker

class TranslationThread(QThread):
    """
    Отдельный поток для работы с API.
    Нужен для того, чтобы во время запроса к интернету (который может занимать 1-2 секунды)
    интерфейс программы не зависал и не белел.
    """
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, word):
        super().__init__()
        self.word = word

    def run(self):
        try:
            result = api_worker.get_full_word_data(self.word)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Не удалось найти перевод или транскрипцию для этого слова.")
        except Exception as e:
            self.error.emit(f"Произошла ошибка при поиске: {e}")


class MainApp(DictionaryUI):
    def __init__(self):
        super().__init__()
        
        self.add_button.clicked.connect(self.start_translation)
        self.word_input.returnPressed.connect(self.start_translation)
        self.load_saved_data()

    def load_saved_data(self):
        """Загружает слова из файла JSON и выводит их в таблицу при запуске"""
        words = database.load_words()
        for word in words:
            self.add_row(word["french"], word["transcription"], word["russian"])

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
        fr_word, transcription, ru_word = result
        is_saved = database.save_word(fr_word, transcription, ru_word)
        
        if is_saved:
            self.add_row(fr_word, transcription, ru_word)
        else:
            QMessageBox.information(self, "Внимание", f"Слово '{fr_word}' уже есть в вашем словаре!")

        self.reset_input_ui()

    def on_translation_error(self, error_message):
        """Срабатывает, если что-то пошло не так (нет интернета, пустой ответ)"""
        QMessageBox.warning(self, "Ошибка поиска", error_message)
        self.reset_input_ui()

    def reset_input_ui(self):
        """Очищает поле ввода и активирует элементы интерфейса обратно"""
        self.word_input.clear()
        self.word_input.setEnabled(True)
        self.add_button.setEnabled(True)
        self.add_button.setText("Добавить")
        self.word_input.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    main_window = MainApp()
    main_window.show()
    
    sys.exit(app.exec())

    