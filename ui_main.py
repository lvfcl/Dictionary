import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class DictionaryUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # 1. Настройки главного окна
        self.setWindowTitle("Французский Словарь v1.0")
        self.resize(750, 550)
        self.setMinimumSize(600, 400)
        
        # Главный контейнер (виджет-подложка)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный слой, куда будем складывать элементы сверху вниз
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)        # Отступы между элементами
        main_layout.setContentsMargins(20, 20, 20, 20) # Поля по краям окна

        # 2. Заголовок приложения
        self.title_label = QLabel("Мой Личный Словарь")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)

        # 3. Блок ввода нового слова (Горизонтальный слой)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Введите слово на русском или французском...")
        self.word_input.setFont(QFont("Arial", 12))
        self.word_input.setFixedHeight(40) # Делаем поле ввода чуть повыше и удобнее
        
        self.add_button = QPushButton("Добавить")
        self.add_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.add_button.setFixedHeight(40)
        self.add_button.setFixedWidth(120)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor) # Иконка руки при наведении

        input_layout.addWidget(self.word_input)
        input_layout.addWidget(self.add_button)
        main_layout.addLayout(input_layout)

        # 4. Таблица для отображения словаря
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Французский", "Транскрипция", "Русский"])
        self.table.setFont(QFont("Arial", 11))
        
        # Настройка внешнего вида таблицы
        self.table.setAlternatingRowColors(True) # Зебра-эффект (чередование цвета строк)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows) # Выделять строку целиком
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Запрещаем редактировать ячейки напрямую в таблице
        
        # Настройка шапки таблицы
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch) # Растягиваем колонки поровну
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        
        main_layout.addWidget(self.table)

        # 5. Применение стилей (CSS-подобный QSS)
        self.apply_styles()

    def apply_styles(self):
        """Метод для придания приложению современного вида"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            QLabel {
                color: #2B2D42;
            }
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding-left: 10px;
                background-color: #FFFFFF;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #4A90E2; /* Подсветка поля при клике */
            }
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #357ABD; /* Темнеет при наведении */
            }
            QPushButton:pressed {
                background-color: #2D689C; /* Еще темнее при клике */
            }
            QTableWidget {
                border: 1px solid #E0E0E0;
                gridline-color: #E0E0E0;
                background-color: #FFFFFF;
                alternate-background-color: #F1F5F9; /* Цвет четных строк */
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #E2E8F0;
                color: #4A5568;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #CBD5E1;
            }
        """)

    def add_row(self, french: str, transcription: str, russian: str):
        """Удобный метод для добавления новой строки в таблицу извне"""
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        
        # Создаем элементы ячеек
        item_fr = QTableWidgetItem(french)
        item_trans = QTableWidgetItem(transcription)
        item_ru = QTableWidgetItem(russian)
        
        # Выравниваем текст по центру
        item_fr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_trans.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_ru.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Вставляем в таблицу
        self.table.setItem(row_count, 0, item_fr)
        self.table.setItem(row_count, 1, item_trans)
        self.table.setItem(row_count, 2, item_ru)
        
        # Автоматически прокручиваем таблицу к новому слову
        self.table.scrollToItem(item_fr)


# Этот блок нужен ТОЛЬКО для проверки, как выглядит окно. 
# Когда мы сделаем main.py, этот кусок можно будет не запускать.
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = DictionaryUI()
    window.show()
    sys.exit(app.exec())

    