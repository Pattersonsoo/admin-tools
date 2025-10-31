from PyQt6.QtWidgets import QPushButton, QApplication
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QMouseEvent, QDrag

class DraggableButton(QPushButton):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.parent = parent
        self.setMouseTracking(True)
        
        self.drag_start_position = None
        self.current_width = 120
        self.is_chat_command = getattr(parent, 'is_chat_commands', False)
        
        self.update_style()
        self.setAcceptDrops(True)
        
        # Определяем тип родителя и получаем соответствующую ширину
        if hasattr(parent, 'settings_panel') and hasattr(parent.settings_panel, 'width_slider'):
            # Основной редактор кнопок (Ответы)
            self.current_width = parent.settings_panel.width_slider.value()
            self.is_chat_command = False
        elif hasattr(parent, 'parent') and hasattr(parent.parent, 'settings_panel'):
            # ChatCommandsPanel
            self.current_width = parent.parent.settings_panel.width_slider.value()
            self.is_chat_command = False
        else:
            # ChatCommandsPanel напрямую
            self.current_width = 120
            self.is_chat_command = True

    def update_style(self):
        """Обновляет стиль кнопки в зависимости от типа"""
        button_height = 25  # Уменьшенная высота кнопок
        
        if self.is_chat_command:
            # Стиль для чат-команд (синий)
            self.normal_style = f"""
                QPushButton {{
                    background: #2A4B7C;
                    color: white;
                    border: 1px solid #3A5B8C;
                    border-radius: 3px;
                    padding: 2px;
                    min-width: {self.current_width}px;
                    max-width: {self.current_width}px;
                    min-height: {button_height}px;
                    max-height: {button_height}px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: #3A5B9C;
                    border: 1px solid #4A6BAC;
                }}
            """
            self.drag_over_style = f"""
                QPushButton {{
                    background: #555;
                    color: white;
                    border: 2px solid #FFA500;
                    border-radius: 3px;
                    padding: 2px;
                    min-width: {self.current_width}px;
                    max-width: {self.current_width}px;
                    min-height: {button_height}px;
                    max-height: {button_height}px;
                    font-size: 11px;
                }}
            """
        else:
            # Стиль для обычных кнопок (темно-серый)
            self.normal_style = f"""
                QPushButton {{
                    background: #333;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 2px;
                    min-width: {self.current_width}px;
                    max-width: {self.current_width}px;
                    min-height: {button_height}px;
                    max-height: {button_height}px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: #3A3A3A;
                    border: 1px solid #555;
                }}
            """
            self.drag_over_style = f"""
                QPushButton {{
                    background: #555;
                    color: white;
                    border: 2px solid #FFA500;
                    border-radius: 3px;
                    padding: 2px;
                    min-width: {self.current_width}px;
                    max-width: {self.current_width}px;
                    min-height: {button_height}px;
                    max-height: {button_height}px;
                    font-size: 11px;
                }}
            """
        
        self.setStyleSheet(self.normal_style)

    def update_width(self, new_width):
        """Обновляет ширину кнопки"""
        self.current_width = new_width
        self.update_style()
        self.setFixedWidth(new_width)
        self.setFixedHeight(25)  # Устанавливаем фиксированную высоту

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.MouseButton.LeftButton) or not self.drag_start_position:
            return
            
        manhattan_length = (event.pos() - self.drag_start_position).manhattanLength()
        if manhattan_length < 10:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.text())
        mime_data.setData("application/x-button", self.text().encode())
        drag.setMimeData(mime_data)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        result = drag.exec(Qt.DropAction.MoveAction)
        
        self.drag_start_position = None
        self.restore_style()

    def dragEnterEvent(self, event):
        if (event.mimeData().hasText() and 
            event.mimeData().text() != self.text()):
            event.acceptProposedAction()
            self.setStyleSheet(self.drag_over_style)

    def dragLeaveEvent(self, event):
        self.restore_style()
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            source_text = event.mimeData().text()
            target_text = self.text()
            
            if (source_text != target_text and 
                hasattr(self.parent, 'button_data') and 
                source_text in self.parent.button_data and
                hasattr(self.parent, 'swap_buttons')):
                
                self.parent.swap_buttons(source_text, target_text)
            
        self.restore_style()
        event.acceptProposedAction()

    def restore_style(self):
        """Восстанавливает стандартный стиль кнопки"""
        self.setStyleSheet(self.normal_style)

    def update_width(self, new_width):
        """Обновляет ширину кнопки"""
        self.current_width = new_width
        self.update_style()
        self.setFixedWidth(new_width)