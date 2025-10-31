import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QPushButton, QLabel, QHBoxLayout, QDialog, 
                            QFileDialog, QMessageBox, QScrollArea)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QWheelEvent
from PyQt6.QtGui import QGuiApplication
from PIL import Image
import numpy as np
import json
import os
from pathlib import Path
import ctypes
import pyautogui
from pynput import keyboard as pynput_keyboard
from pynput import mouse as pynput_mouse

import logging
from scripts.win_event_listener import WinEventListener
from scripts.button_editor import ButtonEditor  # Добавьте в начало файла

from scripts.hotkey_manager import HotkeyManager
from scripts.hotkey_dialog import HotkeyDialog
from scripts.notification_manager import NotificationManager

from PyQt6.QtCore import QProcess
if getattr(sys, 'frozen', False):
    sys.argv = [sys.executable]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='button_executor.log'
)

class ZoomableScrollArea(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.zoom_factor = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 3.0
        self.zoom_step = 0.1
        
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Изменение масштаба при Ctrl + колесико
            angle = event.angleDelta().y()
            if angle > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def zoom_in(self):
        self.set_zoom(self.zoom_factor + self.zoom_step)
    
    def zoom_out(self):
        self.set_zoom(self.zoom_factor - self.zoom_step)
    
    def set_zoom(self, factor):
        self.zoom_factor = max(self.min_zoom, min(self.max_zoom, factor))
        if hasattr(self, 'image_label'):
            self.image_label.setPixmap(
                self.original_pixmap.scaled(
                    self.original_pixmap.size() * self.zoom_factor,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

class ClickableLabel(QLabel):
    clicked = pyqtSignal(QPoint)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.pos())
        super().mousePressEvent(event)

class ScreenshotAnalyzerDialog(QDialog):
    analysis_complete = pyqtSignal(tuple, tuple)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Анализатор скриншотов")
        self.main_window = parent
        self.setMinimumSize(1024, 768)  # Увеличенный минимальный размер
        
        self.points = []
        self.current_point_type = None  # 'executor' или 'chat'
        self.original_pixmap = None
        self.max_executor_points = 2
        self.max_chat_points = 1     # Максимум 1 точка чата
        
        # Устанавливаем стиль для всего диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #252525;
                color: white;
            }
            QLabel {
                color: white;
                background: transparent;
            }
            QPushButton {
                background: #333333;
                color: white;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 30px;
            }
            QPushButton:hover {
                background: #3A3A3A;
                border: 1px solid #555;
            }
            QPushButton:disabled {
                background: #1A1A1A;
                color: #666;
                border: 1px solid #333;
            }
            QScrollArea {
                background: #1E1E1E;
                border: 1px solid #333;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Панель управления
        control_layout = QHBoxLayout()
        
        self.btn_load = QPushButton("Загрузить скриншот")
        self.btn_load.setStyleSheet(self.get_button_style("#4CAF50", "#5CBF60"))
        self.btn_load.clicked.connect(self.load_screenshot)
        control_layout.addWidget(self.btn_load)
        
        self.btn_add_point = QPushButton("Добавить точку исполнителя")
        self.btn_add_point.setStyleSheet(self.get_button_style("#2196F3", "#42A5F5"))
        # ПРЯМОЕ подключение без лямбда-функций
        self.btn_add_point.clicked.connect(self.start_adding_point)
        self.btn_add_point.setEnabled(False)
        control_layout.addWidget(self.btn_add_point)
        
        self.btn_add_chat_point = QPushButton("Добавить точку чата")
        self.btn_add_chat_point.setStyleSheet(self.get_button_style("#9C27B0", "#AB47BC"))
        
        # ДОБАВЬТЕ ОТЛАДОЧНУЮ ИНФОРМАЦИЮ ПЕРЕД ПОДКЛЮЧЕНИЕМ
        print("=" * 50)
        print("ПОДКЛЮЧЕНИЕ КНОПКИ ДОБАВИТЬ ТОЧКУ ЧАТА")
        print(f"Метод start_adding_chat_point: {self.start_adding_chat_point}")
        print("=" * 50)
        self.btn_add_chat_point.clicked.connect(self.start_adding_chat_point)
        self.btn_add_chat_point.setEnabled(False)
        control_layout.addWidget(self.btn_add_chat_point)
        
        self.btn_analyze = QPushButton("Анализировать")
        self.btn_analyze.setStyleSheet(self.get_button_style("#FF9800", "#FB8C00"))
        self.btn_analyze.clicked.connect(self.analyze_points)
        self.btn_analyze.setEnabled(False)
        control_layout.addWidget(self.btn_analyze)
        
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setStyleSheet(self.get_button_style("#F44336", "#E53935"))
        self.btn_clear.clicked.connect(self.clear_points)
        control_layout.addWidget(self.btn_clear)
        
        layout.addLayout(control_layout)
        
        layout.addLayout(control_layout)
        print("Создана кнопка добавления точки чата")
        print(f"Кнопка подключена к методу: {self.btn_add_chat_point.clicked}")
        # Область для скриншота с возможностью прокрутки и зума
        self.scroll_area = ZoomableScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #1E1E1E;
                border: 1px solid #333;
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background: #2A2A2A;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.screenshot_label = ClickableLabel()
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
            }
        """)
        self.screenshot_label.clicked.connect(self.handle_click)
        
        self.scroll_area.setWidget(self.screenshot_label)
        layout.addWidget(self.scroll_area)
        
        # Панель информации
        self.info_label = QLabel("Загрузите скриншот и добавьте точки для анализа")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            QLabel {
                background: #1E1E1E;
                color: white;
                padding: 10px;
                border: 1px solid #333;
                border-radius: 3px;
                font-size: 12px;
            }
        """)
        self.info_label.setMinimumHeight(80)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
    
    def get_button_style(self, color1=None, color2=None):
        """Возвращает стиль кнопки с возможностью задания цветов"""
        if color1 and color2:
            return f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {color1}, stop:1 {color2});
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 8px 12px;
                    font-size: 12px;
                    min-height: 30px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {color1}, stop:1 {color2});
                    border: 1px solid #555;
                }}
                QPushButton:disabled {{
                    background: #1A1A1A;
                    color: #666;
                    border: 1px solid #333;
                }}
            """
        else:
            return """
                QPushButton {
                    background: #333333;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 8px 12px;
                    font-size: 12px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    background: #3A3A3A;
                    border: 1px solid #555;
                }
                QPushButton:disabled {
                    background: #1A1A1A;
                    color: #666;
                    border: 1px solid #333;
                }
            """
    
    def start_adding_chat_point(self):
        """Начинает добавление точки для обнаружения чата"""
        print("=" * 50)
        print("🎯 МЕТОД start_adding_chat_point ВЫЗВАН!")
        print("=" * 50)
        
        # Проверяем, не превышен ли лимит точек чата
        chat_points_count = len([p for p in self.points if p.get("type") == "chat"])
        print(f"Текущее количество точек чата: {chat_points_count}")
        
        if chat_points_count >= self.max_chat_points:
            print("Лимит точек чата превышен!")
            QMessageBox.warning(self, "Ошибка", 
                            f"Можно добавить не более {self.max_chat_points} точки чата!")
            return
        
        # Проверяем, не добавлены ли уже точки исполнителя
        executor_points_count = len([p for p in self.points if p.get("type") != "chat"])
        print(f"Текущее количество точек исполнителя: {executor_points_count}")
        
        if executor_points_count > 0:
            reply = QMessageBox.question(self, "Подтверждение",
                                    "Точки исполнителя будут удалены. Продолжить?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                print("Пользователь отказался удалять точки исполнителя")
                return
            # Удаляем точки исполнителя
            self.points = [p for p in self.points if p.get("type") == "chat"]
            self.update_screenshot_display()
            print("Точки исполнителя удалены")
        
        # Устанавливаем режим добавления точки чата
        self.current_point_type = "chat"
        
        print(f"✅ Установлен режим: {self.current_point_type}")
        print(f"✅ current_point_type после установки: {self.current_point_type}")
        
        self.info_label.setText(
            "🔍 Режим добавления точки чата\n\n"
            "Кликните на скриншоте в месте, где должен открываться чат-помощник.\n"
            "Обычно это область ввода текста в чате игры."
        )
        
        # Подсвечиваем кнопку для индикации активного режима
        self.btn_add_chat_point.setStyleSheet(self.get_active_button_style())
        self.btn_add_point.setStyleSheet(self.get_button_style("#2196F3", "#42A5F5"))
        
        print("=" * 50)
        print("✅ РЕЖИМ ДОБАВЛЕНИЯ ЧАТА АКТИВИРОВАН - МОЖНО КЛИКАТЬ НА СКРИНШОТ")
        print("=" * 50)

    def get_active_button_style(self):
        return """
            QPushButton {
                background: #FF5722;
                color: white;
                border: 2px solid #FF9800;
                padding: 8px 12px;
                font-size: 12px;
                border-radius: 3px;
                min-height: 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FF7043;
            }
        """

    def load_screenshot(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Выберите скриншот", "", "Images (*.png *.jpg *.bmp)"
        )
        
        if filepath:
            try:
                self.screenshot = Image.open(filepath)
                self.original_pixmap = self.pil2pixmap(self.screenshot)
                self.scroll_area.original_pixmap = self.original_pixmap
                self.scroll_area.image_label = self.screenshot_label
                self.update_screenshot_display()
                
                self.btn_add_point.setEnabled(True)
                self.btn_analyze.setEnabled(True)
                self.btn_add_chat_point.setEnabled(True) 
                self.info_label.setText(
                    "✅ Скриншот загружен!\n\n"
                    "Теперь вы можете:\n"
                    "1. 🟥 Добавить точки для ИСПОЛНИТЕЛЯ кнопок\n" 
                    "2. 🟩 Добавить точки для ЧАТ-ПОМОЩНИКА\n"
                    "3. 📊 Нажать 'Анализировать' для сохранения всех настроек\n\n"
                    "Рекомендуется добавить минимум 2 точки исполнителя и 1 точку чата"
                )
                
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить изображение: {str(e)}")
    
    def pil2pixmap(self, pil_img):
        img = pil_img.convert("RGBA")
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.size[0], img.size[1], QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimg)
    
    def start_adding_point(self):
        """Начинает добавление обычной точки"""
        # Проверяем, не превышен ли лимит точек исполнителя
        executor_points_count = len([p for p in self.points if p.get("type") != "chat"])
        if executor_points_count >= self.max_executor_points:
            QMessageBox.warning(self, "Ошибка", 
                            f"Можно добавить не более {self.max_executor_points} точек исполнителя!")
            return
        
        # Проверяем, не добавлена ли уже точка чата
        chat_points_count = len([p for p in self.points if p.get("type") == "chat"])
        if chat_points_count > 0:
            reply = QMessageBox.question(self, "Подтверждение",
                                    "Точка чата будет удалена. Продолжить?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            # Удаляем точку чата
            self.points = [p for p in self.points if p.get("type") != "chat"]
        
        # Устанавливаем режим добавления точки исполнителя
        self.current_point_type = "executor"
        self.info_label.setText("Кликните на скриншоте в нужном месте для добавления точки исполнителя")

    def handle_click(self, pos):
        print(f"Клик по координатам: {pos}")
        print(f"Текущий режим: {self.current_point_type}")
        print(f"Всего точек: {len(self.points)}")
        
        # Проверяем, есть ли активный режим добавления точки
        if self.current_point_type is None:
            print("Нет активного режима добавления точки")
            return
            
        if not hasattr(self, 'screenshot') or self.screenshot is None:
            print("Скриншот не загружен")
            return
        
        # Получаем реальные размеры изображения в пикселях
        img_width = self.screenshot.width
        img_height = self.screenshot.height
        
        print(f"Размер изображения: {img_width}x{img_height}")
        
        # Получаем размеры виджета, в котором отображается изображение
        label_width = self.screenshot_label.width()
        label_height = self.screenshot_label.height()
        
        print(f"Размер label: {label_width}x{label_height}")
        
        # Вычисляем соотношения сторон
        img_ratio = img_width / img_height
        label_ratio = label_width / label_height
        
        # Определяем реальные размеры отображаемого изображения (с учетом сохранения пропорций)
        if label_ratio > img_ratio:
            # По высоте
            display_height = label_height
            display_width = int(display_height * img_ratio)
        else:
            # По ширине
            display_width = label_width
            display_height = int(display_width / img_ratio)
        
        # Вычисляем отступы (если изображение не заполняет весь виджет)
        h_pad = (label_width - display_width) // 2
        v_pad = (label_height - display_height) // 2
        
        print(f"Отступы: h_pad={h_pad}, v_pad={v_pad}")
        print(f"Размер отображения: {display_width}x{display_height}")
        
        # Корректируем позицию клика с учетом отступов и масштаба
        adj_x = pos.x() - h_pad
        adj_y = pos.y() - v_pad
        
        # Пропорционально пересчитываем в координаты исходного изображения
        if display_width > 0 and display_height > 0:
            x = int(adj_x * img_width / display_width)
            y = int(adj_y * img_height / display_height)
            
            # Ограничиваем координаты размерами изображения
            x = max(0, min(img_width - 1, x))
            y = max(0, min(img_height - 1, y))
            
            print(f"Преобразованные координаты: ({x}, {y})")
            
            try:
                pixel = self.screenshot.getpixel((x, y))
                r, g, b = pixel[:3]
                
                print(f"Цвет пикселя: RGB({r}, {g}, {b})")
                
                # Создаем точку в зависимости от типа
                if self.current_point_type == "chat":
                    point_name = "Точка чата"
                    point_type = "chat"
                else:
                    executor_points = len([p for p in self.points if p.get("type") != "chat"])
                    point_name = f"Точка {executor_points + 1}"
                    point_type = "executor"
                
                new_point = {
                    "name": point_name,
                    "coords": (x, y),
                    "color": (r, g, b),
                    "type": point_type
                }
                
                self.points.append(new_point)
                
                print(f"Точка добавлена: {new_point}")
                print(f"Всего точек после добавления: {len(self.points)}")
                
                # Обновляем информацию в зависимости от типа точки
                if point_type == "chat":
                    self.info_label.setText(
                        f"✅ Добавлена точка чата:\n"
                        f"Координаты: ({x}, {y})\n"
                        f"Цвет: RGB({r}, {g}, {b})\n\n"
                        f"Можно добавить только 1 точку чата. Нажмите 'Анализировать' для сохранения."
                    )
                    # Сбрасываем режим и стиль кнопки
                    self.current_point_type = None
                    self.btn_add_chat_point.setStyleSheet(self.get_button_style("#9C27B0", "#AB47BC"))
                    print("Режим добавления чата завершен")
                else:
                    executor_points = len([p for p in self.points if p.get("type") != "chat"])
                    remaining_points = self.max_executor_points - executor_points
                    
                    if remaining_points > 0:
                        self.info_label.setText(
                            f"✅ Добавлена {point_name}:\n"
                            f"Координаты: ({x}, {y})\n"
                            f"Цвет: RGB({r}, {g}, {b})\n\n"
                            f"Можно добавить еще {remaining_points} точку(и) исполнителя."
                        )
                        # Остаемся в режиме добавления точек исполнителя
                        print("Остаемся в режиме добавления точек исполнителя")
                    else:
                        self.info_label.setText(
                            f"✅ Добавлена {point_name}:\n"
                            f"Координаты: ({x}, {y})\n"
                            f"Цвет: RGB({r}, {g}, {b})\n\n"
                            f"Достигнут лимит точек исполнителя. Нажмите 'Анализировать' для сохранения."
                        )
                        self.current_point_type = None
                
                self.update_screenshot_display()
                
            except Exception as e:
                print(f"Ошибка при получении цвета: {str(e)}")
                QMessageBox.warning(self, "Ошибка", f"Не удалось получить цвет: {str(e)}")
        else:
            print("Ошибка: нулевой размер отображения!")
    
    def update_screenshot_display(self):
        if self.original_pixmap:
            pixmap = self.original_pixmap.copy()
            painter = QPainter(pixmap)
            
            for i, point in enumerate(self.points):
                # Разные цвета для разных типов точек
                if point.get("type") == "chat":
                    painter.setPen(QPen(QColor(0, 255, 0), 3))  # Зеленый для точек чата
                    painter.setBrush(QColor(0, 255, 0, 100))    # Зеленая заливка
                else:
                    painter.setPen(QPen(QColor(255, 0, 0), 3))  # Красный для обычных точек
                    painter.setBrush(QColor(255, 0, 0, 100))    # Красная заливка
                
                x, y = point["coords"]
                painter.drawEllipse(QPoint(x, y), 8, 8)  # Увеличиваем размер точек
                
                # Подписываем точки
                font = painter.font()
                font.setPointSize(10)
                font.setBold(True)
                painter.setFont(font)
                
                if point.get("type") == "chat":
                    painter.setPen(QPen(QColor(0, 200, 0)))  # Темно-зеленый для текста
                    painter.drawText(QPoint(x + 12, y - 12), "ЧАТ")
                else:
                    painter.setPen(QPen(QColor(200, 0, 0)))  # Темно-красный для текста
                    painter.drawText(QPoint(x + 12, y - 12), point["name"].replace("Точка ", ""))
            
            painter.end()
            
            scaled_pixmap = pixmap.scaled(
                pixmap.size() * self.scroll_area.zoom_factor,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.screenshot_label.setPixmap(scaled_pixmap)
            self.screenshot_label.adjustSize()

    

    def apply_analysis_results(self):
        """Применяет результаты анализа когда собраны все точки"""
        if not hasattr(self, 'analysis_points') or len(self.analysis_points) < 2:
            QMessageBox.warning(self, "Ошибка", "Недостаточно точек для анализа. Нужно как минимум 2 точки.")
            return
        
        try:
            # Берем первые две точки
            coord1, color1 = self.analysis_points[0]
            coord2, color2 = self.analysis_points[1]
            
            logging.info(f"Применяем настройки:")
            logging.info(f"Точка 1: {coord1} - {color1}")
            logging.info(f"Точка 2: {coord2} - {color2}")
            
            # Сохраняем в настройки
            self.save_color_settings_to_file(coord1, color1, coord2, color2)
            
            # Показываем подтверждение
            QMessageBox.information(self, "Успешно", 
                                f"Настройки сохранены!\n\n"
                                f"Точка 1:\nКоординаты: {coord1}\nЦвет: {color1}\n\n"
                                f"Точка 2:\nКоординаты: {coord2}\nЦвет: {color2}\n\n"
                                f"Перезапустите приложение для применения настроек.")
            
            # Очищаем временные данные
            del self.analysis_points
            
        except Exception as e:
            logging.error(f"Ошибка применения настроек: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось применить настройки: {e}")

    def save_color_settings_to_file(self, coords1, color1, coords2, color2):
        """Сохраняет настройки цвета для двух точек в файл"""
        try:
            settings = {
                'check_coords': coords1,
                'required_color': color1,
                'check_coords2': coords2,
                'required_color2': color2,
                'tolerance': 15  # Увеличиваем допуск для надежности
            }
            
            if hasattr(self, 'editor') and self.editor:
                settings_dir = self.editor.settings_dir
            else:
                settings_dir = os.path.join(os.path.dirname(sys.executable), "scripts", "settings")
            
            os.makedirs(settings_dir, exist_ok=True)
            color_settings_path = os.path.join(settings_dir, "color_settings.json")
            
            with open(color_settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
                
            logging.info(f"Настройки двух точек сохранены:")
            logging.info(f"Точка 1: {coords1} - {color1}")
            logging.info(f"Точка 2: {coords2} - {color2}")
            
            # Показываем подтверждение
            QMessageBox.information(self, "Сохранено", 
                                f"Настройки сохранены!\n\n"
                                f"Точка 1: {coords1}\nЦвет: {color1}\n\n"
                                f"Точка 2: {coords2}\nЦвет: {color2}")
                                
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек цвета: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")

    def save_color_settings(self):
        try:
        # Используем тот же метод определения пути
            if hasattr(self, 'editor') and self.editor:
                settings_dir = self.editor.settings_dir
            else:
                settings_dir = os.path.join(os.path.dirname(sys.executable), "scripts", "settings")
            
            os.makedirs(settings_dir, exist_ok=True)
            color_settings_path = os.path.join(settings_dir, "color_settings.json")
            
            settings = {
                'check_coords': self.editor.check_coords,
                'required_color': self.editor.required_color,
                'zone_center': self.editor.zone_center,
                'zone_color': self.editor.zone_color,
            }
            
            with open(color_settings_path, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            logging.info(f"Ошибка сохранения настроек цвета: {e}")

    def save_click_coordinates(self, coords2):
        """Сохраняет координаты клика в настройки"""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        base_x = int(coords2[0] * 1920 / screen.width())
        base_y = int(coords2[1] * 1080 / screen.height())
        self.click_coordinates = (base_x, base_y)
        
        if hasattr(self, 'editor') and self.editor:
            self.editor.click_coordinates = (base_x, base_y)
        self.save_settings()

    

    def get_settings_path(self):
        """Возвращает путь к app_settings.json в scripts/settings"""
        try:
            # Получаем правильный путь к папке scripts
            if getattr(sys, 'frozen', False):
                # Если приложение собрано в exe
                base_dir = Path(sys.executable).parent
            else:
                # Если запуск из исходного кода
                base_dir = Path(__file__).parent
            
            settings_dir = base_dir / "scripts" / "settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            return settings_dir / "app_settings.json"
        except Exception as e:
            logging.error(f"Ошибка получения пути настроек: {e}")
            return Path("app_settings.json")  # fallback



    def check_chat_settings(self):
        """Проверяет и выводит текущие настройки обнаружения чата"""
        if hasattr(self, 'editor') and self.editor:
            logging.info(f"Текущие настройки чата:")
            logging.info(f"Координаты: {self.editor.chat_detection_coords}")
            logging.info(f"Цвет: {self.editor.chat_detection_color}")
            logging.info(f"Допуск: {self.editor.chat_color_tolerance}")
            
            # Проверяем текущий цвет в указанных координатах
            try:
                x, y = self.editor.chat_detection_coords
                current_color = pyautogui.pixel(x, y)
                logging.info(f"Текущий цвет на экране: {current_color}")
                
                # Проверяем совпадение
                color_match = all(
                    abs(p - c) <= self.editor.chat_color_tolerance 
                    for p, c in zip(current_color, self.editor.chat_detection_color)
                )
                logging.info(f"Цвет совпадает: {color_match}")
                
            except Exception as e:
                logging.error(f"Ошибка проверки цвета: {e}")
    # В метод analyze_points класса ScreenshotAnalyzerDialog добавьте:
    def analyze_points(self):
        """Анализирует точки и передает ВСЕ точки в настройки"""
        # Разделяем точки по типам
        executor_points = [p for p in self.points if p.get("type") != "chat"]
        chat_points = [p for p in self.points if p.get("type") == "chat"]
        
        # Проверяем валидность конфигурации
        if executor_points and chat_points:
            QMessageBox.warning(self, "Ошибка", 
                            "Невозможно сохранить одновременно точки исполнителя и чата!\n"
                            "Выберите один тип точек.")
            return
        
        if not executor_points and not chat_points:
            QMessageBox.warning(self, "Ошибка", "Не добавлено ни одной точки!")
            return
        
        # Обработка точек исполнителя
        if executor_points:
            if len(executor_points) < 2:
                reply = QMessageBox.question(self, "Подтверждение",
                                        "Рекомендуется 2 точки исполнителя для надежной работы.\n"
                                        "Продолжить с одной точкой?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Передаем данные всех точек исполнителя
            for point in executor_points:
                self.analysis_complete.emit(point["coords"], point["color"])
            
            # Сохраняем координаты клика из последней точки исполнителя
            if len(executor_points) >= 2:
                self.parent().save_click_coordinates(executor_points[1]["coords"])
            elif len(executor_points) == 1:
                self.parent().save_click_coordinates(executor_points[0]["coords"])
                
            QMessageBox.information(self, "Успешно", 
                                f"Сохранено {len(executor_points)} точек исполнителя!")
        
        # Обработка точки чата
        if chat_points:
            chat_point = chat_points[0]  # Берем первую точку чата
            
            # Сохраняем настройки обнаружения чата
            self.parent().save_chat_detection_settings(
                chat_point["coords"], 
                chat_point["color"]
            )
            
            QMessageBox.information(self, "Успешно", 
                                "Сохранена точка чата!\n"
                                "Чат-помощник будет активироваться при открытии чата в игре.")
        
        self.close()

    def save_chat_detection_settings(self, coords, color):
        """Сохраняет настройки обнаружения чата"""
        try:
            # Преобразуем абсолютные координаты в относительные для 1920x1080
            screen = QGuiApplication.primaryScreen().availableGeometry()
            rel_x = coords[0] / screen.width()
            rel_y = coords[1] / screen.height()
            
            abs_x = int(rel_x * 1920)
            abs_y = int(rel_y * 1080)
            
            if hasattr(self, 'editor') and self.editor:
                # Сохраняем настройки с параметрами зоны
                self.editor.update_chat_detection_settings(
                    (abs_x, abs_y), 
                    color,
                    zone_size=15,      # Размер зоны 15x15 пикселей
                    min_matches=3,     # Минимум 3 совпадения
                    check_step=3       # Проверять каждый 3-й пиксель
                )
                
            QMessageBox.information(self, "Сохранено", 
                                f"Настройки чата сохранены!\n"
                                f"Координаты: ({abs_x}, {abs_y})\n"
                                f"Цвет: {color}\n"
                                f"Проверка по зоне 15x15 пикселей")
                                
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек чата: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки чата: {e}")

    
    
    def clear_points(self):
        self.points = []
        self.current_point_type = None
        self.update_screenshot_display()
        self.info_label.setText("Точки очищены. Добавьте новые точки")
        # Сбрасываем стили кнопок
        self.btn_add_point.setStyleSheet(self.get_button_style("#2196F3", "#42A5F5"))
        self.btn_add_chat_point.setStyleSheet(self.get_button_style("#9C27B0", "#AB47BC"))

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки")
        self.setFixedSize(300, 200)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Здесь будут настройки"))
        self.setLayout(layout)

class HelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Помощь")
        self.setFixedSize(300, 200)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Здесь будет справочная информация"))
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.click_coordinates = (22, 330)
        self.check_coords = (22, 330)
        self.required_color = (0, 0, 0)
        self.zone_center = (22, 330)
        self.zone_color = (0, 0, 0)
        self.chat_detection_coords = (100, 100)
        self.chat_detection_color = (255, 255, 255)
        self.chat_color_tolerance = 15
        self.chat_zone_size = 15
        self.chat_min_matches = 3
        self.chat_check_step = 3
        
        # Добавляем флаг состояния исполнителя
        self.executor_enabled = False  # По умолчанию выключен
        self.executor_btn = None  # Будем хранить ссылку на кнопку

        self.setWindowTitle("Admin Tools by Notoriuz - Главное меню")
        self.setFixedSize(600, 500)
        

        self.setup_hotkeys()
        
        # Центрируем окно на экране
        self.center_window()
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        title_label = QLabel("Admin Tools by Notoriuz")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF6B6B, stop:0.5 #4ECDC4, stop:1 #45B7D1);
                border-radius: 10px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Добавляем растягивающее пространство сверху
        layout.addStretch(1)
        
        # Кнопки меню (ОБНОВЛЕННЫЙ СПИСОК)
        buttons = [
            ("🎮 Загрузка...", self.launch_executor),  # Временный текст
            ("⚙️ Настройка исполнителя", self.open_executor_settings),
            #("⚙️ Настройка функций", self.open_function_settings),
            ("⚙️ Настройка горячих клавиш", self.open_hotkey_settings),
            ("🖼️ Анализатор скриншотов", self.open_screenshot_analyzer),
            ("❓ Помощь", self.show_help),
            ("🚪 Выход", self.close)
        ]
        
        for text, slot in buttons:
            btn = QPushButton(text)
            btn.setMinimumHeight(50)
            btn.setStyleSheet(self.get_button_style())
            btn.clicked.connect(slot)
            
            # Сохраняем ссылку на кнопку исполнителя
            if "Загрузка" in text:
                self.executor_btn = btn
                
            layout.addWidget(btn)
        
        # Добавляем растягивающее пространство снизу
        layout.addStretch(1)
        
        # Статус бар
        self.statusBar().showMessage("Готов к работе")
        
        # Загружаем настройки
        self.load_settings()
        
        # Применяем темную тему
        self.apply_dark_theme()
        
        # Создаем экземпляр редактора кнопок
        self.editor = ButtonEditor()
        self.editor._parent = self
        self.editor.executor_enabled = self.executor_enabled 
        
        # Загружаем настройки в редактор
        self.load_settings_to_editor()


    def launch_executor(self):
        """Переключает состояние автоматического исполнителя"""
        try:
            # Переключаем состояние
            self.executor_enabled = not self.executor_enabled
            
            logging.info(f"Переключение исполнителя: {self.executor_enabled}")
            
            # Обновляем текст кнопки в главном меню
            if self.executor_enabled:
                self.executor_btn.setText("🎮 Остановить исполнитель")
                self.statusBar().showMessage("Автоматический исполнитель ВКЛЮЧЕН - активация по цвету")
                logging.info("Автоматический исполнитель включен")
            else:
                self.executor_btn.setText("🎮 Запустить исполнитель") 
                self.statusBar().showMessage("Автоматический исполнитель ВЫКЛЮЧЕН")
                logging.info("Автоматический исполнитель выключен")
                
            # Синхронизируем состояние с редактором кнопок
            if hasattr(self, 'editor') and self.editor:
                self.editor.executor_enabled = self.executor_enabled
                
            # Сохраняем настройки
            self.save_settings()
            
            # Принудительно обновим интерфейс
            self.executor_btn.repaint()
            
        except Exception as e:
            logging.error(f"Ошибка переключения исполнителя: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось переключить исполнитель: {str(e)}")

    def get_button_style(self):
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6A11CB, stop:1 #2575FC);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7B1FA2, stop:1 #303F9F);
                border: 2px solid #4FC3F7;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4A148C, stop:1 #1A237E);
            }
        """

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2C3E50, stop:1 #34495E);
            }
            QStatusBar {
                background: #2C3E50;
                color: white;
                border-top: 1px solid #34495E;
            }
        """)


    def center_window(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_size = self.geometry()
        x = (screen.width() - window_size.width()) // 2
        y = (screen.height() - window_size.height()) // 2
        self.move(x, y)


    def open_function_settings(self):
        """Открывает окно настройки функций с горячими клавишами"""
        try:
            # Создаем диалог настроек функций
            settings_dialog = QDialog(self)
            settings_dialog.setWindowTitle("Настройка функций")
            settings_dialog.setFixedSize(600, 500)
            
            layout = QVBoxLayout(settings_dialog)
            
            # Заголовок
            title_label = QLabel("Настройка функций и горячих клавиш")
            title_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 10px;
                    background: #2C3E50;
                    border-radius: 5px;
                }
            """)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)
            
            # Кнопка настройки горячих клавиш
            btn_hotkeys = QPushButton("⚙️ Настройка горячих клавиш")
            btn_hotkeys.setMinimumHeight(40)
            btn_hotkeys.setStyleSheet(self.get_button_style())
            btn_hotkeys.clicked.connect(self.open_hotkey_settings)
            layout.addWidget(btn_hotkeys)
            
            # Другие настройки функций...
            # Можно добавить другие настройки здесь
            
            layout.addStretch()
            
            # Кнопки
            button_layout = QHBoxLayout()
            
            btn_close = QPushButton("Закрыть")
            btn_close.setStyleSheet("""
                QPushButton {
                    background: #95a5a6;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #7f8c8d;
                }
            """)
            btn_close.clicked.connect(settings_dialog.accept)
            
            button_layout.addWidget(btn_close)
            layout.addLayout(button_layout)
            
            settings_dialog.setStyleSheet("""
                QDialog {
                    background: #34495E;
                    color: white;
                }
                QLabel {
                    color: white;
                }
            """)
            
            settings_dialog.exec()
            
        except Exception as e:
            logging.error(f"Ошибка открытия настроек функций: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть настройки: {str(e)}")

    def open_hotkey_settings(self):
        """Открывает диалог настройки горячих клавиш"""
        try:
            hotkey_dialog = HotkeyDialog(self.hotkey_manager, self)
            hotkey_dialog.hotkey_changed.connect(self.on_hotkey_changed)
            hotkey_dialog.exec()
        except Exception as e:
            logging.error(f"Ошибка открытия настроек горячих клавиш: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть настройки горячих клавиш: {str(e)}")

    def on_hotkey_changed(self, action, key_sequence):
        """Обрабатывает изменение горячей клавиши"""
        try:
            # Перезапускаем слушатель с новыми настройками
            self.hotkey_manager.restart_listener()
            
            self.statusBar().showMessage(f"Горячая клавиша обновлена: {key_sequence}")
            
        except Exception as e:
            logging.error(f"Ошибка обновления горячей клавиши: {e}")

    def launch_executor(self):
        """Переключает состояние автоматического исполнителя"""
        try:
            # Переключаем состояние
            self.executor_enabled = not self.executor_enabled
            
            # Добавим отладочный вывод
            logging.info(f"Переключение исполнителя: {self.executor_enabled}")
            
            # Обновляем текст кнопки в главном меню
            if self.executor_enabled:
                self.executor_btn.setText("🎮 Остановить исполнитель")
                self.statusBar().showMessage("Автоматический исполнитель ВКЛЮЧЕН - активация по цвету")
                logging.info("Автоматический исполнитель включен")
            else:
                self.executor_btn.setText("🎮 Запустить исполнитель") 
                self.statusBar().showMessage("Автоматический исполнитель ВЫКЛЮЧЕН")
                logging.info("Автоматический исполнитель выключен")
                
            # Синхронизируем состояние с редактором кнопок
            if hasattr(self, 'editor') and self.editor:
                self.editor.executor_enabled = self.executor_enabled
                
            # Сохраняем настройки
            self.save_settings()
            
            # Принудительно обновим интерфейс
            self.executor_btn.repaint()
            
        except Exception as e:
            logging.error(f"Ошибка переключения исполнителя: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось переключить исполнитель: {str(e)}")

    def open_executor_settings(self):
        """Открывает окно настройки исполнителя (редактор кнопок)"""
        try:
            if not hasattr(self, 'editor') or not self.editor:
                # Создаем экземпляр редактора кнопок если его нет
                self.editor = ButtonEditor()
                self.editor._parent = self
                self.editor.executor_enabled = self.executor_enabled
            
            # Показываем редактор кнопок
            self.editor.show()
            self.editor.raise_()  # Поднимаем окно на передний план
            self.editor.activateWindow()  # Активируем окно
            
            self.statusBar().showMessage("Открыт редактор кнопок исполнителя")
            logging.info("Открыт редактор кнопок исполнителя")
            
        except Exception as e:
            logging.error(f"Ошибка открытия редактора кнопок: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть редактор кнопок: {str(e)}")

    def save_function_settings(self, dialog):
        """Сохраняет настройки функций"""
        try:
            # Здесь будет логика сохранения настроек
            QMessageBox.information(dialog, "Успех", "Настройки функций сохранены!")
            dialog.accept()
        except Exception as e:
            QMessageBox.warning(dialog, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")

    def open_screenshot_analyzer(self):
        try:
            self.analyzer = ScreenshotAnalyzerDialog(self)
            self.analyzer.analysis_complete.connect(self.handle_analysis_complete)
            self.analyzer.exec()
        except Exception as e:
            logging.error(f"Ошибка открытия анализатора: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть анализатор: {str(e)}")

    def handle_analysis_complete(self, coords, color):
        """Обрабатывает завершение анализа - сохраняет настройки цвета"""
        try:
            logging.info(f"Получены данные анализа: {coords}, {color}")
            
            # Сохраняем настройки в редактор
            if hasattr(self, 'editor') and self.editor:
                self.editor.check_coords = coords
                self.editor.required_color = color
                self.editor.save_color_settings()
            
            # Показываем подтверждение
            QMessageBox.information(self, "Успешно", 
                                f"Настройки цвета сохранены!\n\n"
                                f"Координаты: {coords}\n"
                                f"Цвет: {color}")
            
            self.statusBar().showMessage("Настройки цвета обновлены")
            
        except Exception as e:
            logging.error(f"Ошибка обработки анализа: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")

    def save_click_coordinates(self, coords):
        """Сохраняет координаты клика в настройки"""
        try:
            screen = QGuiApplication.primaryScreen().availableGeometry()
            base_x = int(coords[0] * 1920 / screen.width())
            base_y = int(coords[1] * 1080 / screen.height())
            self.click_coordinates = (base_x, base_y)
            
            if hasattr(self, 'editor') and self.editor:
                self.editor.click_coordinates = (base_x, base_y)
            
            self.save_settings()
            logging.info(f"Координаты клика сохранены: {self.click_coordinates}")
            
        except Exception as e:
            logging.error(f"Ошибка сохранения координат клика: {e}")


    def setup_hotkeys(self):
        """Настраивает систему горячих клавиш"""
        try:
            # Менеджер горячих клавиш
            self.hotkey_manager = HotkeyManager()
            self.hotkey_manager.hotkey_triggered.connect(self.on_hotkey_triggered)
            self.hotkey_manager.start_listener()
            
            # Менеджер уведомлений
            self.notification_manager = NotificationManager(self)
            
            print("✅ Система горячих клавиш инициализирована")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации горячих клавиш: {e}")

    def on_hotkey_triggered(self, action):
        """Обрабатывает срабатывание горячей клавиши"""
        try:
            key_sequence = self.hotkey_manager.get_hotkey_display(action)
            action_description = self.hotkey_manager.get_hotkey_description(action)
            
            # Показываем временное уведомление
            self.notification_manager.show_hotkey_notification(action, key_sequence)
            
            # Выполняем соответствующее действие
            self.execute_hotkey_action(action)
            
        except Exception as e:
            print(f"Ошибка обработки горячей клавиши: {e}")

    def execute_hotkey_action(self, action):
        """Выполняет действие по горячей клавише"""
        try:
            if action == "chat_commands":
                self.open_chat_commands()
            elif action == "hints":
                self.open_hints()
            elif action == "teleports":
                self.open_teleports()
        except Exception as e:
            print(f"Ошибка выполнения действия {action}: {e}")

    def open_chat_commands(self):
        """Открывает чат команды"""
        # Реализуйте открытие чат-команд
        print("Открытие чат команд...")

    def open_hints(self):
        """Открывает подсказки"""
        # Реализуйте открытие подсказок
        print("Открытие подсказок...")

    def open_teleports(self):
        """Открывает список телепортов"""
        # Реализуйте открытие телепортов
        print("Открытие списка телепортов...")

    def save_chat_detection_settings(self, coords, color):
        """Сохраняет настройки обнаружения чата"""
        try:
            # Преобразуем абсолютные координаты в относительные для 1920x1080
            screen = QGuiApplication.primaryScreen().availableGeometry()
            rel_x = coords[0] / screen.width()
            rel_y = coords[1] / screen.height()
            
            abs_x = int(rel_x * 1920)
            abs_y = int(rel_y * 1080)
            
            if hasattr(self, 'editor') and self.editor:
                # Сохраняем настройки с параметрами зоны
                self.editor.update_chat_detection_settings(
                    (abs_x, abs_y), 
                    color,
                    zone_size=15,      # Размер зоны 15x15 пикселей
                    min_matches=3,     # Минимум 3 совпадения
                    check_step=3       # Проверять каждый 3-й пиксель
                )
                
            QMessageBox.information(self, "Сохранено", 
                                f"Настройки чата сохранены!\n"
                                f"Координаты: ({abs_x}, {abs_y})\n"
                                f"Цвет: {color}\n"
                                f"Проверка по зоне 15x15 пикселей")
                                
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек чата: {e}")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки чата: {e}")

    def show_help(self):
        help_dialog = HelpDialog()
        help_dialog.exec()

    def load_settings(self):
        """Загружает настройки из файла"""
        try:
            settings_path = self.get_settings_path()
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Загружаем состояние исполнителя
                self.executor_enabled = settings.get('executor_enabled', False)
                
                # Синхронизируем с редактором
                if hasattr(self, 'editor') and self.editor:
                    self.editor.executor_enabled = self.executor_enabled
                
                # Обновляем текст кнопки при загрузке
                if hasattr(self, 'executor_btn') and self.executor_btn:
                    if self.executor_enabled:
                        self.executor_btn.setText("🎮 Остановить исполнитель")
                        self.statusBar().showMessage("Автоматический исполнитель ВКЛЮЧЕН")
                    else:
                        self.executor_btn.setText("🎮 Запустить исполнитель")
                        self.statusBar().showMessage("Автоматический исполнитель ВЫКЛЮЧЕН")
                
                # Загружаем основные настройки
                self.click_coordinates = tuple(settings.get('click_coordinates', (22, 330)))
                self.check_coords = tuple(settings.get('check_coords', (22, 330)))
                # ... остальные настройки
                    
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек: {e}")
            if hasattr(self, 'executor_btn') and self.executor_btn:
                self.executor_btn.setText("🎮 Запустить исполнитель")

    def load_settings_to_editor(self):
        """Загружает настройки в редактор кнопок"""
        try:
            if hasattr(self, 'editor') and self.editor:
                # Основные настройки
                self.editor.click_coordinates = self.click_coordinates
                self.editor.check_coords = self.check_coords
                self.editor.required_color = self.required_color
                self.editor.zone_center = self.zone_center
                self.editor.zone_color = self.zone_color
                
                # Настройки чата
                self.editor.chat_detection_coords = self.chat_detection_coords
                self.editor.chat_detection_color = self.chat_detection_color
                self.editor.chat_color_tolerance = self.chat_color_tolerance
                self.editor.chat_zone_size = self.chat_zone_size
                self.editor.chat_min_matches = self.chat_min_matches
                self.editor.chat_check_step = self.chat_check_step
                
                logging.info("Настройки загружены в редактор")
                
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек в редактор: {e}")

    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            settings = {
                'executor_enabled': self.executor_enabled,
                'click_coordinates': self.click_coordinates,
                'check_coords': self.check_coords,
                'required_color': self.required_color,
                'zone_center': self.zone_center,
                'zone_color': self.zone_color,
                'chat_detection': {
                    'coords': self.chat_detection_coords,
                    'color': self.chat_detection_color,
                    'tolerance': self.chat_color_tolerance,
                    'zone_size': self.chat_zone_size,
                    'min_matches': self.chat_min_matches,
                    'check_step': self.chat_check_step
                }
            }
            
            settings_path = self.get_settings_path()
            logging.info(f"Сохранение настроек в: {settings_path}")
            
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=2)
                
            logging.info(f"Настройки сохранены, executor_enabled: {self.executor_enabled}")
            
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек: {e}")

    def get_settings_path(self):
        """Возвращает путь к app_settings.json в scripts/settings"""
        try:
            script_dir = Path(__file__).parent / "scripts"
            settings_dir = script_dir / "settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            return settings_dir / "app_settings.json"
        except Exception as e:
            logging.error(f"Ошибка получения пути настроек: {e}")
            return Path("app_settings.json")  # fallback

def closeEvent(self, event):
    """Обработка закрытия приложения"""
    try:
        # Останавливаем слушатель горячих клавиш
        if hasattr(self, 'hotkey_manager'):
            self.hotkey_manager.stop_listener()
    except Exception as e:
        logging.error(f"Ошибка при закрытии: {e}")
    
    super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    
    # Устанавливаем иконку приложения (если есть)
    # app.setWindowIcon(QIcon('icon.png'))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()