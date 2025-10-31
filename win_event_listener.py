# win_event_listener.py
import threading
import time

class WinEventListener(threading.Thread):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.daemon = True
        self.running = True
        
    def run(self):
        prev_state = False
        while self.running:
            current_state = self.editor.is_target_window_active()
            if current_state != prev_state:
                self.editor.check_conditions()
                prev_state = current_state
            time.sleep(0.5)  # Проверяем каждые 500 мс
            
    def stop(self):
        self.running = False