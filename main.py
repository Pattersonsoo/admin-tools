import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QEvent
import os
import win32gui
from pynput import keyboard as pynput_keyboard
import threading
from time import time
import ctypes

from .button_editor import ButtonEditor

class GlobalHotkeyManager(QObject):
    toggle_executor_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.listener = None
        self.running = False

    def start(self):
        self.running = True
        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char == 'ё':
                    self.toggle_executor_signal.emit()
                elif hasattr(key, 'vk') and key.vk == 192:  # Английская раскладка
                    self.toggle_executor_signal.emit()
            except Exception as e:
                print(f"Ошибка обработки горячей клавиши: {e}")

        self.listener = pynput_keyboard.Listener(on_press=on_press)  # Явно указываем pynput
        self.listener.start()


    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()

class Application(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.editor = ButtonEditor()
        self.hotkey_manager = GlobalHotkeyManager()
        self.hotkey_manager.toggle_executor_signal.connect(self.editor.toggle_executor)
        self.hotkey_manager.start()
        
        self.editor.show()
        
        # Для оптимизации проверок
        self.last_check_time = 0
        self.check_interval = 0.1  # 100ms между проверками
        
        # Устанавливаем фильтр событий
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseMove:
            current_time = time()
            if current_time - self.last_check_time > self.check_interval:
                self.last_check_time = current_time
                self.handle_window_visibility()
        return super().eventFilter(obj, event)

    def handle_window_visibility(self):
        """Управляет видимостью окна на основе проверок"""
        try:
            # Простая проверка - если цвет совпадает, показываем окно
            color_active = self.check_screen_color()
            
            if color_active:
                if not hasattr(self.editor, 'executor_window') or not self.editor.executor_window:
                    self.editor.open_executor_window()
                elif not self.editor.executor_window.isVisible():
                    self.editor.executor_window.show()
            else:
                if hasattr(self.editor, 'executor_window') and self.editor.executor_window:
                    if not self.editor.executor_window.mouse_over:
                        self.editor.executor_window.hide()
        except Exception as e:
            print(f"Ошибка проверки видимости: {e}")

    def cleanup(self):
        self.hotkey_manager.stop()
        if hasattr(self.editor, 'watcher'):
            self.editor.watcher.deleteLater()

    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = Application(sys.argv)
    app.setStyle("Fusion")
    
    # Обеспечиваем правильное завершение
    app.aboutToQuit.connect(app.cleanup)
    app.editor.show()
    sys.exit(app.exec())