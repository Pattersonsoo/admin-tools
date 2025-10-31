from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel, 
                            QLineEdit, QTextEdit, QSlider, QHBoxLayout,
                            QPushButton)
from PyQt6.QtCore import Qt
from .draggable_button import DraggableButton

class SettingsPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        self.setFixedWidth(300)
        self.setStyleSheet("""
            background-color: #1E1E1E;
            padding: 0;
            margin: 0;
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # Группа настроек кнопки
        settings_group = QGroupBox("Настройка кнопки")
        settings_group.setStyleSheet("""
            QGroupBox {
                color: #FFA500;
                font-size: 14px;
                border: 1px solid #333;
                border-radius: 3px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        
        group_layout = QVBoxLayout(settings_group)
        group_layout.setContentsMargins(5, 10, 5, 5)
        group_layout.setSpacing(8)

        # Поля ввода
        group_layout.addWidget(QLabel("Название кнопки:"))
        self.btn_name_edit = QLineEdit()
        self.btn_name_edit.setStyleSheet("""
            QLineEdit {
                background: #353535;
                border: 1px solid #444;
                color: white;
                padding: 8px;
                border-radius: 3px;
            }
        """)
        group_layout.addWidget(self.btn_name_edit)

        group_layout.addWidget(QLabel("Описание кнопки:"))
        self.btn_desc_edit = QTextEdit()
        self.btn_desc_edit.setStyleSheet("""
            QTextEdit {
                background: #353535;
                border: 1px solid #444;
                color: white;
                padding: 8px;
                border-radius: 3px;
            }
        """)
        self.btn_desc_edit.setMaximumHeight(100)
        group_layout.addWidget(self.btn_desc_edit)

        # Слайдер ширины
        width_layout = QVBoxLayout()
        width_layout.addWidget(QLabel("Ширина кнопок:"))
        
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setRange(90, 300)
        self.width_slider.setValue(120)
        self.width_slider.setTickInterval(10)
        self.width_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.width_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #353535;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFA500;
                width: 12px;
                height: 12px;
                margin: -3px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #FFA500;
                border-radius: 3px;
            }
        """)
        self.width_slider.valueChanged.connect(self.parent.update_all_buttons_width)
        
        self.width_value = QLabel("120 px")
        self.width_value.setStyleSheet("color: #FFA500; font-weight: bold;")
        self.width_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        width_layout.addWidget(self.width_slider)
        width_layout.addWidget(self.width_value)
        group_layout.addLayout(width_layout)

        # Первый ряд кнопок (Добавить и Удалить)
        first_row = QHBoxLayout()
        first_row.setSpacing(5)

        self.add_btn = QPushButton("Добавить")
        self.add_btn.setFixedHeight(30)
        self.add_btn.setStyleSheet(self.get_button_style())
        self.add_btn.clicked.connect(self.parent.add_new_button)
        first_row.addWidget(self.add_btn)

        self.del_btn = QPushButton("Удалить")
        self.del_btn.setFixedHeight(30)
        self.del_btn.setStyleSheet(self.get_button_style())
        self.del_btn.clicked.connect(self.parent.delete_current_button)
        first_row.addWidget(self.del_btn)

        group_layout.addLayout(first_row)

        # Вторая строка (Расширенные настройки)
        second_row = QHBoxLayout()
        second_row.setSpacing(5)

        self.advanced_btn = QPushButton("Расширенные настройки")
        self.advanced_btn.setFixedHeight(30)
        self.advanced_btn.setStyleSheet(self.get_button_style())
        self.advanced_btn.clicked.connect(self.parent.open_advanced_settings)
        second_row.addWidget(self.advanced_btn)

        group_layout.addLayout(second_row)

        # Третья строка (Сохранить)
        third_row = QHBoxLayout()
        third_row.setSpacing(5)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setFixedHeight(30)
        self.save_btn.setStyleSheet(self.get_button_style())
        self.save_btn.clicked.connect(self.parent.save_button)
        third_row.addWidget(self.save_btn)

        group_layout.addLayout(third_row)

        main_layout.addWidget(settings_group)
        main_layout.addStretch()

        self.width_slider.valueChanged.connect(self.update_button_widths)

    def get_button_style(self):
        return """
            QPushButton {
                background: #333333;
                color: white;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 0px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3A3A3A;
                border: 1px solid #555;
            }
        """
    
    def update_button_widths(self, value):
        self.parent.button_width = value
        self.width_value.setText(f"{value} px")
        self.parent.save_width_to_file()
        
        # Получаем button_data из родительского окна (ButtonEditor)
        if hasattr(self.parent, 'button_data'):
            for name, data in self.parent.button_data.items():
                btn = data["widget"]
                
                if isinstance(btn, DraggableButton):
                    btn.current_width = value
                    btn.setFixedWidth(value)
                    btn.restore_style()
                    
                    data["width"] = value
            
            self.parent.force_update_executor()
            if hasattr(self.parent, 'executor_window') and self.parent.executor_window:
                self.parent.executor_window.update_buttons_width(value)
        
        self.parent.save_width_to_file()
        if hasattr(self.parent, 'buttons_panel'):
            self.parent.buttons_panel.container.updateGeometry()