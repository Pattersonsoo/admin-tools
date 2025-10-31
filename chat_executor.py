from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QScrollArea, 
                           QVBoxLayout, QFrame, QMessageBox, QSizePolicy, QScrollBar)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect, QEvent, QTimer
from PyQt6.QtGui import QGuiApplication, QShortcut, QKeySequence
from PyQt6.QtCore import QFileSystemWatcher
import os
import numpy as np
from PIL import Image
import win32gui
import win32api
import win32con
import win32process
import psutil
from pathlib import Path
import win32clipboard
from pynput import keyboard as pynput_keyboard
import time
import pyautogui
import random
import win32gui
import ctypes

import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chat_executor.log'
)

class ChatExecutor(QWidget):
    button_clicked = pyqtSignal(str, str)
    
    def __init__(self, button_data, parent=None):
        super().__init__(parent)
        
        # Устанавливаем флаги окна
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self.reload_buttons)
        self.button_data = button_data
        self.button_width = 120
        self.button_height = 30
        
        self._parent = parent
        
        self.setMouseTracking(True)
        self.mouse_over = False
        
        self.setup_ui()
        
        # Загружаем настройки обнаружения чата из файла
        self.chat_detection_coords = (0, 0)
        self.chat_detection_color = (0, 0, 0)
        self.chat_color_tolerance = 10
        self.zone_size = 15
        self.min_matches_required = 3
        self.check_step = 3
        
        self.load_chat_detection_settings()
        
        # Таймеры для проверки условий
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_chat_conditions)
        self.check_timer.setInterval(1500)
        
        self.cursor_check_timer = QTimer(self)
        self.cursor_check_timer.timeout.connect(self.check_cursor_appearance)
        self.cursor_check_timer.setInterval(300)
        
        self.should_be_visible = False
        self._last_geometry_log = 0
        self._last_debug_log = 0

        self.hotkey_listener = None
        self.setup_qt_hotkeys()
        
        # Устанавливаем стиль и прозрачность
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            background: rgba(42, 75, 124, 220);
            border-radius: 5px;
            border: 1px solid #3A5B8C;
        """)
        
        # Позиционируем окно
        self.adjust_to_screen()
        self.drag_start_position = QPoint()
        self.original_pos = QPoint()
        
        # Состояние активации проверки
        self.checking_active = False
        
        # Кэш для оптимизации
        self.cursor_cache = {
            'last_check': 0,
            'cursor_visible': False,
            'last_cursor_type': None,
            'cursor_types_found': set()
        }
        
    def setup_qt_hotkeys(self):
        """Настраивает обработку горячих клавиш через QShortcut"""
        try:
            # Горячие клавиши для активации проверки чата (Е/T)
            self.activate_shortcut_e = QShortcut(QKeySequence("Е"), self)
            self.activate_shortcut_t = QShortcut(QKeySequence("T"), self)
            self.activate_shortcut_e2 = QShortcut(QKeySequence("т"), self)
            self.activate_shortcut_t2 = QShortcut(QKeySequence("e"), self)
            
            # Подключаем все варианты к активации проверки
            self.activate_shortcut_e.activated.connect(self.activate_chat_checking)
            self.activate_shortcut_t.activated.connect(self.activate_chat_checking)
            self.activate_shortcut_e2.activated.connect(self.activate_chat_checking)
            self.activate_shortcut_t2.activated.connect(self.activate_chat_checking)
            
            # Горячие клавиши для деактивации проверки (ESC/Enter)
            self.deactivate_shortcut_esc = QShortcut(QKeySequence("Escape"), self)
            self.deactivate_shortcut_enter = QShortcut(QKeySequence("Return"), self)
            self.deactivate_shortcut_enter2 = QShortcut(QKeySequence("Enter"), self)
            
            # Подключаем деактивацию
            self.deactivate_shortcut_esc.activated.connect(self.deactivate_chat_checking)
            self.deactivate_shortcut_enter.activated.connect(self.deactivate_chat_checking)
            self.deactivate_shortcut_enter2.activated.connect(self.deactivate_chat_checking)
            
            # Отладочные комбинации
            self.debug_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
            self.debug_shortcut.activated.connect(self.debug_current_color)
            
            self.debug_cursor_shortcut = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
            self.debug_cursor_shortcut.activated.connect(self.debug_cursor_info)
            
            logging.info("✅ Горячие клавиши настроены")
            
        except Exception as e:
            logging.error(f"❌ Ошибка настройки горячих клавиш: {e}")
    
    def activate_chat_checking(self):
        """Активирует проверку чата по горячей клавише Е/T"""
        if not self.checking_active:
            self.checking_active = True
            self.check_timer.start()
            self.cursor_check_timer.start()
            logging.info("🎯 АКТИВИРОВАНА ПРОВЕРКА ЧАТА (Е/T)")
            
            # Визуальная обратная связь
            self.flash_window()
            
            # Сразу делаем первую проверку
            self.check_chat_conditions()
    
    def deactivate_chat_checking(self):
        """Деактивирует проверку чата по горячей клавише ESC/Enter"""
        if self.checking_active:
            self.checking_active = False
            self.check_timer.stop()
            self.cursor_check_timer.stop()
            logging.info("⏹️ ПРОВЕРКА ЧАТА ОСТАНОВЛЕНА (ESC/Enter)")
            
            # Скрываем окно если оно видимо
            if self.isVisible() and not self.mouse_over:
                self.hide()
                logging.info("📱 Окно чат-команд скрыто")
    
    def flash_window(self):
        """Мигание окна для визуальной обратной связи"""
        try:
            original_style = self.styleSheet()
            self.setStyleSheet("""
                background: rgba(255, 165, 0, 220);
                border-radius: 5px;
                border: 2px solid #FF5722;
            """)
            QTimer.singleShot(200, lambda: self.setStyleSheet(original_style))
        except Exception as e:
            logging.error(f"Ошибка при мигании окна: {e}")
    
    def check_chat_conditions(self):
        """Проверяет условия для открытия чат-команд"""
        if not self.checking_active:
            return
            
        try:
            # Если мышь над окном - не скрываем
            if self.mouse_over:
                return
                
            # Комбинированная проверка: курсор + геометрия + цвет
            cursor_detected = self.cursor_cache.get('cursor_visible', False)
            geometry_detected = self.detect_chat_by_geometry()
            color_detected = self.check_chat_zone()
            
            # Чат открыт если обнаружен любой из признаков
            chat_opened = cursor_detected or geometry_detected or color_detected
            
            # Логируем для отладки
            if hasattr(self, '_last_check_log') and time.time() - self._last_check_log > 3:
                logging.info(f"🔍 Проверка: курсор={cursor_detected}, геометрия={geometry_detected}, цвет={color_detected}")
                self._last_check_log = time.time()
            
            # Обновляем видимость только при изменении состояния
            if chat_opened != self.should_be_visible:
                self.should_be_visible = chat_opened
                self.update_visibility()
                
        except Exception as e:
            logging.error(f"❌ Ошибка в check_chat_conditions: {e}")
    
    def check_cursor_appearance(self):
        """Проверка появления курсоров в области чата"""
        try:
            current_time = time.time()
            
            # Кэшируем проверки
            if current_time - self.cursor_cache['last_check'] < 0.2:
                return
                
            self.cursor_cache['last_check'] = current_time
            
            # Проверяем курсор в области чата
            cursor_in_chat_area = self.detect_cursor_in_chat_area()
            
            # Обновляем кэш
            self.cursor_cache['cursor_visible'] = cursor_in_chat_area
            
        except Exception as e:
            logging.error(f"❌ Ошибка проверки курсора: {e}")
    
    def detect_cursor_in_chat_area(self):
        """Обнаруживает курсоры в области чата"""
        try:
            # Получаем информацию о курсоре
            cursor_info = win32gui.GetCursorInfo()
            if not cursor_info:
                return False
            
            # Получаем позицию курсора
            cursor_pos = win32gui.GetCursorPos()
            if not cursor_pos:
                return False
            
            cursor_x, cursor_y = cursor_pos
            
            # Определяем область вокруг ожидаемой позиции чата
            chat_x, chat_y = self.chat_detection_coords
            search_width, search_height = 400, 200
            
            left = max(0, chat_x - search_width // 2)
            top = max(0, chat_y - search_height // 2)
            right = left + search_width
            bottom = top + search_height
            
            # Проверяем находится ли курсор в области чата
            cursor_in_area = (left <= cursor_x <= right and top <= cursor_y <= bottom)
            
            if not cursor_in_area:
                return False
            
            # Анализируем тип курсора
            cursor_handle, cursor_type = cursor_info[1], cursor_info[2]
            
            # Сохраняем обнаруженные типы курсоров для отладки
            if cursor_type not in self.cursor_cache['cursor_types_found']:
                self.cursor_cache['cursor_types_found'].add(cursor_type)
            
            # Проверяем типы курсоров, характерные для полей ввода
            is_input_cursor = self.is_input_cursor_type(cursor_handle, cursor_type)
            
            return is_input_cursor
            
        except Exception as e:
            logging.error(f"❌ Ошибка обнаружения курсора: {e}")
            return False
    
    def is_input_cursor_type(self, cursor_handle, cursor_type):
        """Определяет является ли курсор курсором ввода текста"""
        try:
            # Стандартные типы курсоров Windows для полей ввода
            input_cursor_types = {
                32512,  # IDC_ARROW - обычная стрелка
                32513,  # IDC_IBEAM - I-образный курсор ввода текста
                32514,  # IDC_WAIT - курсор ожидания
                32515,  # IDC_CROSS - крестообразный курсор
                32650,  # IDC_HAND - рука (для ссылок)
            }
            
            # Проверяем по типу
            if cursor_type in input_cursor_types:
                # Для стрелки дополнительно проверяем фон
                if cursor_type == 32512:  # IDC_ARROW
                    try:
                        cursor_pos = win32gui.GetCursorPos()
                        pixel_color = pyautogui.pixel(cursor_pos[0], cursor_pos[1])
                        brightness = sum(pixel_color) / 3
                        # Поле ввода обычно имеет светлый фон
                        return brightness > 150
                    except:
                        return False
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"❌ Ошибка определения типа курсора: {e}")
            return False

    def detect_chat_by_geometry(self):
        """Обнаруживает чат по геометрическим признакам"""
        try:
            x, y = self.chat_detection_coords
            search_width, search_height = 900, 300
            
            # Рассчитываем область поиска
            left = max(0, x - search_width // 2)
            top = max(0, y - search_height // 2)
            
            region = (left, top, search_width, search_height)
            screenshot = pyautogui.screenshot(region=region)
            
            # Конвертируем в grayscale для упрощения анализа
            grayscale = screenshot.convert('L')
            
            # Ищем прямоугольные области (поля ввода чата)
            input_fields = self.find_input_fields(grayscale, search_width, search_height)
            
            # Логируем для отладки
            if hasattr(self, '_last_geometry_log') and time.time() - self._last_geometry_log > 5:
                logging.info(f"🔍 Геометрия: найдено {input_fields} полей ввода")
                self._last_geometry_log = time.time()
            
            return input_fields >= 1
            
        except Exception as e:
            logging.error(f"❌ Ошибка обнаружения по геометрии: {e}")
            return False

    def find_input_fields(self, image, width, height):
        """Находит прямоугольные поля ввода в изображении"""
        pixels = list(image.getdata())
        input_fields = 0
        
        # Ищем характерные паттерны полей ввода
        horizontal_lines = self.detect_horizontal_lines(pixels, width, height)
        vertical_lines = self.detect_vertical_lines(pixels, width, height)
        rectangles = self.detect_rectangles(pixels, width, height)
        
        # Комбинируем результаты
        if horizontal_lines >= 2 and vertical_lines >= 2:
            input_fields += 1
        if rectangles >= 1:
            input_fields += 1
        
        return min(input_fields, 2)

    def detect_horizontal_lines(self, pixels, width, height):
        """Обнаруживает горизонтальные линии"""
        lines_found = 0
        line_threshold = width * 0.4
        
        for y in range(5, height - 5):
            line_length = 0
            max_line_length = 0
            
            for x in range(width):
                idx = y * width + x
                brightness = pixels[idx]
                
                if brightness < 50 or brightness > 200:
                    line_length += 1
                    max_line_length = max(max_line_length, line_length)
                else:
                    line_length = 0
            
            if max_line_length >= line_threshold:
                lines_found += 1
        
        return lines_found

    def detect_vertical_lines(self, pixels, width, height):
        """Обнаруживает вертикальные линии"""
        lines_found = 0
        line_threshold = height * 0.3
        
        for x in range(5, width - 5):
            line_length = 0
            max_line_length = 0
            
            for y in range(height):
                idx = y * width + x
                brightness = pixels[idx]
                
                if brightness < 50 or brightness > 200:
                    line_length += 1
                    max_line_length = max(max_line_length, line_length)
                else:
                    line_length = 0
            
            if max_line_length >= line_threshold:
                lines_found += 1
        
        return lines_found

    def detect_rectangles(self, pixels, width, height):
        """Обнаруживает прямоугольные области"""
        rectangles = 0
        
        # Ищем углы прямоугольников
        corners = self.find_corners(pixels, width, height)
        
        if corners >= 4:
            rectangles += 1
        
        # Ищем области с резкими границами
        bounded_areas = self.find_bounded_areas(pixels, width, height)
        rectangles += bounded_areas
        
        return rectangles

    def find_corners(self, pixels, width, height):
        """Находит углы прямоугольников"""
        corners = 0
        
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                idx = y * width + x
                current = pixels[idx]
                
                # Проверяем соседей
                left = pixels[idx - 1]
                right = pixels[idx + 1]
                top = pixels[idx - width]
                bottom = pixels[idx + width]
                
                horizontal_contrast = abs(left - right) > 50
                vertical_contrast = abs(top - bottom) > 50
                
                if horizontal_contrast and vertical_contrast:
                    corners += 1
        
        return corners

    def find_bounded_areas(self, pixels, width, height):
        """Находит области ограниченные контрастными границами"""
        bounded_areas = 0
        
        for y in range(10, height - 10, 20):
            for x in range(10, width - 10, 20):
                if self.is_bounded_area(pixels, width, height, x, y):
                    bounded_areas += 1
        
        return min(bounded_areas, 2)

    def is_bounded_area(self, pixels, width, height, start_x, start_y):
        """Проверяет является ли область ограниченной"""
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        boundaries_found = 0
        
        for dx, dy in directions:
            x, y = start_x, start_y
            boundary_found = False
            
            for _ in range(30):
                x += dx
                y += dy
                
                if x < 0 or x >= width or y < 0 or y >= height:
                    break
                
                idx = y * width + x
                brightness = pixels[idx]
                
                start_idx = start_y * width + start_x
                start_brightness = pixels[start_idx]
                
                if abs(brightness - start_brightness) > 80:
                    boundary_found = True
                    break
            
            if boundary_found:
                boundaries_found += 1
        
        return boundaries_found >= 3

    def check_chat_zone(self):
        """Проверяет чат по зоне с умной валидацией цвета"""
        try:
            center_x, center_y = self.chat_detection_coords
            
            # Рассчитываем границы зоны
            half_size = self.zone_size // 2
            left = max(0, center_x - half_size)
            top = max(0, center_y - half_size)
            
            matches_found = 0
            total_checked = 0
            confidence_scores = []
            
            # Проверяем точки в зоне
            for x in range(left, left + self.zone_size, self.check_step):
                for y in range(top, top + self.zone_size, self.check_step):
                    try:
                        screenshot = pyautogui.screenshot(region=(x, y, 1, 1))
                        pixel_color = screenshot.getpixel((0, 0))
                        
                        color_match = self.is_color_similar(pixel_color, self.chat_detection_color)
                        
                        if color_match:
                            matches_found += 1
                            confidence = self.calculate_color_confidence(pixel_color, self.chat_detection_color)
                            confidence_scores.append(confidence)
                        
                        total_checked += 1
                        
                    except Exception:
                        continue
            
            # Динамическое определение порога
            if confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                dynamic_threshold = max(1, int(self.min_matches_required * (1 - avg_confidence / 100)))
            else:
                dynamic_threshold = self.min_matches_required
            
            result = matches_found >= dynamic_threshold
            
            # Логируем для отладки
            if hasattr(self, '_last_debug_log') and time.time() - self._last_debug_log > 2:
                logging.info(f"🔍 Зона чата: {matches_found}/{total_checked} совпадений")
                self._last_debug_log = time.time()
                
            return result
            
        except Exception as e:
            logging.error(f"❌ Ошибка проверки зоны чата: {e}")
            return False

    def calculate_color_confidence(self, color1, color2):
        """Вычисляет уверенность в совпадении цветов"""
        max_deviation = max(abs(c1 - c2) for c1, c2 in zip(color1, color2))
        confidence = max(0, 100 - (max_deviation * 100 / self.chat_color_tolerance))
        return confidence
        
    def is_color_similar(self, color1, color2, tolerance=None):
        """Проверяет схожесть цветов"""
        if tolerance is None:
            tolerance = self.chat_color_tolerance
        
        # Простое сравнение по компонентам
        simple_match = all(abs(c1 - c2) <= tolerance for c1, c2 in zip(color1, color2))
        
        if simple_match:
            return True
        
        # Евклидово расстояние
        distance = sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)) ** 0.5
        euclidean_match = distance <= (tolerance * 1.7)
        
        # Учет яркости
        brightness1 = sum(color1) / 3
        brightness2 = sum(color2) / 3
        brightness_match = abs(brightness1 - brightness2) <= tolerance
        
        return simple_match or euclidean_match or brightness_match

    def update_visibility(self):
        """Обновляет видимость окна"""
        if self.should_be_visible:
            if self.isHidden():
                self.show()
                logging.info("📱 Чат открыт - показываем окно чат-команд")
        else:
            if self.isVisible() and not self.mouse_over:
                self.hide()
                logging.info("📱 Чат закрыт - скрываем окно чат-команд")
    
    def update_chat_detection_settings(self, coords, color, tolerance=10):
        """Обновляет настройки обнаружения чата"""
        self.chat_detection_coords = coords
        self.chat_detection_color = color
        self.chat_color_tolerance = tolerance
        logging.info(f"Обновлены настройки чата: {coords} - {color}")

    def send_chat_command(self, name, command):
        """Отправляет чат команду в игру"""
        try:
            # Сохраняем текущий буфер обмена
            try:
                win32clipboard.OpenClipboard()
                original_clipboard = win32clipboard.GetClipboardData()
            except:
                original_clipboard = ""
            finally:
                win32clipboard.CloseClipboard()

            # Копируем команду в буфер обмена
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(command, win32con.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()

            # Активируем игровое окно и вставляем команду
            time.sleep(0.1)
            
            # Вставляем текст (Ctrl+V)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            # Отправляем команду (Enter)
            time.sleep(0.05)
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Восстанавливаем буфер обмена
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_clipboard)
            finally:
                win32clipboard.CloseClipboard()
            
            logging.info(f"Отправлена команда: {command}")
            
        except Exception as e:
            logging.error(f"Ошибка при отправке команды: {e}")
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_clipboard)
            except:
                pass
            finally:
                win32clipboard.CloseClipboard()

    def update_buttons(self, button_data):
        self.button_data = button_data
        self.create_buttons()

    def reload_buttons(self):
        if self._parent:
            if hasattr(self._parent, 'load_chat_commands'):
                self._parent.load_chat_commands()
                self.update_buttons(self._parent.chat_button_data)

    def enterEvent(self, event):
        """Мышь вошла в область виджета"""
        self.mouse_over = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Мышь покинула область виджета"""
        self.mouse_over = False
        super().leaveEvent(event)

    def debug_current_color(self):
        """Показывает текущий цвет в указанных координатах"""
        try:
            x, y = self.chat_detection_coords
            
            screenshot = pyautogui.screenshot(region=(x-1, y-1, 3, 3))
            center_color = screenshot.getpixel((1, 1))
            
            logging.info("🎨 ТЕКУЩИЙ ЦВЕТ ДЛЯ ОТЛАДКИ:")
            logging.info(f"📍 Координаты: ({x}, {y})")
            logging.info(f"🟦 Текущий цвет: {center_color}")
            logging.info(f"🟥 Ожидаемый цвет: {self.chat_detection_color}")
            logging.info(f"📏 Допуск: {self.chat_color_tolerance}")
            
            color_match = all(
                abs(p - c) <= self.chat_color_tolerance 
                for p, c in zip(center_color, self.chat_detection_color)
            )
            
            logging.info(f"🔍 Совпадение: {'ДА' if color_match else 'НЕТ'}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка отладки цвета: {e}")

    def debug_cursor_info(self):
        """Отладочная информация о курсоре"""
        try:
            cursor_info = win32gui.GetCursorInfo()
            cursor_pos = win32gui.GetCursorPos()
            
            chat_x, chat_y = self.chat_detection_coords
            search_width, search_height = 400, 200
            
            in_chat_area = (
                chat_x - search_width//2 <= cursor_pos[0] <= chat_x + search_width//2 and
                chat_y - search_height//2 <= cursor_pos[1] <= chat_y + search_height//2
            )
            
            logging.info("🎯 ОТЛАДКА КУРСОРА:")
            logging.info(f"📍 Позиция: {cursor_pos}")
            logging.info(f"🖱️ Тип: {cursor_info[1] if cursor_info else 'N/A'}")
            logging.info(f"📌 В области чата: {in_chat_area}")
            logging.info(f"📋 Обнаруженные типы: {self.cursor_cache.get('cursor_types_found', set())}")
            
            if in_chat_area and cursor_info:
                try:
                    pixel_color = pyautogui.pixel(cursor_pos[0], cursor_pos[1])
                    brightness = sum(pixel_color) / 3
                    logging.info(f"🎨 Цвет под курсором: {pixel_color}, яркость: {brightness:.1f}")
                except:
                    pass
                    
        except Exception as e:
            logging.error(f"❌ Ошибка отладки курсора: {e}")

    def force_color_check(self):
        """Принудительная проверка цвета"""
        try:
            logging.info("🎯 ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА")
            
            self.flash_window()
            
            chat_opened = self.check_chat_zone()
            
            self.debug_current_color()
            
            if chat_opened:
                if self.isHidden():
                    self.show()
                    logging.info("📱 Окно чат-команд ПОКАЗАНО")
            else:
                if self.isVisible() and not self.mouse_over:
                    self.hide()
                    logging.info("📱 Окно чат-команд СКРЫТО")
                    
        except Exception as e:
            logging.error(f"❌ Ошибка принудительной проверки: {e}")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.mouse_over = False
        self.check_timer.stop()
        self.cursor_check_timer.stop()
        
        if self._parent and hasattr(self._parent, 'chat_executor_window'):
            self._parent.chat_executor_window = None
        event.accept()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Основной контейнер для кнопок
        self.container = QWidget()
        self.buttons_layout = QGridLayout(self.container)
        self.buttons_layout.setContentsMargins(5, 5, 5, 5)
        self.buttons_layout.setHorizontalSpacing(10)
        self.buttons_layout.setVerticalSpacing(8)
        
        main_layout.addWidget(self.container)
        
        self.max_rows = 3
        self.create_buttons()
        
    def adjust_to_screen(self):
        """Адаптирует размер и позицию окна"""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        
        width = int(screen.width() * 0.2)
        height = int(screen.height() * 0.15)

        self.setFixedSize(width, height)
        
        left_margin = int(screen.width() * 0.02)
        top_margin = int(screen.height() * 0.62)
        
        self.move(
            screen.left() + left_margin,
            screen.top() + top_margin
        )

    def create_buttons(self):
        # Очищаем layout
        for i in reversed(range(self.buttons_layout.count())): 
            widget = self.buttons_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        sorted_buttons = list(self.button_data.items())
        row = 0
        col = 0
        
        for name, data in sorted_buttons:
            btn = QPushButton(name)
            btn.setFixedSize(self.button_width, self.button_height)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2A4B7C;
                    color: white;
                    border: 1px solid #3A5B8C;
                    border-radius: 3px;
                    padding: 5px;
                    font-size: 11px;
                    min-width: {self.button_width}px;
                    max-width: {self.button_width}px;
                    min-height: {self.button_height}px;
                    max-height: {self.button_height}px;
                }}
                QPushButton:hover {{
                    background-color: #3A5B9C;
                    border: 1px solid #4A6BAC;
                }}
            """)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            
            self.buttons_layout.addWidget(btn, row, col)
            btn.clicked.connect(lambda checked, n=name, d=data["description"]: 
                              self.send_chat_command(n, d))
            
            col += 1
            if col >= len(sorted_buttons) // self.max_rows + 1:
                col = 0
                row += 1
                if row >= self.max_rows:
                    break

    def load_chat_detection_settings(self):
        """Загружает настройки обнаружения чата из файла"""
        try:
            if hasattr(self, '_parent') and self._parent and hasattr(self._parent, 'settings_dir'):
                settings_dir = self._parent.settings_dir
            else:
                base_path = Path(__file__).parent.parent
                settings_dir = base_path / "scripts" / "settings"
            
            chat_settings_path = settings_dir / "chat_detection_settings.json"
            
            if chat_settings_path.exists():
                with open(chat_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                self.chat_detection_coords = tuple(settings.get('chat_check_coords', (100, 100)))
                self.chat_detection_color = tuple(settings.get('chat_required_color', (68, 80, 95)))
                self.chat_color_tolerance = settings.get('chat_tolerance', 10)
                self.zone_size = settings.get('zone_size', 15)
                self.min_matches_required = settings.get('min_matches_required', 3)
                self.check_step = settings.get('check_step', 3)
                
                logging.info(f"✅ Настройки чата загружены: {self.chat_detection_coords}")
            else:
                self.set_default_chat_settings()
                logging.info("⚠ Используются настройки чата по умолчанию")
                
        except Exception as e:
            logging.error(f"❌ Ошибка загрузки настроек чата: {e}")
            self.set_default_chat_settings()
    
    def set_default_chat_settings(self):
        """Устанавливает настройки по умолчанию"""
        self.chat_detection_coords = (100, 100)
        self.chat_detection_color = (68, 80, 95)
        self.chat_color_tolerance = 15
        self.zone_size = 15
        self.min_matches_required = 3
        self.check_step = 3