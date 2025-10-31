from PyQt6.QtWidgets import (QWidget, QGridLayout, QPushButton, QScrollArea, 
                           QVBoxLayout, QFrame, QMessageBox, QSizePolicy, QScrollBar)
from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect, QEvent
from PyQt6.QtGui import QKeyEvent, QGuiApplication
from PyQt6.QtCore import QFileSystemWatcher
import os
from PIL import Image
import win32gui
import win32api
import win32con
import win32process
import psutil
from pathlib import Path
import win32clipboard  # Добавлен импорт

import time
import pyautogui
import random
import win32gui
import ctypes  # Для проверки раскладки

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='button_executor.log'
)

class ButtonExecutor(QWidget):
    button_clicked = pyqtSignal(str, str)
    
    def __init__(self, button_data, parent=None):
        super().__init__(parent)
        
        # Устанавливаем флаги окна отдельно
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
        self.button_height = 20
        self._parent = parent
        
        self.setMouseTracking(True)
        self.mouse_over = False
        
        self.load_width_from_file()
        self.setup_ui()
        
        # Устанавливаем стиль и прозрачность
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            background: rgba(30, 30, 30, 220);
            border-radius: 5px;
            border: 1px solid #444;
        """)
        
        # Вызываем метод для правильного позиционирования
        self.adjust_to_screen()
        self.drag_start_position = QPoint()
        self.original_pos = QPoint()
        
    def check_keyboard_layout(self):
        """Проверяет текущую раскладку клавиатуры (0x409 - английская)"""
        try:
            hkl = ctypes.windll.user32.GetKeyboardLayout(0)
            lid = hkl & 0xFFFF
            return lid == 0x409  # Английская раскладка
        except:
            return False
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Основной контейнер (переименовываем buttons_area в container для совместимости)
        self.container = QWidget()
        self.buttons_layout = QGridLayout(self.container)
        self.buttons_layout.setContentsMargins(5, 5, 5, 5)
        self.buttons_layout.setHorizontalSpacing(15)
        self.buttons_layout.setVerticalSpacing(5)  # Меньшее расстояние между строками

        # Горизонтальный скроллбар
        self.h_scroll = QScrollBar(Qt.Orientation.Horizontal)
        self.h_scroll.setStyleSheet("""
            QScrollBar:horizontal {
                background: #2A2A2A;
                height: 12px;
                margin: 5px 0 0 0;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #555;
                min-width: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 10px;
                background: none;
            }
        """)

        self.container = QWidget()
        self.buttons_layout = QGridLayout(self.container)
        self.buttons_layout.setContentsMargins(5, 5, 5, 5)
        self.buttons_layout.setHorizontalSpacing(15)
        self.buttons_layout.setVerticalSpacing(5)
        main_layout.addWidget(self.container)
        main_layout.addWidget(self.h_scroll)

        self.click_coordinates = (22, 330)
        self.max_rows_per_column = 9
        self.current_columns = 1

        self.setup_scrollbars()
        self.create_buttons()



    def setup_scrollbars(self):
    # Связываем горизонтальный скроллбар с областью кнопок
        self.container.installEventFilter(self)
        self.h_scroll.valueChanged.connect(self.scroll_buttons)

    def scroll_buttons(self, value):
        # Прокрутка кнопок по горизонтали
        self.container.move(-value, self.container.y())

    def eventFilter(self, obj, event):
        if obj == self.container and event.type() == QEvent.Type.Resize:
            # Обновляем диапазон скроллбара
            content_width = self.container.width()
            viewport_width = self.width() - 10  # Ширина окна минус отступы
            
            if content_width > viewport_width:
                self.h_scroll.setRange(0, content_width - viewport_width)
                self.h_scroll.setPageStep(viewport_width)
                self.h_scroll.setSingleStep(20)
            else:
                self.h_scroll.setRange(0, 0)
        return super().eventFilter(obj, event)

    def open_chat_checker(self):
        """Открывает окно для настройки точки обнаружения чата"""
        if hasattr(self._parent, 'open_chat_checker_analyzer'):
            self._parent.open_chat_checker_analyzer()
        else:
            QMessageBox.information(self, "Информация", 
                                "Функция настройки точки чата доступна из главного меню")

    def adjust_to_screen(self):
        """Адаптирует размер и позицию окна под текущий монитор"""
        # Получаем геометрию экрана
        screen = QGuiApplication.primaryScreen().availableGeometry()
        
        # Рассчитываем размеры (30% ширины экрана, 60% высоты)
        width = int(screen.width() * 0.15)
        height = int(screen.height() * 0.35)

        self.setFixedSize(width, height)
        self.move(
            screen.right() - width - int(screen.width() * 0.17),
            screen.top() + int(screen.height() * 0.01)
        )
        
        # Устанавливаем фиксированный размер
        self.setFixedSize(width, height)
        
        # Позиционируем в правой части экрана с отступом
        right_margin = int(screen.width() * 0.85)  # 2% отступа
        top_margin = int(screen.height() * 0.62)    # 10% сверху
        
        self.move(
            screen.right() - width - right_margin,
            screen.top() + top_margin
        )

    def create_buttons(self):
        # Очищаем layout
        for i in reversed(range(self.buttons_layout.count())): 
            widget = self.buttons_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Создаем кнопки
        for name, data in self.button_data.items():
            btn = QPushButton(name)
            btn.setFixedSize(self.button_width, self.button_height)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #3A3A3A;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 3px;
                    padding: 5px;
                    font-size: 12px;
                    min-width: {self.button_width}px;
                    max-width: {self.button_width}px;
                    min-height: {self.button_height}px;
                    max-height: {self.button_height}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(68, 68, 68, 220);
                    border: 1px solid #555;
                }}
            """)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            row, col = data.get("position", (0, 0))
            self.buttons_layout.addWidget(btn, row, col)
            # Исправленная строка - передаем description из данных кнопки
            btn.clicked.connect(lambda checked, n=name, d=data["description"]: 
                            self.send_text_to_cursor(n, d))

        self.update_container_size()

    def send_text_to_cursor(self, name, description):
        self._parent.save_mouse_position()
        try:
            text_to_send = description
            count_report = False
            
            if hasattr(self._parent, 'advanced_settings') and name in self._parent.advanced_settings:
                settings = self._parent.advanced_settings[name]
                if settings['response_count'] > 1 and settings['responses']:
                    valid_responses = [r for r in settings['responses'] if r.strip()]
                    if valid_responses:
                        text_to_send = random.choice(valid_responses)
                    count_report = settings.get('count_reports', False)

            if not text_to_send.strip():
                return

            # Проверяем раскладку клавиатуры
            if not self.check_keyboard_layout():
                logging.info("Раскладка клавиатуры не английская - переключаем")
                win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.01)

            # Сохраняем текущий буфер обмена
            try:
                win32clipboard.OpenClipboard()
                original_clipboard = win32clipboard.GetClipboardData()
            except:
                original_clipboard = ""
            finally:
                win32clipboard.CloseClipboard()

            # Копируем текст в буфер обмена
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text_to_send, win32con.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()

            # Кликаем по координатам (вместо поиска RAGE окна)
            self._parent.mouse_click(1405, 1033)  # Клик по полю ввода
            self._parent.restore_mouse_position()
            
            # Вставляем текст (Ctrl+V)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Проверяем, что текст вставился корректно
            self._verify_inserted_text(text_to_send)

            # Нажатие стрелки вправо
            win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            # Если нужно - отправляем Enter
            if (hasattr(self._parent, 'advanced_settings') and 
                name in self._parent.advanced_settings and
                self._parent.advanced_settings[name]['auto_enter']):
                time.sleep(0.01)
                win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
                time.sleep(0.01)
                win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            if count_report:
                try:
                    script_dir = Path(__file__).parent
                    settings_dir = script_dir / "settings"
                    settings_dir.mkdir(parents=True, exist_ok=True)
                    
                    tmp_path = settings_dir / "report_counter.tmp"
                    with open(tmp_path, 'w') as f:
                        f.write('+1')
                    print(f"[DEBUG] Создан tmp файл: {tmp_path}")
                except Exception as e:
                    logging.error(f"Ошибка при обновлении счетчика: {e}")

            # Восстанавливаем буфер обмена
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_clipboard)
            finally:
                win32clipboard.CloseClipboard()
            
        except Exception as e:
            logging.error(f"Ошибка при отправке текста: {e}")
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_clipboard)
            except:
                pass
            finally:
                win32clipboard.CloseClipboard()

    def _verify_inserted_text(self, expected_text):
        """Проверяет, что текст вставился корректно"""
        try:
            # Получаем текст из поля ввода (через Ctrl+A, Ctrl+C)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('A'), 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(ord('A'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)
            
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('C'), 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.1)
            
            # Получаем текст из буфера обмена
            try:
                win32clipboard.OpenClipboard()
                inserted_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            except TypeError:
                # Если не удалось получить как Unicode, пробуем как текст
                try:
                    inserted_text = win32clipboard.GetClipboardData(win32con.CF_TEXT)
                    if isinstance(inserted_text, bytes):
                        inserted_text = inserted_text.decode('cp1251')
                except:
                    inserted_text = ""
            finally:
                win32clipboard.CloseClipboard()
                
            # Нормализуем строки для сравнения
            expected_normalized = expected_text.strip().lower()
            inserted_normalized = inserted_text.strip().lower()
            
            if inserted_normalized != expected_normalized:
                logging.error(f"Текст не совпадает! Ожидалось: '{expected_text}', получено: '{inserted_text}'")
                return False
            return True
        except Exception as e:
            logging.error(f"Ошибка при проверке вставленного текста: {e}")
            return False

    def click_at_normalized_coords(self, x, y):
        """Выполняет клик по нормализованным координатам."""
        try:
            normalized_x, normalized_y = self.parent.normalize_coordinates(x, y)
            pyautogui.click(normalized_x, normalized_y)
        except Exception as e:
            logging.error(f"Ошибка при клике: {e}")

    def update_container_size(self):
        # Рассчитываем размеры контента
        visible_rows = min(len(self.button_data), self.max_rows_per_column)
        content_height = (visible_rows * self.button_height + 
                        (visible_rows - 1) * self.buttons_layout.verticalSpacing() + 
                        self.buttons_layout.contentsMargins().top() + 
                        self.buttons_layout.contentsMargins().bottom())
        
        columns = max(1, (len(self.button_data) + self.max_rows_per_column - 1) // self.max_rows_per_column)
        content_width = (columns * self.button_width + 
                        (columns - 1) * self.buttons_layout.horizontalSpacing() + 
                        self.buttons_layout.contentsMargins().left() + 
                        self.buttons_layout.contentsMargins().right())
        
        # Устанавливаем минимальный размер для container
        self.container.setMinimumSize(content_width, content_height)
        
        # Обновляем диапазон скроллбара
        viewport_width = self.width() - 10
        if content_width > viewport_width:
            self.h_scroll.setRange(0, content_width - viewport_width)
            self.h_scroll.setPageStep(viewport_width)
        else:
            self.h_scroll.setRange(0, 0)

    def update_buttons(self, button_data):
        self.button_data = button_data
        self.create_buttons()
        self.update_container_size()

    def reload_buttons(self):
        parent = self._parent
        if parent:
            parent.load_buttons_from_file()
            self.update_buttons(parent.button_data)

    def update_buttons_width(self, width):
        self.button_width = width
        for name, data in self.button_data.items():
            btn = self.buttons_layout.itemAtPosition(data["position"][0], 
                                                data["position"][1]).widget()
            if btn:
                btn.setFixedWidth(width)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #3A3A3A;
                        color: white;
                        border: 1px solid #444;
                        border-radius: 3px;
                        padding: 5px;
                        font-size: 12px;
                        min-width: {width}px;
                        max-width: {width}px;
                        min-height: {self.button_height}px;
                        max-height: {self.button_height}px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(68, 68, 68, 220);
                        border: 1px solid #555;
                    }}
                """)
        self.update_container_size()

    def load_width_from_file(self):
        width_file = "button_width.cfg"
        if os.path.exists(width_file):
            try:
                with open(width_file, 'r') as f:
                    self.button_width = int(f.read().strip())
            except Exception as e:
                logging.info(f"Ошибка загрузки ширины: {e}")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.mouse_over = False  # Сбрасываем флаг при закрытии
        if self._parent and hasattr(self._parent, 'executor_window'):
            self._parent.executor_window = None
        event.accept()

    def check_screen_color(self):
        if not hasattr(self, '_parent') or not self._parent:
            logging.info("No parent for color check")
            return False
        result = self._parent.check_screen_color()
        logging.info(f"Color check result: {result}")
        return result
    
    def mouseMoveEvent(self, event):
        """Закрываем окно если пропал нужный цвет"""
        if hasattr(self, '_parent') and self._parent:
            if not self._parent.check_screen_color():
                self.hide()
        super().mouseMoveEvent(event)

    def enterEvent(self, event):
        """Мышь вошла в область виджета"""
        self.mouse_over = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Мышь покинула область виджета"""
        self.mouse_over = False
        # При уходе мыши сразу проверяем условия
        if self._parent:
            self._parent.check_conditions()
        super().leaveEvent(event)

    def _send_single_response(self, text):
        """Отправляет один ответ в чат RAGE Multiplayer"""
        try:
            # Сохраняем текущий буфер обмена с win32clipboard
            try:
                win32clipboard.OpenClipboard()
                original_clipboard = win32clipboard.GetClipboardData()
            finally:
                win32clipboard.CloseClipboard()
            
            # Копируем текст в буфер обмена
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text)
            finally:
                win32clipboard.CloseClipboard()
            
            # Даем время для обработки буфера обмена
            time.sleep(0.2)
            
            # Активируем окно RAGE Multiplayer
            try:
                window = win32gui.FindWindow(None, "RAGE Multiplayer")
                if window:
                    win32gui.SetForegroundWindow(window)
                    time.sleep(0.2)
            except Exception as e:
                logging.info(f"Ошибка активации окна: {e}")
            
            # Эмулируем вставку через Ctrl+V
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('V'), 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            # Восстанавливаем оригинальный буфер обмена
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_clipboard)
            finally:
                win32clipboard.CloseClipboard()
            
        except Exception as e:
            logging.info(f"Ошибка отправки текста: {e}")
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_clipboard)
            except:
                pass
            finally:
                win32clipboard.CloseClipboard()

    def focusInEvent(self, event):
        # Игнорируем событие получения фокуса
        event.ignore()

    def focusOutEvent(self, event):
        # Игнорируем событие потери фокуса
        event.ignore()

    def mousePressEvent(self, event):
        # Часть 1: Обработка проверки зоны (работает всегда)
        
        # Часть 2: Стандартная обработка (с игнорированием)
        event.ignore()
        super().mousePressEvent(event)