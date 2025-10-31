# notification_manager.py
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer
import time

class NotificationManager:
    def __init__(self, parent=None):
        self.parent = parent
        self.notification_timers = {}
        
    def show_temporary_message(self, title, message, duration=2000):
        """Показывает временное сообщение"""
        try:
            msg = QMessageBox(self.parent)
            msg.setWindowTitle(title)
            msg.setText(message)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Автоматическое закрытие через указанное время
            timer = QTimer(self.parent)
            timer.timeout.connect(msg.accept)
            timer.start(duration)
            
            msg.exec()
            
        except Exception as e:
            print(f"Ошибка показа уведомления: {e}")
    
    def show_hotkey_notification(self, action_name, key_sequence):
        """Показывает уведомление о срабатывании горячей клавиши"""
        action_descriptions = {
            "chat_commands": "Чат команды",
            "hints": "Подсказки", 
            "teleports": "Список телепортов"
        }
        
        description = action_descriptions.get(action_name, "Неизвестное действие")
        self.show_temporary_message(
            "Горячая клавиша", 
            f"{description}\n\nАктивирована клавиша: {key_sequence}",
            1500  # 1.5 секунды
        )