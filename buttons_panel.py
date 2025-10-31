from PyQt6.QtWidgets import QScrollArea, QWidget, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent

class ButtonsPanel(QScrollArea):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setWidgetResizable(False)
        self.setStyleSheet("""
            border: none; 
            background: #252525;
        """)
        
        self.container = QWidget()
        self.buttons_layout = QGridLayout(self.container)
        self.buttons_layout.setSizeConstraint(QGridLayout.SizeConstraint.SetFixedSize)

        self.buttons_layout.setContentsMargins(10, 10, 10, 10)
        self.buttons_layout.setHorizontalSpacing(15)
        self.buttons_layout.setVerticalSpacing(5)
        
        # Разрешаем перетаскивание
        self.setAcceptDrops(True)
        self.container.setAcceptDrops(True)
        
        self.current_columns = 1
        self.max_rows = 9

        self.setWidget(self.container)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        # Обработка перетаскивания на саму панель (если нужно)
        event.ignore()  # Пусть обрабатывают отдельные кнопки

    def add_column(self):
        """Добавляет новый столбец в layout"""
        self.current_columns += 1
    
    def is_position_empty(self, row, col):
        """Проверяет, свободна ли указанная позиция в сетке"""
        return not self.buttons_layout.itemAtPosition(row, col)