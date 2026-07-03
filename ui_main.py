import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QTextBrowser)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class DictionaryUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Французский Словарь v1.0")
        self.resize(1050, 600)
        self.setMinimumSize(800, 450)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Введите слово на русском или французском...")
        self.word_input.setFont(QFont("Arial", 12))
        self.word_input.setFixedHeight(40)
        
        self.add_button = QPushButton("Добавить")
        self.add_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.add_button.setFixedHeight(40)
        self.add_button.setFixedWidth(120)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)

        input_layout.addWidget(self.word_input)
        input_layout.addWidget(self.add_button)
        main_layout.addLayout(input_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Французский", "Транскрипция", "Русский"])
        self.table.setFont(QFont("Arial", 11))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        content_layout.addWidget(self.table, stretch=2)

        self.details_panel = QTextBrowser()
        self.details_panel.setPlaceholderText("Нажмите на слово в таблице, чтобы увидеть подробную информацию с примерами контекста...")
        self.details_panel.setFont(QFont("Arial", 11))
        self.details_panel.setMinimumWidth(320)
        content_layout.addWidget(self.details_panel, stretch=1)

        main_layout.addLayout(content_layout)

        self.review_button = QPushButton("Учить слова")
        self.review_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.review_button.setFixedHeight(40)
        self.review_button.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.review_button)

        self.apply_styles()

    def apply_styles(self):
        """Метод для придания приложению современного вида с полной независимостью от тем Windows"""
        self.setStyleSheet("""
            /* Главное окно приложения */
            QMainWindow {
                background-color: #F8F9FA;
            }
            
            /* Все стандартные текстовые подписи */
            QLabel {
                color: #2B2D42;
            }
            
            /* Поле ввода слова */
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding-left: 10px;
                background-color: #FFFFFF;
                color: #333333;
            }
            /* Подсветка поля ввода при фокусе */
            QLineEdit:focus {
                border: 2px solid #4A90E2;
            }
            
            /* Все стандартные кнопки (например, "Добавить") */
            QPushButton {
                background-color: #4A90E2;
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2D689C;
            }
            
            /* Стили для зеленой нижней кнопки Anki ("Учить слова") */
            QPushButton#review_btn_style {
                background-color: #2ECC71;
            }
            QPushButton#review_btn_style:hover {
                background-color: #27AE60;
            }
            QPushButton#review_btn_style:pressed {
                background-color: #1E8449;
            }
            
            /* Корпус таблицы */
            QTableWidget {
                border: 1px solid #E0E0E0;
                gridline-color: #E0E0E0;
                background-color: #FFFFFF;
                alternate-background-color: #F1F5F9; /* Цвет четных строк */
                border-radius: 6px;
                color: #333333;
            }
            
            /* Обычные ячейки со словами */
            QTableWidget::item {
                color: #333333;
                padding: 5px;
            }
            /* Эффект наведения мыши на слово */
            QTableWidget::item:hover {
                background-color: #E2E8F0;
                color: #000000;
            }
            /* Выделение выбранного слова сочным фиолетовым цветом */
            QTableWidget::item:selected {
                background-color: #9c23ed;
                color: #FFFFFF;
            }
            
            /* Шапка таблицы (Французский, Транскрипция, Русский) */
            QHeaderView::section:horizontal {
                background-color: #E2E8F0;
                color: #4A5568;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #CBD5E1;
            }
            
            /* Нумерация строк (Левая колонка с цифрами) */
            QHeaderView::section:vertical {
                background-color: #E2E8F0;
                color: #4A5568;
                padding: 5px;
                border: none;
                border-right: 2px solid #CBD5E1;
                text-align: center;
            }
            
            /* КРИТИЧНО: Запрещаем нумерации строк выделяться и менять цвет при клике */
            QHeaderView::section:vertical:selected, 
            QHeaderView::section:vertical:checked,
            QHeaderView::section:vertical:disabled {
                background-color: #E2E8F0;
                color: #4A5568;
            }
            
            /* Верхний левый пустой угол таблицы (над номерами строк) */
            QTableCornerButton::section {
                background-color: #E2E8F0;
                border: none;
                border-bottom: 2px solid #CBD5E1;
                border-right: 2px solid #CBD5E1;
            }
            
            /* Правая HTML панель (Карточка детальной информации) */
            QTextBrowser {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #333333;
            }
        """)
        self.review_button.setObjectName("review_btn_style")

    def add_row(self, french: str, transcription: str, russian: str):
        """Удобный метод для добавления новой строки в таблицу извне"""
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        
        item_fr = QTableWidgetItem(french)
        item_trans = QTableWidgetItem(transcription)
        item_ru = QTableWidgetItem(russian)
        
        item_fr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_trans.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_ru.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.table.setItem(row_count, 0, item_fr)
        self.table.setItem(row_count, 1, item_trans)
        self.table.setItem(row_count, 2, item_ru)
        
        self.table.scrollToItem(item_fr)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = DictionaryUI()
    window.show()
    sys.exit(app.exec())