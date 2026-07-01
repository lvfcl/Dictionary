import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal

# Импортируем наши собственные модули
from ui_main import DictionaryUI
import database
import api_worker

class TranslationThread(QThread):
    """
    Отдельный поток для работы с API.
    Нужен для того, чтобы во время запроса к интернету (который может занимать 1-2 секунды)
    интерфейс программы не зависал и не белел.
    """
    # Сигнал, который вернет результат перевода обратно в главное окно
    finished = pyqtSignal(tuple)
    # Сигнал на случай ошибки
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
        
        # 1. Привязываем события к кнопкам интерфейса
        self.add_button.clicked.connect(self.start_translation)
        self.word_input.returnPressed.connect(self.start_translation) # По нажатию Enter
        
        # 2. Загружаем уже существующие слова из базы данных
        self.load_saved_data()

    def load_saved_data(self):
        """Загружает слова из файла JSON и выводит их в таблицу при запуске"""
        words = database.load_words()
        for word in words:
            # Метод add_row мы предусмотрительно написали в ui_main.py
            self.add_row(word["french"], word["transcription"], word["russian"])

    def start_translation(self):
        """Запускает процесс перевода в фоновом режиме"""
        word = self.word_input.text().strip()
        if not word:
            return

        # Временно отключаем кнопку и поле ввода, чтобы пользователь не спамил кликами
        self.add_button.setEnabled(False)
        self.word_input.setEnabled(False)
        self.add_button.setText("Ищу...")

        # Создаем фоновый поток для запроса к API
        self.worker = TranslationThread(word)
        self.worker.finished.connect(self.on_translation_success)
        self.worker.error.connect(self.on_translation_error)
        
        # Запускаем поток
        self.worker.start()

    def on_translation_success(self, result):
        """Срабатывает, когда API успешно вернул данные слова"""
        fr_word, transcription, ru_word = result
        
        # Пробуем сохранить слово в базу данных (JSON)
        # Функция save_word сама проверит на дубликаты
        is_saved = database.save_word(fr_word, transcription, ru_word)
        
        if is_saved:
            # Если слово новое и успешно сохранено — добавляем строку в таблицу UI
            self.add_row(fr_word, transcription, ru_word)
        else:
            # Если слово уже было в базе
            QMessageBox.information(self, "Внимание", f"Слово '{fr_word}' уже есть в вашем словаре!")

        # Возвращаем интерфейс в рабочее состояние
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
        self.word_input.setFocus() # Возвращаем курсор в поле ввода


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Запускаем наше собранное приложение
    main_window = MainApp()
    main_window.show()
    
    sys.exit(app.exec())

    