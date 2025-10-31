import os
import json
import sys
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
import pyautogui

class ReportLabel(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QLabel {
                color: red;
                font-size: 48px;
                font-weight: bold;
                background-color: rgba(30, 30, 30, 150);
                padding: 10px;
                border-radius: 5px;
            }
        """)
        
        self.report_count = 0
        self.load_counter()  # Загружаем сохраненный счетчик
        self.label = QLabel(self)
        self.update_label()  # Обновляем текст с текущим счетчиком
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize(300, 80)
        self.move_to_corner()
        
        # Настройки проверки
        self.check_coords = (45, 380)
        self.target_color = (51, 59, 71)
        self.color_tolerance = 10
        
        # Таймеры
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_conditions)
        self.timer.start(500)

        self.counter_timer = QTimer(self)
        self.counter_timer.timeout.connect(self.check_counter)
        self.counter_timer.start(300)

        # Для двойного клика
        self.last_click_time = 0

    def mousePressEvent(self, event):
        current_time = QTimer.currentTime()
        if current_time - self.last_click_time < 300:  # 300ms для двойного клика
            self.report_count = 0
            self.update_label()
            self.save_counter()
        self.last_click_time = current_time
        super().mousePressEvent(event)

    def get_data_path(self, filename):
        """Возвращает полный путь к файлу данных в папке scripts/settings"""
        # ИСПРАВЛЕННЫЙ ПУТЬ - убираем лишнюю папку scripts
        base_path = Path(__file__).parent.parent  # Переходим на уровень выше
        settings_dir = base_path / "scripts" / "settings"
        settings_dir.mkdir(parents=True, exist_ok=True)
        
        return settings_dir / filename

    def load_counter(self):
        """Загружает счетчик из файла"""
        try:
            path = self.get_data_path('report_counter.json')
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.report_count = data.get('count', 0)
                    print(f"Загружен счетчик: {self.report_count}")  # Для отладки
        except Exception as e:
            print(f"Ошибка загрузки счетчика: {e}")

    def save_counter(self):
        """Сохраняет счетчик в файл"""
        try:
            path = self.get_data_path('report_counter.json')
            print(f"[DEBUG] Сохранение в: {path}")
            
            # Проверяем доступность папки для записи
            if not path.parent.exists():
                print(f"[ERROR] Папка {path.parent} не существует!")
                return
                
            with open(path, 'w') as f:
                json.dump({'count': self.report_count}, f)
                print(f"[DEBUG] Счетчик {self.report_count} успешно сохранен")
                
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения счетчика: {str(e)}")

    def check_counter(self):
        """Проверяет команды для счетчика"""
        try:
            path = self.get_data_path('report_counter.tmp')
            if path.exists():
                try:
                    with open(path, 'r+') as f:
                        content = f.read().strip()
                        if content == '+1':
                            self.report_count += 1
                            self.update_label()
                            self.save_counter()
                            print(f"[DEBUG] Счетчик увеличен: {self.report_count}")
                        
                        # Очищаем файл только если он содержит +1
                        if content:
                            f.seek(0)
                            f.truncate()
                except PermissionError:
                    print("[WARNING] Файл занят, пропускаем итерацию")
                    return
        except Exception as e:
            print(f"[ERROR] Ошибка обработки счетчика: {str(e)}")

    def update_label(self):
        """Обновляет текст метки"""
        self.label.setText(f"РЕПОРТ: {self.report_count}")

    def move_to_corner(self):
        screen = QGuiApplication.primaryScreen().geometry()

        width = int(screen.width() * 0.1)
        height = int(screen.height() * 0.35)

        # Позиционируем в правой части экрана с отступом
        right_margin = int(screen.width() * 0.05)  # 2% отступа
        top_margin = int(screen.height() * 0.01)    # 10% сверху
        
        self.move(
            screen.right() - width - right_margin,
            screen.top() + top_margin
        )

    def check_conditions(self):
        try:
            x, y = self.check_coords
            pixel = pyautogui.pixel(x, y)
            color_match = all(abs(p - t) <= self.color_tolerance 
                           for p, t in zip(pixel, self.target_color))
            self.setVisible(color_match)
        except:
            self.setVisible(False)

if __name__ == "__main__":
    app = QApplication([])
    window = ReportLabel()
    sys.exit(app.exec())