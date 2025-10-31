
import json
import os
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QKeySequence
from pynput import keyboard as pynput_keyboard
import threading
import time
import sys

class HotkeyManager(QObject):
    hotkey_triggered = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.hotkeys = {}
        self.listener = None
        self.running = False
        self.settings_file = self.get_settings_path()
        self.load_hotkeys()

    @property
    def special_keys_mapping(self):
        """Сопоставление специальных клавиш"""
        return {
            'space': '<space>',
            'tab': '<tab>',
            'enter': '<enter>',
            'return': '<enter>',
            'esc': '<esc>',
            'escape': '<esc>',
            'backspace': '<backspace>',
            'delete': '<delete>',
            'insert': '<insert>',
            'home': '<home>',
            'end': '<end>',
            'pageup': '<page_up>',
            'pagedown': '<page_down>',
            'up': '<up>',
            'down': '<down>',
            'left': '<left>',
            'right': '<right>',
            'caps_lock': '<caps_lock>',
            'num_lock': '<num_lock>',
            'scroll_lock': '<scroll_lock>',
        }
    
    def get_settings_path(self):
        """Возвращает путь к файлу настроек горячих клавиш"""
        try:
            if getattr(sys, 'frozen', False):
                # Если приложение собрано в exe
                base_path = Path(sys.executable).parent
            else:
                # Если запуск из исходного кода
                base_path = Path(__file__).parent.parent
            
            settings_dir = base_path / "scripts" / "settings"
            settings_dir.mkdir(parents=True, exist_ok=True)
            return settings_dir / "hotkey_settings.json"
        except Exception as e:
            print(f"Ошибка получения пути настроек: {e}")
            return Path("hotkey_settings.json")  # fallback
    
    def load_hotkeys(self):
        """Загружает горячие клавиши из файла"""
        default_hotkeys = {
            "chat_commands": {"key": "F1", "description": "Открыть чат команды"},
            "hints": {"key": "F2", "description": "Открыть подсказки"},
            "teleports": {"key": "F3", "description": "Открыть список телепортов"}
        }
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.hotkeys = json.load(f)
            else:
                self.hotkeys = default_hotkeys
                self.save_hotkeys()
        except Exception as e:
            print(f"Ошибка загрузки горячих клавиш: {e}")
            self.hotkeys = default_hotkeys
    
    def save_hotkeys(self):
        """Сохраняет горячие клавиши в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.hotkeys, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения горячих клавиш: {e}")
    
    def set_hotkey(self, action, key_sequence):
        """Устанавливает горячую клавишу для действия"""
        self.hotkeys[action] = {
            "key": key_sequence,
            "description": self.hotkeys.get(action, {}).get("description", "Неизвестное действие")
        }
        self.save_hotkeys()
        self.restart_listener()
    
    def get_hotkey_display(self, action):
        """Возвращает отображаемое название горячей клавиши"""
        hotkey = self.hotkeys.get(action, {})
        return hotkey.get("key", "Не назначена")
    
    def get_hotkey_description(self, action):
        """Возвращает описание действия"""
        hotkey = self.hotkeys.get(action, {})
        return hotkey.get("description", "Неизвестное действие")
    
    def start_listener(self):
        """Запускает слушатель горячих клавиш"""
        if self.listener and self.listener.running:
            self.listener.stop()
        
        self.running = True
        self.listener = pynput_keyboard.GlobalHotKeys(self.create_hotkey_map())
        self.listener.start()
    
    def stop_listener(self):
        """Останавливает слушатель горячих клавиш"""
        self.running = False
        if self.listener:
            self.listener.stop()
    
    def restart_listener(self):
        """Перезапускает слушатель"""
        self.stop_listener()
        time.sleep(0.1)
        self.start_listener()
    
    def create_hotkey_map(self):
        """Создает карту горячих клавиш для pynput"""
        hotkey_map = {}
        for action, config in self.hotkeys.items():
            key = config.get("key", "")
            if key:
                # Конвертируем формат горячих клавиш для pynput
                pynput_key = self.convert_to_pynput_format(key)
                if pynput_key:
                    # Создаем замыкание с правильным action
                    hotkey_map[pynput_key] = (lambda act=action: 
                                            lambda: self.on_hotkey_triggered(act))()
        return hotkey_map
    
    def convert_to_pynput_format(self, key_sequence):
        """Конвертирует QKeySequence в формат pynput"""
        try:
            if not key_sequence:
                return None

            # Приводим к нижнему регистру
            key_sequence = key_sequence.lower()
            
            # Простая замена для основных комбинаций
            replacements = {
                'ctrl+': '<ctrl>+',
                'alt+': '<alt>+', 
                'shift+': '<shift>+',
                'space': '<space>',
                'tab': '<tab>',
                'enter': '<enter>',
                'return': '<enter>',
                'esc': '<esc>',
                'escape': '<esc>',
                'backspace': '<backspace>',
                'delete': '<delete>',
                'insert': '<insert>',
                'home': '<home>',
                'end': '<end>',
                'pageup': '<page_up>',
                'pagedown': '<page_down>',
                'up': '<up>',
                'down': '<down>',
                'left': '<left>',
                'right': '<right>',
                
                # Numpad клавиши - pynput использует специальные коды
                'numpad0': '<kp_0>', 'numpad1': '<kp_1>', 'numpad2': '<kp_2>',
                'numpad3': '<kp_3>', 'numpad4': '<kp_4>', 'numpad5': '<kp_5>',
                'numpad6': '<kp_6>', 'numpad7': '<kp_7>', 'numpad8': '<kp_8>',
                'numpad9': '<kp_9>', 'numpaddecimal': '<kp_decimal>', 
                'numpadplus': '<kp_add>', 'numpadminus': '<kp_subtract>', 
                'numpadmultiply': '<kp_multiply>', 'numpaddivide': '<kp_divide>',
                'numpadenter': '<kp_enter>',
            }
            
            # Заменяем все известные комбинации
            result = key_sequence
            for find, replace in replacements.items():
                result = result.replace(find, replace)
            
            # Обработка функциональных клавиш
            if result.startswith('f') and len(result) > 1 and result[1:].isdigit():
                result = f'<{result}>'
            
            # Для отладки
            print(f"Конвертация: '{key_sequence}' -> '{result}'")
            
            return result if result else None
                
        except Exception as e:
            print(f"Ошибка конвертации клавиши {key_sequence}: {e}")
            return None
    
    def on_hotkey_triggered(self, action):
        """Обрабатывает срабатывание горячей клавиши"""
        print(f"Сработала горячая клавиша: {action}")
        self.hotkey_triggered.emit(action)