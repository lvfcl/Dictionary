import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QLabel, QTextBrowser, QListWidget, QCheckBox,
                             QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class DictionaryUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Инициализация всех элементов интерфейса и стилей"""
        self.setWindowTitle("Французский Словарь v1.0")
        self.resize(1250, 600)
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

        self.hint_label = QLabel("Вы можете просто скопировать (Ctrl+C) любое слово в другом окне, и нажать на плюсик ➕ для быстрого добавления")
        self.hint_label.setFont(QFont("Arial", 10))
        self.hint_label.setStyleSheet("color: #7f8c8d; font-style: italic; margin-bottom: 5px;")
        main_layout.addWidget(self.hint_label)

        settings_row = QHBoxLayout()
        settings_row.setSpacing(15)

        self.autostart_checkbox = QCheckBox("Запускать при включении ПК")
        self.autostart_checkbox.setFont(QFont("Arial", 10))
        self.autostart_checkbox.setStyleSheet("color: #3d4e91;")
        self.autostart_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_row.addWidget(self.autostart_checkbox)

        self.background_mode_checkbox = QCheckBox("Работать в фоне после закрытия окна")
        self.background_mode_checkbox.setFont(QFont("Arial", 10))
        self.background_mode_checkbox.setStyleSheet("color: #3d4e91;")
        self.background_mode_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.background_mode_checkbox.setToolTip(
            "Если включено — закрытие окна сворачивает программу в трей, и она продолжает\n"
            "работать в фоне. Если выключено — закрытие окна полностью завершает программу."
        )
        settings_row.addWidget(self.background_mode_checkbox)

        settings_row.addStretch()

        self.rules_button = QPushButton("📖 Правила языка")
        self.rules_button.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.rules_button.setFixedHeight(32)
        self.rules_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rules_button.setToolTip("Открыть справочник по грамматике французского языка")
        settings_row.addWidget(self.rules_button)

        self.rules_replace_main_checkbox = QCheckBox("Правила в колонке слова")
        self.rules_replace_main_checkbox.setFont(QFont("Arial", 10))
        self.rules_replace_main_checkbox.setStyleSheet("color: #3d4e91;")
        self.rules_replace_main_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rules_replace_main_checkbox.setToolTip(
            "Если включено — по кнопке «Правила языка» текст правил появляется\n"
            "на месте колонки «подробно о слове» справа.\n"
            "Если выключено — правила открываются отдельным окном."
        )
        settings_row.addWidget(self.rules_replace_main_checkbox)

        main_layout.addLayout(settings_row)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(6)

        # --- Панель папок (категорий слов) ---
        folders_container = QWidget()
        folders_layout = QVBoxLayout(folders_container)
        folders_layout.setContentsMargins(0, 0, 0, 0)
        folders_layout.setSpacing(8)

        folders_title = QLabel("Папки")
        folders_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        folders_layout.addWidget(folders_title)

        self.folder_list = QListWidget()
        self.folder_list.setFont(QFont("Arial", 11))
        folders_layout.addWidget(self.folder_list)

        folder_buttons_row = QHBoxLayout()
        folder_buttons_row.setSpacing(6)

        self.new_folder_btn = QPushButton("➕")
        self.new_folder_btn.setToolTip("Создать новую папку")
        self.new_folder_btn.setFixedHeight(32)
        self.new_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.delete_folder_btn = QPushButton("🗑")
        self.delete_folder_btn.setToolTip("Удалить выбранную папку")
        self.delete_folder_btn.setFixedHeight(32)
        self.delete_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        folder_buttons_row.addWidget(self.new_folder_btn)
        folder_buttons_row.addWidget(self.delete_folder_btn)
        folders_layout.addLayout(folder_buttons_row)

        self.show_all_words_btn = QPushButton("Все слова")
        self.show_all_words_btn.setFixedHeight(32)
        self.show_all_words_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folders_layout.addWidget(self.show_all_words_btn)

        self.populate_folder_btn = QPushButton("Пополнить с ИИ")
        self.populate_folder_btn.setFixedHeight(36)
        self.populate_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.populate_folder_btn.setEnabled(False)
        folders_layout.addWidget(self.populate_folder_btn)

        folders_container.setMinimumWidth(140)
        content_splitter.addWidget(folders_container)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Французский", "Транскрипция", "Русский", "", "", ""])
        self.table.setFont(QFont("Arial", 11))
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)

        header = self.table.horizontalHeader()
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(20)

        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        content_splitter.addWidget(self.table)

        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(8)

        details_splitter = QSplitter(Qt.Orientation.Horizontal)
        details_splitter.setChildrenCollapsible(False)
        details_splitter.setHandleWidth(6)

        # Вертикальный столбец кнопок с названиями правил - показывается только
        # в режиме "Правила в колонке слова" (вместо колонки "подробно о слове").
        self.rules_buttons_container = QWidget()
        self.rules_buttons_container.setMinimumWidth(100)
        rules_buttons_layout = QVBoxLayout(self.rules_buttons_container)
        rules_buttons_layout.setContentsMargins(0, 0, 0, 0)
        rules_buttons_layout.setSpacing(6)

        self.rules_category_buttons = []
        for title in ("Артикли и род", "Множ. число", "Произношение"):
            rule_btn = QPushButton(title)
            rule_btn.setFont(QFont("Arial", 10))
            rule_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rule_btn.setCheckable(True)
            rule_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E2E8F0;
                    color: #4A5568;
                    padding: 8px 10px;
                    border: none;
                    border-radius: 6px;
                    text-align: left;
                }
                QPushButton:checked {
                    background-color: #4A90E2;
                    color: white;
                    font-weight: bold;
                }
            """)
            rules_buttons_layout.addWidget(rule_btn)
            self.rules_category_buttons.append(rule_btn)
        rules_buttons_layout.addStretch()

        self.rules_buttons_container.hide()
        details_splitter.addWidget(self.rules_buttons_container)

        self.details_panel = QTextBrowser()
        self.details_panel.setPlaceholderText("Нажмите на слово в таблице, чтобы увидеть подробную информацию с примерами от ИИ...")
        self.details_panel.setFont(QFont("Arial", 11))
        self.details_panel.setMinimumWidth(220)
        details_splitter.addWidget(self.details_panel)
        details_splitter.setStretchFactor(0, 0)
        details_splitter.setStretchFactor(1, 1)

        details_layout.addWidget(details_splitter)

        content_splitter.addWidget(details_container)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setStretchFactor(2, 1)
        content_splitter.setSizes([200, 700, 350])

        main_layout.addWidget(content_splitter, stretch=1)

        self.review_button = QPushButton("Учить слова")
        self.review_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.review_button.setFixedHeight(40)
        self.review_button.setCursor(Qt.CursorShape.PointingHandCursor)
        main_layout.addWidget(self.review_button)

        self.apply_styles()

    def apply_styles(self):
        """Метод для придания приложению современного вида с полной независимостью от тем Windows"""
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
                border: 2px solid #4A90E2;
            }
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
                alternate-background-color: #F1F5F9;
                border-radius: 6px;
                color: #333333;
                outline: none;
            }
            
            /* Обычные ячейки со словами */
            QTableWidget::item {
                color: #333333;
                padding: 5px;
                border-bottom: 1px solid #E0E0E0;
            }
                           
            /* Убираем подсветку при наведении (в т.ч. системную) */
            QTableWidget::item:hover {
                background-color: transparent;
                color: #333333;
            }

            /* Выделение выбранного слова сочным фиолетовым цветом */
            QTableWidget::item:selected {
                background-color: #9c23ed;
                color: #FFFFFF;
                border-bottom: 1px solid #9c23ed;
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
            
            /* Запрещаем нумерации строк выделяться и менять цвет при клике */
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
        """Вставляет данные в таблицу и генерирует кнопку-крестик в 4-й колонке"""
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
        
        audio_btn = AnimatedButton("🔊")
        audio_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        audio_btn.setFixedWidth(30)
        audio_btn.setFixedHeight(25)
        audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        audio_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
        """)
        audio_btn.setProperty("word", french)
        audio_btn.setToolTip("Прослушать произношение")
        self.table.setCellWidget(row_count, 3, audio_btn)

        delete_btn = AnimatedButton("❌")
        delete_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        delete_btn.setFixedWidth(30)
        delete_btn.setFixedHeight(25)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
        """)
        
        delete_btn.setProperty("word", french)
        
        self.table.setCellWidget(row_count, 4, delete_btn)

        folder_btn = AnimatedButton("📁")
        folder_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        folder_btn.setFixedWidth(30)
        folder_btn.setFixedHeight(25)
        folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 13px;
            }
        """)
        folder_btn.setProperty("word", french)
        folder_btn.setToolTip("Добавить слово в папку")
        self.table.setCellWidget(row_count, 5, folder_btn)

        self.table.scrollToItem(item_fr)
        
        return audio_btn, delete_btn, folder_btn
    

class AnimatedButton(QPushButton):
    """
    Кнопка с эффектом при наведении курсора.

    Раньше эффект делался через QPropertyAnimation по pos() — кнопка физически
    сдвигалась вверх на несколько пикселей. Но эта кнопка живет внутри ячейки
    таблицы (setCellWidget), а QTableWidget сам периодически переустанавливает
    геометрию своих ячеек (при прокрутке, изменении размеров и т.д.), не зная
    о нашей анимации. Из-за этого кнопки то "убегали" от курсора, то "проваливались"
    вниз — ручной сдвиг позиции и автоматическое управление геометрией со стороны
    таблицы конфликтовали друг с другом.

    Поэтому эффект наведения сделан только через стиль (фон при наведении),
    без изменения физического положения виджета — это не может конфликтовать
    с таблицей, так как geometry кнопки вообще не трогается.
    """
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._base_style = ""
        self._hover_style = ""

    def setStyleSheet(self, style: str):
        # Запоминаем стиль, заданный снаружи (например, "прозрачный фон, без рамки"),
        # чтобы при наведении добавить к нему подсветку, а не потерять исходный вид.
        self._base_style = style
        self._hover_style = style + "\nQPushButton { background-color: rgba(0, 0, 0, 25); border-radius: 4px; }"
        super().setStyleSheet(style)

    def enterEvent(self, event):
        super().setStyleSheet(self._hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().setStyleSheet(self._base_style)
        super().leaveEvent(event)



if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = DictionaryUI()
    window.show()
    sys.exit(app.exec())