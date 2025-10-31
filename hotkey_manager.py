
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
            
            # Сопоставление для pynput
            replacements = {
                'ctrl+': '<ctrl>+',
                'alt+': '<alt>+', 
                'shift+': '<shift>+',
                'win+': '<cmd>+',  # Windows key
                'meta+': '<cmd>+', # Meta key
                
                # Специальные клавиши
                'space': ' ',
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
                'print_screen': '<print_screen>',
                'pause': '<pause>',
                
                # Обычные цифры и буквы остаются как есть
                '0': '0', '1': '1', '2': '2', '3': '3', '4': '4',
                '5': '5', '6': '6', '7': '7', '8': '8', '9': '9',
                
                # Numpad клавиши в правильном формате для pynput
                'numpad0': '<num_lock>',  # pynput использует <num_lock> для Numpad
                'numpad1': '<end>',       # Numpad 1 = End
                'numpad2': '<down>',      # Numpad 2 = Down Arrow
                'numpad3': '<page_down>', # Numpad 3 = Page Down
                'numpad4': '<left>',      # Numpad 4 = Left Arrow
                'numpad5': '<clear>',     # Numpad 5 = Clear (нет в pynput, используем num_lock)
                'numpad6': '<right>',     # Numpad 6 = Right Arrow
                'numpad7': '<home>',      # Numpad 7 = Home
                'numpad8': '<up>',        # Numpad 8 = Up Arrow
                'numpad9': '<page_up>',   # Numpad 9 = Page Up
                'numpaddecimal': '<delete>',
                'numpadplus': '+',
                'numpadminus': '-',
                'numpadmultiply': '*',
                'numpaddivide': '/',
                'numpadenter': '<enter>',
            }
            
            # Разбираем комбинацию клавиш
            parts = key_sequence.split('+')
            converted_parts = []
            
            for part in parts:
                if part in replacements:
                    converted_parts.append(replacements[part])
                else:
                    # Для букв, функциональных клавиш и других оставляем как есть
                    converted_parts.append(part)
            
            result = '+'.join(converted_parts)
            
            # Обработка функциональных клавиш (F1-F12)
            if len(parts) == 1 and parts[0].startswith('f') and parts[0][1:].isdigit():
                result = f'<{parts[0]}>'
            
            # Убираем двойные модификаторы если есть
            result = result.replace('<ctrl>+<ctrl>', '<ctrl>')
            result = result.replace('<alt>+<alt>', '<alt>')
            result = result.replace('<shift>+<shift>', '<shift>')
            
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