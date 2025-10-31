from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QDialog, QGroupBox, QSpinBox, QCheckBox, QTextEdit, QTabWidget, QLineEdit, QSlider
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox, QPushButton, QApplication, QVBoxLayout, QLabel, QScrollArea

from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QObject, QEvent, QTimer, QMimeData
from PyQt6.QtCore import QParallelAnimationGroup
from PyQt6.QtGui import QGuiApplication, QDrag

from .settings_panel import SettingsPanel
from .buttons_panel import ButtonsPanel
from .styles import set_dark_theme
from .draggable_button import DraggableButton
from .button_executor import ButtonExecutor

import json
import os
import sys

import pyautogui
import time
import keyboard
from pathlib import Path
import win32gui
import win32process
import psutil
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='button_executor.log'
)

def get_base_path():
    """Возвращает правильный базовый путь для всех режимов работы"""
    if getattr(sys, 'frozen', False):
        # Режим EXE - берем папку, где лежит исполняемый файл
        return os.path.dirname(sys.executable)
    else:
        # Режим разработки - берем папку проекта (ATools)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class BasePanel(QWidget):
    """Базовый класс для панелей Ответы и Чат команды"""
    
    def __init__(self, parent, is_chat_commands=False):
        super().__init__(parent)
        self.parent = parent
        self.is_chat_commands = is_chat_commands
        self.supports_advanced_settings = not is_chat_commands
        self.base_path = get_base_path()
        self.settings_dir = os.path.join(self.base_path, "scripts", "settings")
        os.makedirs(self.settings_dir, exist_ok=True)
        
        # Определяем файл конфигурации в зависимости от типа панели
        if is_chat_commands:
            self.config_file = os.path.join(self.settings_dir, "chat_commands.json")
            self.panel_name = "Чат команды"
            self.button_style_color = "#2A4B7C"
        else:
            self.config_file = os.path.join(self.settings_dir, "button_config.json")
            self.panel_name = "Ответы"
            self.button_style_color = "#333333"
            
        self.button_data = {}
        self.advanced_settings = {}
        self.current_button = None
        
        # Настройки размеров по умолчанию
        self.button_width = 120
        self.button_height = 40
        self.row_spacing = 5
        
        self.setup_ui()
        self.load_buttons()
        self.load_size_settings()
        
        if not self.button_data:
            self.load_default_buttons()

    def get_button_width(self):
        """Возвращает ширину для кнопок"""
        return self.button_width

    def get_button_height(self):
        """Возвращает высоту для кнопок"""
        return self.button_height

    def setup_ui(self):
        """Настройка интерфейса панели"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Панель настроек
        self.settings_panel = BaseSettingsPanel(self)
        
        # Панель кнопок
        self.buttons_panel = ButtonsPanel(self)
        
        main_layout.addWidget(self.settings_panel)
        main_layout.addWidget(self.buttons_panel)

    def load_default_buttons(self):
        """Загружает стандартные кнопки"""
        if self.is_chat_commands:
            default_buttons = [
                ("/report", "Открыть меню репортов"),
                ("/admins", "Список администраторов онлайн"),
                ("/help", "Помощь по командам"),
                ("/rules", "Правила сервера"),
                ("/time", "Текущее игровое время"),
                ("/weather", "Текущая погода"),
                ("/stats", "Статистика игрока"),
                ("/fraction", "Информация о фракции"),
                ("/house", "Управление домом"),
                ("/business", "Управление бизнесом"),
                ("/car", "Управление транспортом"),
                ("/phone", "Открыть телефон"),
                ("/inventory", "Открыть инвентарь"),
                ("/skills", "Навыки персонажа"),
                ("/settings", "Настройки игры"),
                ("/bugreport", "Сообщить о баге"),
                ("/donate", "Информация о донате"),
                ("/discord", "Ссылка на Discord"),
                ("/forum", "Ссылка на форум"),
                ("/youtube", "Наш YouTube канал")
            ]
        else:
            default_buttons = [
                ("Наказания", "Меню выдачи наказаний"),
                ("Репорты", "Просмотр репортов игроков"),
                ("Телепорты", "Управление телепортами"),
                ("Настройка кнопки", "Настройка параметров кнопки"),
                ("Лечу", "Телепортироваться к игроку"),
                ("Узнайте сами", "Описание отсутствует"),
                ("Нет миникарты", "Исправить проблему с миникартой"),
                ("Пиши на форум", "Ссылка на форум"),
                ("Вторая машина", "Доступ к второй машине"),
                ("Фикс микрофона", "Исправить проблемы с микрофоном"),
            ]
        
        for name, desc in default_buttons:
            self.add_button(name, desc)

    def add_button(self, name, description="", position=None):
        """Добавляет новую кнопку"""
        if not isinstance(name, str) or not name:
            logging.error(f"Ошибка: некорректное имя кнопки {type(name)}: {name}")
            return
            
        if name in self.button_data:
            return
            
        if position is None:
            position = self.find_free_grid_position()

        while self.buttons_panel.buttons_layout.itemAtPosition(*position):
            position = self.find_free_grid_position()

        try:
            btn = DraggableButton(name, self)
            btn.current_width = self.button_width
            btn.current_height = self.button_height
            btn.is_chat_command = self.is_chat_commands
            btn.setFixedSize(self.button_width, self.button_height)
            btn.update_style()
            
            btn.clicked.connect(lambda _, n=name: self.load_button_settings(n))
            
            self.buttons_panel.buttons_layout.addWidget(btn, *position)
            self.button_data[name] = {
                "description": description,
                "width": self.button_width,
                "height": self.button_height,
                "widget": btn,
                "position": position
            }
            
            self.save_buttons()
        except Exception as e:
            logging.error(f"Ошибка создания кнопки '{name}': {e}")

    def find_free_grid_position(self):
        """Находит свободную позицию в сетке"""
        max_rows = self.buttons_panel.max_rows
        current_columns = self.buttons_panel.current_columns
        
        for col in range(current_columns):
            for row in range(max_rows):
                if not self.buttons_panel.buttons_layout.itemAtPosition(row, col):
                    return (row, col)
        
        self.buttons_panel.add_column()
        return (0, current_columns)

    def load_button_settings(self, button_name):
        """Загружает настройки выбранной кнопки"""
        self.current_button = button_name
        data = self.button_data.get(button_name, {})
        self.settings_panel.btn_name_edit.setText(button_name)
        self.settings_panel.btn_desc_edit.setPlainText(data.get("description", ""))
        
        # Устанавливаем значения слайдеров
        if hasattr(self.settings_panel, 'width_slider'):
            self.settings_panel.width_slider.setValue(data.get("width", self.button_width))
            self.settings_panel.width_value.setText(f"{data.get('width', self.button_width)} px")
        
        if hasattr(self.settings_panel, 'height_slider'):
            self.settings_panel.height_slider.setValue(data.get("height", self.button_height))
            self.settings_panel.height_value.setText(f"{data.get('height', self.button_height)} px")

    def add_new_button(self):
        """Добавляет новую кнопку из полей ввода"""
        name = self.settings_panel.btn_name_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название кнопки")
            return
            
        if name in self.button_data:
            reply = QMessageBox.question(
                self, "Кнопка существует",
                f"Кнопка '{name}' уже существует. Обновить её?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_button()
            return
        
        description = self.settings_panel.btn_desc_edit.toPlainText().strip()
        self.add_button(name, description)
        self.current_button = name
        self.save_buttons()

    def delete_current_button(self):
        """Удаляет текущую кнопку с реорганизацией"""
        if not self.current_button:
            QMessageBox.warning(self, "Ошибка", "Выберите кнопку для удаления")
            return
            
        if self.current_button not in self.button_data:
            self.current_button = None
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение", 
            f"Удалить кнопку '{self.current_button}'?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем кнопку
            self.button_data[self.current_button]['widget'].deleteLater()
            del self.button_data[self.current_button]
            
            # Реорганизуем оставшиеся кнопки
            self.reorganize_buttons()
            
            self.current_button = None
            self.settings_panel.btn_name_edit.clear()
            self.settings_panel.btn_desc_edit.clear()
            self.save_buttons()

    def save_button(self):
        """Сохраняет изменения кнопки"""
        if not self.current_button:
            QMessageBox.warning(self, "Ошибка", "Выберите кнопку для сохранения")
            return
            
        name = self.settings_panel.btn_name_edit.text().strip()
        description = self.settings_panel.btn_desc_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название кнопки")
            return
            
        # Получаем значения слайдеров
        width = self.button_width
        height = self.button_height
        
        if hasattr(self.settings_panel, 'width_slider'):
            width = self.settings_panel.width_slider.value()
        if hasattr(self.settings_panel, 'height_slider'):
            height = self.settings_panel.height_slider.value()
        
        if self.current_button != name:
            if name in self.button_data:
                QMessageBox.warning(self, "Ошибка", "Кнопка с таким именем уже существует")
                return
                
            data = self.button_data.pop(self.current_button)
            btn = data["widget"]
            btn.setText(name)
            
            self.button_data[name] = data
            self.current_button = name
        
        self.button_data[name].update({
            "description": description,
            "width": width,
            "height": height
        })
        
        # Обновляем размеры кнопки
        if name in self.button_data:
            btn = self.button_data[name]["widget"]
            btn.current_width = width
            btn.current_height = height
            btn.setFixedSize(width, height)
            btn.update_style()
        
        QMessageBox.information(self, "Сохранено", "Настройки кнопки сохранены")
        self.save_buttons()

    def reorganize_buttons(self):
        """Перераспределяет кнопки в сетке"""
        # Сортируем кнопки сначала по столбцам, затем по строкам
        sorted_buttons = sorted(self.button_data.items(),
                            key=lambda x: (x[1]['position'][1], x[1]['position'][0]))
        
        # Очищаем layout
        for i in reversed(range(self.buttons_panel.buttons_layout.count())): 
            widget = self.buttons_panel.buttons_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Перераспределяем кнопки
        self.buttons_panel.current_columns = 1
        max_rows = self.buttons_panel.max_rows
        
        for index, (name, data) in enumerate(sorted_buttons):
            row = index % max_rows
            col = index // max_rows
            
            if col >= self.buttons_panel.current_columns:
                self.buttons_panel.current_columns = col + 1
            
            # Обновляем позицию в данных
            data['position'] = (row, col)
            self.buttons_panel.buttons_layout.addWidget(data['widget'], row, col)
        
        self.save_buttons()

    def swap_buttons(self, source_text, target_text):
        """Обменивает позиции двух кнопок"""
        if not isinstance(source_text, str) or not source_text:
            logging.error(f"Ошибка: source_text должен быть непустой строкой, получен {type(source_text)}: {source_text}")
            return
            
        if not isinstance(target_text, str) or not target_text:
            logging.error(f"Ошибка: target_text должен быть непустой строкой, получен {type(target_text)}: {target_text}")
            return
        
        if source_text == target_text:
            return
            
        if source_text not in self.button_data or target_text not in self.button_data:
            return
            
        # Получаем данные кнопок
        source_data = self.button_data[source_text]
        target_data = self.button_data[target_text]
        
        # Сохраняем текущие позиции
        source_pos = source_data["position"]
        target_pos = target_data["position"]
        
        # Меняем позиции в данных
        source_data["position"] = target_pos
        target_data["position"] = source_pos
        
        # Полностью перестраиваем layout
        self.rebuild_buttons_layout()

    def rebuild_buttons_layout(self):
        """Полностью перестраивает layout кнопок"""
        # Очищаем layout
        for i in reversed(range(self.buttons_panel.buttons_layout.count())): 
            widget = self.buttons_panel.buttons_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Добавляем кнопки обратно в новых позициях
        for name, data in self.button_data.items():
            row, col = data["position"]
            btn = data["widget"]
            
            # Восстанавливаем стиль и размер
            btn.update_style()
            btn.setFixedSize(data["width"], data["height"])
            
            self.buttons_panel.buttons_layout.addWidget(btn, row, col)
        
        self.save_buttons()

    def save_buttons(self):
        """Сохраняет кнопки в файл"""
        try:
            data_to_save = []
            for name, data in self.button_data.items():
                if not isinstance(name, str) or not name:
                    continue
                    
                button_info = {
                    'name': name,
                    'description': data['description'],
                    'position': list(data['position']),
                    'width': data['width'],
                    'height': data['height'],
                }
                
                # Добавляем расширенные настройки если они есть
                if name in self.advanced_settings:
                    button_info['advanced'] = self.advanced_settings[name]
                    
                data_to_save.append(button_info)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Ошибка сохранения кнопок: {e}")

    def load_buttons(self):
        """Загружает кнопки из файла"""
        if not os.path.exists(self.config_file):
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not data:
                    return
                    
                for item in data:
                    name = item.get('name')
                    if not isinstance(name, str) or not name:
                        continue
                        
                    if name not in self.button_data:
                        self.add_button(
                            name,
                            item.get('description', ''),
                            tuple(item.get('position', (0, 0)))
                        )
                    
                    if name in self.button_data:
                        self.button_data[name]['width'] = item.get('width', self.button_width)
                        self.button_data[name]['height'] = item.get('height', self.button_height)
                        if item.get('advanced'):
                            self.advanced_settings[name] = item['advanced']
                            
        except Exception as e:
            logging.error(f"Ошибка загрузки кнопок: {e}")

    def update_all_buttons_width(self, value):
        """Обновляет ширину всех кнопок"""
        self.button_width = max(80, value)
        
        for name, data in self.button_data.items():
            btn = data["widget"]
            if isinstance(btn, DraggableButton):
                btn.current_width = self.button_width
                data["width"] = self.button_width
                btn.setFixedWidth(self.button_width)
                btn.update_style()
                
        self.save_buttons()
        self.save_size_settings()

    def update_all_buttons_height(self, value):
        """Обновляет высоту всех кнопок"""
        self.button_height = max(30, value)
        
        for name, data in self.button_data.items():
            btn = data["widget"]
            if isinstance(btn, DraggableButton):
                btn.current_height = self.button_height
                data["height"] = self.button_height
                btn.setFixedHeight(self.button_height)
                btn.update_style()
                
        self.save_buttons()
        self.save_size_settings()

    def update_row_spacing(self, value):
        """Обновляет межстрочное расстояние"""
        self.row_spacing = max(0, value)
        self.buttons_panel.buttons_layout.setVerticalSpacing(self.row_spacing)
        self.save_size_settings()

    def save_size_settings(self):
        """Сохраняет настройки размеров"""
        try:
            size_settings = {
                'width': self.button_width,
                'height': self.button_height,
                'row_spacing': self.row_spacing
            }
            
            size_file = os.path.join(self.settings_dir, f"{'chat' if self.is_chat_commands else 'main'}_size_settings.json")
            with open(size_file, 'w', encoding='utf-8') as f:
                json.dump(size_settings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек размеров: {e}")

    def load_size_settings(self):
        """Загружает настройки размеров"""
        try:
            size_file = os.path.join(self.settings_dir, f"{'chat' if self.is_chat_commands else 'main'}_size_settings.json")
            if os.path.exists(size_file):
                with open(size_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    self.button_width = settings.get('width', 120)
                    self.button_height = settings.get('height', 40)
                    self.row_spacing = settings.get('row_spacing', 5)
                    
                    # Применяем настройки к layout
                    self.buttons_panel.buttons_layout.setVerticalSpacing(self.row_spacing)
                    
                    # Обновляем слайдеры если они есть
                    if hasattr(self, 'settings_panel'):
                        if hasattr(self.settings_panel, 'width_slider'):
                            self.settings_panel.width_slider.setValue(self.button_width)
                            self.settings_panel.width_value.setText(f"{self.button_width} px")
                        if hasattr(self.settings_panel, 'height_slider'):
                            self.settings_panel.height_slider.setValue(self.button_height)
                            self.settings_panel.height_value.setText(f"{self.button_height} px")
                        if hasattr(self.settings_panel, 'spacing_slider'):
                            self.settings_panel.spacing_slider.setValue(self.row_spacing)
                            self.settings_panel.spacing_value.setText(f"{self.row_spacing} px")
                            
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек размеров: {e}")

    def open_advanced_settings(self):
        """Открывает расширенные настройки для текущей кнопки"""
        if not self.supports_advanced_settings:
            QMessageBox.information(self, "Информация", 
                                  "Расширенные настройки доступны только для вкладки 'Ответы'")
            return
            
        if not self.current_button:
            QMessageBox.warning(self, "Ошибка", "Выберите кнопку для настройки")
            return
        
        # Создаем или получаем настройки для текущей кнопки
        if self.current_button not in self.advanced_settings:
            self.advanced_settings[self.current_button] = {
                'response_count': 1,
                'count_reports': False,
                'auto_enter': False,
                'responses': [self.settings_panel.btn_desc_edit.toPlainText()]
            }
        
        settings = self.advanced_settings[self.current_button]
        
        # Создаем окно настроек
        self.advanced_settings_window = QWidget()
        self.advanced_settings_window.setWindowTitle(f"Расширенные настройки: {self.current_button}")
        self.advanced_settings_window.setFixedSize(400, 300 if settings['response_count'] == 1 else 350)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Группа настроек ответов
        response_group = QGroupBox("Настройки ответов")
        response_layout = QVBoxLayout()
        
        # Настройка количества ответов (максимум 5)
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Кол-во ответов (1-5):"))
        
        self.response_count_input = QSpinBox()
        self.response_count_input.setRange(1, 5)
        self.response_count_input.setValue(settings['response_count'])
        self.response_count_input.valueChanged.connect(self.update_response_fields)
        count_layout.addWidget(self.response_count_input)
        
        response_layout.addLayout(count_layout)
        
        # Поля для ответов (только если ответов > 1)
        if settings['response_count'] > 1:
            self.response_fields = []
            self.response_scroll = QScrollArea()
            self.response_scroll.setWidgetResizable(True)
            
            response_container = QWidget()
            self.response_container_layout = QVBoxLayout(response_container)
            
            # Заполняем поля ответов
            for i, response in enumerate(settings['responses']):
                self.add_response_field(i, response)
            
            self.response_scroll.setWidget(response_container)
            response_layout.addWidget(self.response_scroll)
        
        response_group.setLayout(response_layout)
        layout.addWidget(response_group)
        
        # Чекбоксы
        self.count_reports_check = QCheckBox("Учитывать в счетчике репортов")
        self.count_reports_check.setChecked(settings['count_reports'])
        layout.addWidget(self.count_reports_check)
        
        self.auto_enter_check = QCheckBox("Автоматически нажимать Enter")
        self.auto_enter_check.setChecked(settings['auto_enter'])
        layout.addWidget(self.auto_enter_check)
        
        # Информационное сообщение (только если ответов > 1)
        if settings['response_count'] > 1:
            info_label = QLabel(
                "При количестве ответов > 1 будет выбран случайный вариант. "
                "Основное описание кнопки будет отключено."
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("color: #FFA500; font-style: italic;")
            layout.addWidget(info_label)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_advanced_settings)
        btn_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.advanced_settings_window.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        self.advanced_settings_window.setLayout(layout)
        self.advanced_settings_window.show()

    def add_response_field(self, index, text=""):
        """Добавляет поле для ответа"""
        if not hasattr(self, 'response_container_layout'):
            return None
        
        field = QTextEdit()
        field.setPlainText(text)
        field.setMaximumHeight(80)
        field.setStyleSheet("""
            QTextEdit {
                background: #353535;
                border: 1px solid #444;
                color: white;
                padding: 8px;
                border-radius: 3px;
            }
        """)
        
        # Добавляем метку и поле в layout
        label = QLabel(f"Ответ {index + 1}:")
        self.response_container_layout.addWidget(label)
        self.response_container_layout.addWidget(field)
        
        # Сохраняем поле в список
        if not hasattr(self, 'response_fields'):
            self.response_fields = []
        self.response_fields.append(field)
        
        return field

    def update_response_fields(self, count):
        """Обновляет количество полей для ответов"""
        # Если количество ответов стало 1 - скрываем поля
        if count == 1:
            if hasattr(self, 'response_fields'):
                # Сохраняем текущие ответы перед удалением
                responses = [field.toPlainText() for field in self.response_fields]
                if responses and self.current_button in self.advanced_settings:
                    self.advanced_settings[self.current_button]['responses'] = responses
                
                # Удаляем поля
                for field in self.response_fields:
                    field.deleteLater()
                self.response_fields = []
                
                # Удаляем scroll area если она есть
                if hasattr(self, 'response_scroll'):
                    self.response_scroll.deleteLater()
                    del self.response_scroll
            return
        
        # Если количество ответов > 1 - создаем/обновляем поля
        if not hasattr(self, 'response_scroll'):
            # Создаем новые элементы
            self.response_scroll = QScrollArea()
            self.response_scroll.setWidgetResizable(True)
            
            response_container = QWidget()
            self.response_container_layout = QVBoxLayout(response_container)
            self.response_scroll.setWidget(response_container)
            
            # Вставляем scroll area перед чекбоксами
            layout = self.advanced_settings_window.layout()
            layout.insertWidget(layout.indexOf(self.count_reports_check), self.response_scroll)
        
        # Инициализируем список полей если нужно
        if not hasattr(self, 'response_fields'):
            self.response_fields = []
        
        # Добавляем недостающие поля
        while len(self.response_fields) < count:
            new_index = len(self.response_fields)
            # Используем сохраненные ответы или пустые строки
            default_text = ""
            if (self.current_button in self.advanced_settings and 
                len(self.advanced_settings[self.current_button]['responses']) > new_index):
                default_text = self.advanced_settings[self.current_button]['responses'][new_index]
            
            self.add_response_field(new_index, default_text)
        
        # Удаляем лишние поля
        while len(self.response_fields) > count:
            field = self.response_fields.pop()
            field.deleteLater()
        
        # Показываем scroll area
        self.response_scroll.show()
        self.advanced_settings_window.adjustSize()

    def save_advanced_settings(self):
        """Сохраняет расширенные настройки для текущей кнопки"""
        if not self.current_button:
            return
        
        response_count = self.response_count_input.value()
        
        settings = {
            'response_count': response_count,
            'count_reports': self.count_reports_check.isChecked(),
            'auto_enter': self.auto_enter_check.isChecked(),
            'responses': []
        }
        
        if response_count == 1:
            # Для 1 ответа используем текущее значение основного описания
            settings['responses'] = [self.settings_panel.btn_desc_edit.toPlainText()]
        else:
            # Для нескольких ответов собираем их из полей
            settings['responses'] = [field.toPlainText() for field in self.response_fields]
        
        self.advanced_settings[self.current_button] = settings
        self.update_description_field_state()
        self.save_buttons()
        self.advanced_settings_window.close()

    def update_description_field_state(self):
        """Обновляет состояние поля описания в зависимости от настроек"""
        if not self.current_button:
            return
        
        # Если для кнопки есть настройки и ответов больше 1 - блокируем поле описания
        if (self.current_button in self.advanced_settings and 
            self.advanced_settings[self.current_button]['response_count'] > 1):
            self.settings_panel.btn_desc_edit.setEnabled(False)
            self.settings_panel.btn_desc_edit.setStyleSheet("""
                QTextEdit {
                    background: #252525;
                    border: 1px solid #333;
                    color: #555;
                    padding: 8px;
                    border-radius: 3px;
                }
            """)
            self.settings_panel.btn_desc_edit.setPlaceholderText("Используйте расширенные настройки для нескольких ответов")
        else:
            self.settings_panel.btn_desc_edit.setEnabled(True)
            self.settings_panel.btn_desc_edit.setStyleSheet("""
                QTextEdit {
                    background: #353535;
                    border: 1px solid #444;
                    color: white;
                    padding: 8px;
                    border-radius: 3px;
                }
            """)
            self.settings_panel.btn_desc_edit.setPlaceholderText("")

class BaseSettingsPanel(QWidget):
    """Базовая панель настроек для обеих вкладок"""
    
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

        # Определяем цвет заголовка в зависимости от типа панели
        title_color = "#4CAF50" if self.parent.is_chat_commands else "#FFA500"
        panel_name = self.parent.panel_name

        settings_group = QGroupBox(f"Настройка {panel_name.lower()}")
        settings_group.setStyleSheet(f"""
            QGroupBox {{
                color: {title_color};
                font-size: 14px;
                border: 1px solid #333;
                border-radius: 3px;
                margin-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }}
        """)
        
        group_layout = QVBoxLayout(settings_group)
        group_layout.setContentsMargins(5, 10, 5, 5)
        group_layout.setSpacing(8)

        # Поля ввода (одинаковые для обеих панелей)
        group_layout.addWidget(QLabel("Название:"))
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

        group_layout.addWidget(QLabel("Описание:"))
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
        self.width_slider.setRange(40, 300)
        self.width_slider.setValue(120)
        self.width_slider.setTickInterval(10)
        self.width_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.width_slider.setStyleSheet(self.get_slider_style())
        self.width_slider.valueChanged.connect(self.parent.update_all_buttons_width)
        
        self.width_value = QLabel("120 px")
        self.width_value.setStyleSheet("color: #FFA500; font-weight: bold;")
        self.width_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        width_layout.addWidget(self.width_slider)
        width_layout.addWidget(self.width_value)
        group_layout.addLayout(width_layout)

        # Слайдер высоты
        height_layout = QVBoxLayout()
        height_layout.addWidget(QLabel("Высота кнопок:"))
        
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(10, 100)
        self.height_slider.setValue(40)
        self.height_slider.setTickInterval(5)
        self.height_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.height_slider.setStyleSheet(self.get_slider_style())
        self.height_slider.valueChanged.connect(self.parent.update_all_buttons_height)
        
        self.height_value = QLabel("40 px")
        self.height_value.setStyleSheet("color: #FFA500; font-weight: bold;")
        self.height_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        height_layout.addWidget(self.height_slider)
        height_layout.addWidget(self.height_value)
        group_layout.addLayout(height_layout)

        # Слайдер межстрочного расстояния
        spacing_layout = QVBoxLayout()
        spacing_layout.addWidget(QLabel("Межстрочное расстояние:"))
        
        self.spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self.spacing_slider.setRange(0, 20)
        self.spacing_slider.setValue(5)
        self.spacing_slider.setTickInterval(2)
        self.spacing_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.spacing_slider.setStyleSheet(self.get_slider_style())
        self.spacing_slider.valueChanged.connect(self.parent.update_row_spacing)
        
        self.spacing_value = QLabel("5 px")
        self.spacing_value.setStyleSheet("color: #FFA500; font-weight: bold;")
        self.spacing_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        spacing_layout.addWidget(self.spacing_slider)
        spacing_layout.addWidget(self.spacing_value)
        group_layout.addLayout(spacing_layout)

        # Кнопки управления (одинаковые для обеих панелей)
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

        # Кнопка сохранения
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setFixedHeight(30)
        self.save_btn.setStyleSheet(self.get_button_style())
        self.save_btn.clicked.connect(self.parent.save_button)
        group_layout.addWidget(self.save_btn)

        # Расширенные настройки (только для основной панели)
        if self.parent.supports_advanced_settings:
            self.advanced_btn = QPushButton("Расширенные настройки")
            self.advanced_btn.setFixedHeight(30)
            self.advanced_btn.setStyleSheet(self.get_button_style())
            self.advanced_btn.clicked.connect(self.parent.open_advanced_settings)
            group_layout.addWidget(self.advanced_btn)

        main_layout.addWidget(settings_group)
        main_layout.addStretch()

        # Подключаем обновление значений слайдеров
        self.width_slider.valueChanged.connect(lambda v: self.width_value.setText(f"{v} px"))
        self.height_slider.valueChanged.connect(lambda v: self.height_value.setText(f"{v} px"))
        self.spacing_slider.valueChanged.connect(lambda v: self.spacing_value.setText(f"{v} px"))

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

    def get_slider_style(self):
        return """
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
        """

class DraggableButton(QPushButton):
    def __init__(self, text, parent):
        super().__init__(text, parent)
        self.parent = parent
        self.setMouseTracking(True)
        
        self.drag_start_position = None
        self.current_width = 120
        self.current_height = 40
        self.is_chat_command = getattr(parent, 'is_chat_commands', False)
        
        self.update_style()
        self.setAcceptDrops(True)

    def update_style(self):
        """Обновляет стиль кнопки в зависимости от типа"""
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
                    min-height: {self.current_height}px;
                    max-height: {self.current_height}px;
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
                    min-height: {self.current_height}px;
                    max-height: {self.current_height}px;
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
                    min-height: {self.current_height}px;
                    max-height: {self.current_height}px;
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
                    min-height: {self.current_height}px;
                    max-height: {self.current_height}px;
                    font-size: 11px;
                }}
            """
        
        self.setStyleSheet(self.normal_style)

    def update_width(self, new_width):
        """Обновляет ширину кнопки"""
        self.current_width = new_width
        self.update_style()
        self.setFixedWidth(new_width)

    def update_height(self, new_height):
        """Обновляет высоту кнопки"""
        self.current_height = new_height
        self.update_style()
        self.setFixedHeight(new_height)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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

class ButtonEditor(QMainWindow):
    buttons_updated = pyqtSignal(dict)

    def load_click_coordinates(self):
        """Загружает сохраненные координаты клика из app_settings.json"""
        script_dir = Path(__file__).parent  # Папка scripts/
        settings_path = script_dir / "scripts" / "settings" / "app_settings.json"
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    coords = settings.get('click_coords', (22, 330))
                    # Проверяем что координаты валидны
                    if isinstance(coords, (list, tuple)) and len(coords) == 2:
                        self.click_coordinates = tuple(int(x) for x in coords)
                    else:
                        self.click_coordinates = (22, 330)
                    logging.info(f"Загружены координаты клика: {self.click_coordinates}")
            except Exception as e:
                logging.info(f"Ошибка загрузки координат клика: {e}")
                self.click_coordinates = (22, 330)
        else:
            self.click_coordinates = (22, 330)

    def __init__(self):
        super().__init__()
        self.executor_enabled = False  # По умолчанию выключен
        self.click_coordinates = (22, 330)
        self.base_path = get_base_path()
        self._is_checking = False
        self.report_count = 0
        self.settings_dir = os.path.join(self.base_path, "scripts", "settings")
        os.makedirs(self.settings_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.settings_dir, "button_config.json")
        self.width_config_file = os.path.join(self.settings_dir, "button_width.cfg")
        self.color_settings_file = os.path.join(self.settings_dir, "color_settings.json")
        self.load_click_coordinates()

        if hasattr(self, 'executor_window'):
            self.executor_window.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.original_mouse_pos = None
        self.button_data = {}
        self.advanced_settings = {}
        self.current_button = None
        self.executor_window = None
        self.watcher = None
        self.should_executor_be_visible = False
        self._current_button_width = 120
        
        self.load_chat_settings()

        self.target_windows = []
        self.required_color = (68, 80, 95)
        self.check_coords = (719, 317)
        self.color_check_enabled = True
        
        self.click_coordinates = (0, 0)

        self.setWindowTitle("Редактор кнопок")
        self.setGeometry(100, 100, 1000, 400)
        self.setup_ui()
        set_dark_theme(self)
        
        self.load_width_from_file()
        self.load_buttons_from_file()
        self.load_color_settings()
        
        if not self.button_data:
            self.load_initial_buttons()

        self.setup_executor_button()
        
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_conditions)
        self.check_timer.start(100)

        self.resolution_timer = QTimer(self)
        self.resolution_timer.timeout.connect(self.update_game_resolution)
        self.resolution_timer.start(1000)

 # Настройки обнаружения чата
        self.chat_detection_coords = (100, 100)
        self.chat_detection_color = (68, 80, 95)
        self.chat_color_tolerance = 10
        
        # Таймер для проверки чата
        self.chat_check_timer = QTimer(self)
        self.chat_check_timer.timeout.connect(self.check_chat_conditions)
        self.chat_check_timer.start(150)  # Проверка чата каждые 150мс

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setFixedSize(950, 530)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #252525;
            }
            QTabBar::tab {
                background: #333;
                color: white;
                padding: 8px 16px;
                margin-right: 2px;
                border: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background: #555;
            }
            QTabBar::tab:hover {
                background: #444;
            }
        """)
        
        self.commands_tab = BasePanel(self, is_chat_commands=False)
        self.tab_widget.addTab(self.commands_tab, "Ответы")
        
        self.chat_commands_tab = BasePanel(self, is_chat_commands=True)
        self.tab_widget.addTab(self.chat_commands_tab, "Чат команды")
        
        main_layout.addWidget(self.tab_widget)

    def check_chat_conditions(self):
        """Проверяет условия для открытия чат-команд"""
        if hasattr(self, 'chat_executor_window') and self.chat_executor_window:
            if self.chat_executor_window.mouse_over:
                return
                
        chat_opened = self.check_chat_opened()
        
        if chat_opened:
            if not hasattr(self, 'chat_executor_window') or not self.chat_executor_window:
                self.open_chat_executor()
            elif self.chat_executor_window.isHidden():
                self.chat_executor_window.show()
        else:
            if hasattr(self, 'chat_executor_window') and self.chat_executor_window:
                if not self.chat_executor_window.mouse_over:
                    self.chat_executor_window.hide()
    
    def open_chat_executor(self):
        """Открывает окно чат-команд"""
        try:
            if not hasattr(self, 'chat_executor_window') or not self.chat_executor_window:
                from .chat_executor import ChatExecutor
                chat_button_data = self.chat_commands_tab.button_data if hasattr(self, 'chat_commands_tab') else {}
                self.chat_executor_window = ChatExecutor(chat_button_data, self)
                logging.info("Окно чат-команд создано")
            
            if self.chat_executor_window.isHidden():
                self.chat_executor_window.show()
                logging.info("Окно чат-команд показано")
            else:
                self.chat_executor_window.raise_()
                logging.info("Окно чат-команд поднято на передний план")
                
        except Exception as e:
            logging.error(f"Ошибка открытия окна чат-команд: {e}")

    def check_chat_opened(self):
        """Проверяет, открыт ли чат по цвету"""
        try:
            x, y = self.chat_detection_coords
            pixel_color = pyautogui.pixel(x, y)
            
            color_match = all(
                abs(p - c) <= self.chat_color_tolerance 
                for p, c in zip(pixel_color, self.chat_detection_color)
            )
            
            return color_match
            
        except Exception as e:
            logging.error(f"Ошибка проверки чата: {e}")
            return False
    
    def update_chat_detection_settings(self, coords, color, tolerance=15, zone_size=15, min_matches=3, check_step=3):
        """Обновляет настройки обнаружения чата"""
        self.chat_detection_coords = coords
        self.chat_detection_color = color
        self.chat_color_tolerance = tolerance
        
        # Сохраняем настройки зоны
        chat_settings = {
            'chat_check_coords': self.chat_detection_coords,
            'chat_required_color': self.chat_detection_color,
            'chat_tolerance': self.chat_color_tolerance,
            'zone_size': zone_size,
            'min_matches_required': min_matches,
            'check_step': check_step
        }
        
        try:
            chat_settings_path = os.path.join(self.settings_dir, "chat_detection_settings.json")
            with open(chat_settings_path, 'w', encoding='utf-8') as f:
                json.dump(chat_settings, f, indent=2, ensure_ascii=False)
                
            logging.info(f"✅ Сохранены настройки чата с зоной: {coords} - {color}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка сохранения настроек чата: {e}")
        
        # Передаем настройки в окно чат-команд
        if hasattr(self, 'chat_executor_window') and self.chat_executor_window:
            self.chat_executor_window.update_chat_detection_settings(coords, color, tolerance)
    
    def save_chat_settings(self):
        """Сохраняет настройки обнаружения чата"""
        try:
            chat_settings = {
                'chat_check_coords': self.chat_detection_coords,
                'chat_required_color': self.chat_detection_color,
                'chat_tolerance': self.chat_color_tolerance
            }
            
            chat_settings_path = os.path.join(self.settings_dir, "chat_detection_settings.json")
            with open(chat_settings_path, 'w', encoding='utf-8') as f:
                json.dump(chat_settings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек чата: {e}")
    
    def load_chat_settings(self):
        """Загружает настройки обнаружения чата"""
        try:
            chat_settings_path = os.path.join(self.settings_dir, "chat_detection_settings.json")
            if os.path.exists(chat_settings_path):
                with open(chat_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    self.chat_detection_coords = tuple(settings.get('chat_check_coords', (100, 100)))
                    self.chat_detection_color = tuple(settings.get('chat_required_color', (68, 80, 95)))
                    self.chat_color_tolerance = settings.get('chat_tolerance', 10)
                    
                    logging.info(f"Загружены настройки чата: {self.chat_detection_coords}")
                    
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек чата: {e}")

    def load_initial_buttons(self):
        """Загружает начальные кнопки (для обратной совместимости)"""
        pass

    def setup_executor_button(self):
        self.executor_btn = QPushButton("Открыть исполнитель")
        self.executor_btn.setStyleSheet("""
            QPushButton {
                background: #9C27B0;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 15px;
                min-height: 40px;
            }
            QPushButton:hover {
                background: #AB47BC;
            }
        """)
        self.executor_btn.clicked.connect(self.open_executor_window)

    def handle_button_action(self, description):
        """Обрабатывает нажатия кнопок в исполнителе"""
        logging.info(f"Выполнено действие: {description}")
        QMessageBox.information(self, "Действие выполнено", 
                              f"Выполнено действие:\n\n{description}")
        
    def save_buttons_to_file(self):
        """Сохраняет кнопки в JSON-формате (для обратной совместимости)"""
        pass

    def load_buttons_from_file(self):
        """Загружает кнопки только из JSON-формата (для обратной совместимости)"""
        pass

    def load_width_from_file(self):
        """Загружает сохраненную ширину кнопок"""
        if os.path.exists(self.width_config_file):
            try:
                with open(self.width_config_file, 'r') as f:
                    width = int(f.read().strip())
                    if hasattr(self, 'commands_tab') and hasattr(self.commands_tab.settings_panel, 'width_slider'):
                        self.commands_tab.settings_panel.width_slider.setValue(width)
            except Exception as e:
                logging.info(f"Ошибка загрузки ширины: {e}, используем значение по умолчанию")

    def save_width_to_file(self):
        """Сохраняет текущую ширину кнопок"""
        try:
            with open(self.width_config_file, 'w') as f:
                if hasattr(self, 'commands_tab') and hasattr(self.commands_tab.settings_panel, 'width_slider'):
                    f.write(str(self.commands_tab.settings_panel.width_slider.value()))
        except Exception as e:
            logging.info(f"Ошибка сохранения ширины: {e}")

    def force_update_executor(self):
        """Принудительно обновляет исполнитель"""
        if self.executor_window and self.executor_window.isVisible():
            active_tab = self.tab_widget.currentWidget()
            if hasattr(active_tab, 'button_data'):
                self.executor_window.update_buttons(active_tab.button_data.copy())

    def close_executor_window(self):
        if hasattr(self, 'executor_window') and self.executor_window:
            try:
                self.executor_window.button_clicked.disconnect()
                self.buttons_updated.disconnect()
            except:
                pass
            self.executor_window.close()
            self.executor_window = None

    def open_executor_window(self):
        try:
            if self.executor_window is None:
                active_tab = self.tab_widget.currentWidget()
                button_data = active_tab.button_data.copy() if hasattr(active_tab, 'button_data') else {}
                
                self.executor_window = ButtonExecutor(button_data, self)
                self.executor_window.button_width = 120
                self.executor_window.button_clicked.connect(self.handle_button_action)
                self.executor_window.setWindowTitle("Исполнитель команд")
                self.executor_window.resize(800, 350)
                
                self.buttons_updated.connect(self.executor_window.update_buttons)
                self.executor_window.destroyed.connect(lambda: setattr(self, 'executor_window', None))
            
            if self.executor_window.isHidden():
                self.executor_window.show()
            else:
                self.executor_window.raise_()
                self.executor_window.activateWindow()
        
        except Exception as e:
            logging.info(f"Ошибка при открытии исполнителя: {e}")
            active_tab = self.tab_widget.currentWidget()
            button_data = active_tab.button_data.copy() if hasattr(active_tab, 'button_data') else {}
            
            self.executor_window = ButtonExecutor(button_data, self)
            self.executor_window.button_width = 120
            self.executor_window.button_clicked.connect(self.handle_button_action)
            self.buttons_updated.connect(self.executor_window.update_buttons)
            self.executor_window.setWindowTitle("Исполнитель команд")
            self.executor_window.resize(800, 600)
            self.executor_window.move(100, 100)
            self.executor_window.show()

    def eventFilter(self, obj, event):
        """Обработчик событий для проверки ЛКМ и автоматического закрытия"""
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if self.check_screen_color() and self.is_target_window_active():
                    if not hasattr(self, 'executor_window') or not self.executor_window:
                        self.open_executor_window()
                    elif not self.executor_window.isVisible():
                        self.executor_window.show()
        
        if event.type() == QEvent.Type.MouseMove:
            current_time = time.time()
            if hasattr(self, 'last_check_time') and current_time - self.last_check_time > 0.1:
                self.last_check_time = current_time
                if hasattr(self, 'executor_window') and self.executor_window:
                    if not self.check_screen_color():
                        self.executor_window.hide()
        
        return super().eventFilter(obj, event)

    def check_conditions(self):
        """Проверяет условия для показа/скрытия исполнителя"""
        # Проверяем, включен ли автоматический исполнитель
        if not self.executor_enabled:
            # Если автоматический режим выключен - не показываем окно
            if hasattr(self, 'executor_window') and self.executor_window and self.executor_window.isVisible():
                if not self.executor_window.mouse_over:
                    self.executor_window.hide()
            return
        
        if self._is_checking:
            return
        self._is_checking = True
        
        try:
            if hasattr(self, 'executor_window') and self.executor_window:
                if self.executor_window.mouse_over:
                    self._is_checking = False
                    return
                    
            current_state = self.check_screen_color()
            
            if current_state != self.should_executor_be_visible:
                self.should_executor_be_visible = current_state
                self.update_executor_visibility()
        finally:
            self._is_checking = False

    def update_executor_visibility(self):
        """Обновляет видимость исполнителя с учетом настроек"""
        # Проверяем, включен ли автоматический исполнитель
        if not self.executor_enabled:
            # Если выключен - скрываем окно если оно открыто
            if hasattr(self, 'executor_window') and self.executor_window:
                self.executor_window.hide()
            return
        
        if self.should_executor_be_visible:
            if not hasattr(self, 'executor_window') or not self.executor_window:
                active_tab = self.tab_widget.currentWidget()
                button_data = active_tab.button_data.copy() if hasattr(active_tab, 'button_data') else {}
                self.executor_window = ButtonExecutor(button_data, self)
                self.executor_window.show()
            elif self.executor_window.isHidden():
                self.executor_window.show()
        else:
            if hasattr(self, 'executor_window') and self.executor_window:
                if not self.executor_window.mouse_over:
                    self.executor_window.hide()

    def toggle_executor(self):
        """Ручное переключение видимости исполнителя"""
        if hasattr(self, 'executor_window') and self.executor_window:
            if self.executor_window.isVisible():
                self.executor_window.hide()
            else:
                self.executor_window.show()
        else:
            self.open_executor_window()

    def mousePressEvent(self, event):
        """Обработка кликов мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.check_conditions()
        super().mousePressEvent(event)

    def check_screen_color(self):
        """Проверяет цвет в двух точках"""
        try:
            x1, y1 = self.normalize_coordinates(*self.check_coords)
            screenshot1 = pyautogui.screenshot(region=(x1-2, y1-2, 5, 5))
            pixel1 = screenshot1.getpixel((2, 2))
            
            x2, y2 = self.normalize_coordinates(*self.check_coords2)
            screenshot2 = pyautogui.screenshot(region=(x2-2, y2-2, 5, 5))
            pixel2 = screenshot2.getpixel((2, 2))
            
            tolerance = self.color_tolerance
            
            color1_match = all(abs(p - c) <= tolerance for p, c in zip(pixel1, self.required_color))
            color2_match = all(abs(p - c) <= tolerance for p, c in zip(pixel2, self.required_color2))
            
            if color1_match and color2_match:
                logging.info(f"Обе точки совпали: {pixel1} и {pixel2}")
                return True
            else:
                if not color1_match:
                    logging.info(f"Точка 1 не совпала: {pixel1} (ожидался {self.required_color})")
                if not color2_match:
                    logging.info(f"Точка 2 не совпала: {pixel2} (ожидался {self.required_color2})")
                return False
                
        except Exception as e:
            logging.error(f"Ошибка проверки цвета: {e}")
            return False

    def _check_pixel_color_cached(self, coords, expected_color, tolerance, screenshot):
        """Проверка цвета с использованием кешированного скриншота"""
        try:
            current_color = screenshot.getpixel(coords)
            return all(abs(c - e) <= tolerance for c, e in zip(current_color, expected_color))
        except:
            return False

    def check_color_in_zone_cached(self, center, size, expected_color, tolerance, screenshot):
        """Проверка зоны с использованием кешированного скриншота"""
        try:
            left = max(0, center[0] - size[0] // 2)
            top = max(0, center[1] - size[1] // 2)
            
            for x in range(left, left + size[0], 2):
                for y in range(top, top + size[1], 2):
                    try:
                        pixel = screenshot.getpixel((x, y))
                        if all(abs(p - e) <= tolerance for p, e in zip(pixel, expected_color)):
                            return True
                    except:
                        continue
            return False
        except:
            return False
    
    def _check_pixel_color(self, coords, expected_color, tolerance):
        """Проверяет цвет в конкретной точке"""
        try:
            current_color = self._get_pixel_color(coords)
            return all(abs(c - e) <= tolerance for c, e in zip(current_color, expected_color))
        except:
            return False

    def _check_zone(self, center, size, expected_color, tolerance):
        """Проверяет цвет в зоне"""
        try:
            left = max(0, center[0] - size[0] // 2)
            top = max(0, center[1] - size[1] // 2)
            
            screenshot = pyautogui.screenshot()
            for x in range(left, left + size[0], 2):
                for y in range(top, top + size[1], 2):
                    try:
                        pixel = screenshot.getpixel((x, y))
                        if all(abs(p - e) <= tolerance for p, e in zip(pixel, expected_color)):
                            return True
                    except:
                        continue
            return False
        except:
            return False
    
    def _check_color_set(self, params):
        """Проверяет один набор параметров цвета"""
        try:
            if not self._check_single_pixel(params['check_coords'], params['required_color']):
                return False
                
            if not self.check_color_in_zone(
                params['zone_center'],
                self.zone_size,
                params['zone_color'],
                self.zone_tolerance
            ):
                return False
                
            return True
        except Exception as e:
            logging.error(f"Ошибка проверки набора цветов: {e}")
            return False
        
    def _get_pixel_color(self, coord):
        """Возвращает цвет пикселя по координатам"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hdc = user32.GetDC(0)
            pixel = gdi32.GetPixel(hdc, coord[0], coord[1])
            rgb = (pixel & 0xff, (pixel >> 8) & 0xff, (pixel >> 16) & 0xff)
            user32.ReleaseDC(0, hdc)
            return rgb
        except:
            screenshot = pyautogui.screenshot()
            return screenshot.getpixel(coord)

    def _color_close_enough(self, color1, color2, tolerance):
        """Проверяет, достаточно ли близки цвета с учетом допуска"""
        return all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))

    def _check_single_pixel(self, coord, expected_color):
        """Проверяет один пиксель с допуском"""
        try:
            pixel = self._get_pixel_color(coord)
            result = self._color_close_enough(pixel, expected_color, tolerance=5)
            
            if not result:
                logging.info(f"Ожидался цвет {expected_color}, получен {pixel} в координатах {coord}")
            
            return result
            
        except Exception as e:
            logging.info(f"Ошибка проверки цвета пикселя: {e}")
            return False

    def is_target_window_active(self):
        """Упрощенная проверка - всегда возвращает True для активного окна"""
        try:
            active_window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            return bool(active_window)
        except:
            return True
        
    def check_color_in_zone(self, center_coords, size, target_color, tolerance=10, step=2):
        """
        Проверяет наличие целевого цвета в зоне вокруг указанных координат
        center_coords: (x, y) - центральные координаты
        size: (width, height) - размер зоны для проверки
        target_color: (r, g, b) - целевой цвет
        tolerance: допустимое отклонение цвета
        """
        try:
            screenshot = pyautogui.screenshot()
            
            left = max(0, center_coords[0] - size[0] // 2)
            top = max(0, center_coords[1] - size[1] // 2)
            
            for x in range(left, left + size[0], step):
                for y in range(top, top + size[1], step):
                    try:
                        pixel = screenshot.getpixel((x, y))
                        if self._color_close_enough(pixel, target_color, tolerance):
                            return True
                    except:
                        continue
            return False
        except Exception as e:
            logging.info(f"Ошибка проверки зоны: {e}")
            return False

    def normalize_coordinates(self, x, y):
        """Нормализует координаты относительно активного окна"""
        try:
            active_window = win32gui.GetForegroundWindow()
            if active_window:
                rect = win32gui.GetWindowRect(active_window)
                window_width = rect[2] - rect[0]
                window_height = rect[3] - rect[1]
                
                return (
                    int(x * window_width / 1920),
                    int(y * window_height / 1080)
                )
        except:
            pass
        
        screen = QGuiApplication.primaryScreen().availableGeometry()
        return (
            int(x * screen.width() / 1920),
            int(y * screen.height() / 1080)
        )
    
    def normalize_all_coordinates(self):
        """Нормализует координаты проверки цвета"""
        try:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            self.check_coords = (
                int(270 * screen.width() / 1920),
                int(320 * screen.height() / 1080)
            )
        except:
            self.check_coords = (270, 320)

    def update_game_resolution(self):
        """Определяет текущее разрешение активного окна"""
        try:
            active_window = win32gui.GetForegroundWindow()
            if active_window:
                rect = win32gui.GetWindowRect(active_window)
                window_width = rect[2] - rect[0]
                window_height = rect[3] - rect[1]
                
                if hasattr(self, 'last_window_resolution') and self.last_window_resolution != (window_width, window_height):
                    logging.info(f"Обнаружено изменение разрешения окна: {window_width}x{window_height}")
                    self.normalize_all_coordinates()
                
                self.last_window_resolution = (window_width, window_height)
                return True
            return False
        except Exception as e:
            logging.info(f"Ошибка определения разрешения окна: {e}")
            return False
        
    def mouse_move(self, x, y):
        """Перемещает курсор мыши к указанным координатам с учетом нормализации."""
        try:
            norm_x, norm_y = self.normalize_coordinates(x, y)
            pyautogui.moveTo(norm_x, norm_y, duration=0.0)
            logging.info(f"Курсор перемещен к ({norm_x}, {norm_y})")
        except Exception as e:
            logging.error(f"Ошибка перемещения курсора: {e}")

    def mouse_click(self, x, y, button='left'):
        """Выполняет клик мыши по указанным координатам с учетом нормализации."""
        try:
            norm_x, norm_y = self.normalize_coordinates(x, y)
            pyautogui.moveTo(norm_x, norm_y, duration=0.01)
            pyautogui.click(button=button, _pause=False)
            logging.info(f"Выполнен клик {button} кнопкой по ({norm_x}, {norm_y})")
        except Exception as e:
            logging.error(f"Ошибка клика: {e}")

    def save_mouse_position(self):
        """Сохраняет текущую позицию курсора."""
        try:
            self.original_mouse_pos = pyautogui.position()
            logging.info(f"Сохранили позицию курсора: {self.original_mouse_pos}")
        except Exception as e:
            logging.error(f"Ошибка сохранения позиции курсора: {e}")

    def restore_mouse_position(self):
        """Восстанавливает сохраненную позицию курсора."""
        if self.original_mouse_pos:
            try:
                pyautogui.moveTo(self.original_mouse_pos.x, self.original_mouse_pos.y, duration=0.0)
            except Exception as e:
                return
    
    @property
    def button_width(self):
        return self._current_button_width
    
    @button_width.setter
    def button_width(self, value):
        value = max(90, min(300, value))
        self._current_button_width = value
        self._apply_button_width_to_all()

    def _apply_button_width_to_all(self):
        """Применяет текущую ширину ко всем кнопкам"""
        for name, data in self.button_data.items():
            btn = data["widget"]
            btn.setFixedWidth(self._current_button_width)
            data["width"] = self._current_button_width
        if hasattr(self, 'buttons_panel'):
            self.buttons_panel.container.updateGeometry()

    def load_color_settings(self):
        """Загружает настройки цветов для двух точек"""
        try:
            color_settings_path = os.path.join(self.settings_dir, "color_settings.json")
            if os.path.exists(color_settings_path):
                with open(color_settings_path, 'r') as f:
                    settings = json.load(f)
                    
                    self.check_coords = tuple(settings.get('check_coords', (270, 320)))
                    self.required_color = tuple(settings.get('required_color', (68, 68, 68)))
                    
                    check_coords2 = settings.get('check_coords2')
                    required_color2 = settings.get('required_color2')
                    
                    if check_coords2 and required_color2:
                        self.check_coords2 = tuple(check_coords2)
                        self.required_color2 = tuple(required_color2)
                        logging.info(f"✓ Вторая точка загружена: {self.check_coords2} - {self.required_color2}")
                    else:
                        self.check_coords2 = (300, 320)
                        self.required_color2 = (68, 68, 68)
                        logging.warning("⚠ Вторая точка не найдена в настройках, используем значения по умолчанию")
                    
                    self.color_tolerance = settings.get('tolerance', 10)
                    
                    logging.info(f"Загружены настройки двух точек:")
                    logging.info(f"Точка 1: {self.check_coords} - {self.required_color}")
                    logging.info(f"Точка 2: {self.check_coords2} - {self.required_color2}")
                    logging.info(f"Допуск: {self.color_tolerance}")
                    
            else:
                self.check_coords = (270, 320)
                self.required_color = (68, 68, 68)
                self.check_coords2 = (300, 320)
                self.required_color2 = (68, 68, 68)
                self.color_tolerance = 10
                logging.info("Используются настройки цвета по умолчанию")
                
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек цвета: {e}")
            self.check_coords = (270, 320)
            self.required_color = (68, 68, 68)
            self.check_coords2 = (300, 320)
            self.required_color2 = (68, 68, 68)
            self.color_tolerance = 10

    def save_color_settings(self):
        """Сохраняет настройки цвета в файл"""
        try:
            settings = {
                'check_coords': self.check_coords,
                'required_color': self.required_color,
                'check_coords2': getattr(self, 'check_coords2', (300, 320)),
                'required_color2': getattr(self, 'required_color2', (68, 68, 68)),
                'tolerance': getattr(self, 'color_tolerance', 10)
            }
            
            color_settings_path = os.path.join(self.settings_dir, "color_settings.json")
            with open(color_settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
                
            logging.info(f"Настройки цвета сохранены: {self.check_coords} - {self.required_color}")
            
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек цвета: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки цвета: {e}")