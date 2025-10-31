# hotkey_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QPushButton, QLabel, QMessageBox,
                            QHeaderView, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence

class HotkeyDialog(QDialog):
    hotkey_changed = pyqtSignal(str, str)
    
    def __init__(self, hotkey_manager, parent=None):
        super().__init__(parent)
        self.hotkey_manager = hotkey_manager
        self.setup_ui()
        self.load_hotkeys()
        
    def setup_ui(self):
        self.setWindowTitle("Настройка горячих клавиш")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Таблица горячих клавиш
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Действие", "Горячая клавиша", "Операция"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.btn_set = QPushButton("Назначить клавишу")
        self.btn_set.clicked.connect(self.set_hotkey)
        button_layout.addWidget(self.btn_set)
        
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.clicked.connect(self.clear_hotkey)
        button_layout.addWidget(self.btn_clear)
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.close)
        button_layout.addWidget(self.btn_close)
        
        layout.addLayout(button_layout)
        
        # Информация
        info_label = QLabel("Выберите действие и нажмите 'Назначить клавишу', затем нажмите нужную комбинацию клавиш")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info_label)
        
        # Для захвата клавиш
        self.setting_hotkey = False
        self.current_action = None
        
    def load_hotkeys(self):
        """Загружает горячие клавиши в таблицу"""
        actions = {
            "chat_commands": "Открыть чат команды",
            "hints": "Открыть подсказки", 
            "teleports": "Открыть список телепортов"
        }
        
        self.table.setRowCount(len(actions))
        
        for row, (action_id, description) in enumerate(actions.items()):
            # Действие
            action_item = QTableWidgetItem(description)
            action_item.setData(Qt.ItemDataRole.UserRole, action_id)
            self.table.setItem(row, 0, action_item)
            
            # Горячая клавиша
            hotkey = self.hotkey_manager.get_hotkey_display(action_id)
            hotkey_item = QTableWidgetItem(hotkey)
            self.table.setItem(row, 1, hotkey_item)
            
            # Кнопка назначения
            btn_widget = QPushButton("Назначить")
            btn_widget.clicked.connect(lambda checked, act=action_id: self.start_set_hotkey(act))
            self.table.setCellWidget(row, 2, btn_widget)
    
    def start_set_hotkey(self, action):
        """Начинает процесс назначения горячей клавиши"""
        self.setting_hotkey = True
        self.current_action = action
        self.grabKeyboard()
        
        # Обновляем интерфейс
        for row in range(self.table.rowCount()):
            btn = self.table.cellWidget(row, 2)
            if btn:
                action_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if action_id == action:
                    btn.setText("Нажмите клавишу...")
                    btn.setEnabled(False)
                else:
                    btn.setEnabled(False)
        
        self.btn_set.setEnabled(False)
        self.btn_clear.setEnabled(False)
        
        QMessageBox.information(self, "Назначение клавиши", 
                              "Нажмите нужную комбинацию клавиш...\n\n"
                              "Для отмены нажмите Escape")
    
    def keyPressEvent(self, event):
        if self.setting_hotkey:
            if event.key() == Qt.Key.Key_Escape:
                self.cancel_set_hotkey()
                return
                
            # Игнорируем одиночные нажатия модификаторов
            if event.key() in [
                Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, 
                Qt.Key.Key_Meta, Qt.Key.Key_AltGr
            ]:
                event.ignore()
                return
                
            # Используем nativeEvent для получения информации о Numpad
            key_name = self.get_key_name_with_numpad(event)
            
            if key_name:
                # Собираем комбинацию клавиш вручную
                modifiers = []
                
                # Обрабатываем модификаторы
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    modifiers.append("Ctrl")
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    modifiers.append("Alt")
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    modifiers.append("Shift")
                if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
                    modifiers.append("Meta")
                
                # Формируем комбинацию
                if modifiers:
                    key_sequence = "+".join(modifiers) + "+" + key_name
                else:
                    key_sequence = key_name
                
                # Сохраняем горячую клавишу
                self.finish_set_hotkey(key_sequence)
                event.accept()
            else:
                # Если клавиша не распознана, игнорируем
                event.ignore()
        else:
            super().keyPressEvent(event)

    def get_key_name_with_numpad(self, event):
        """Определяет название клавиши с учетом Numpad"""
        try:
            # Базовое определение клавиши
            key = event.key()
            key_name = self.get_key_name(key)
            
            # Проверяем, является ли это Numpad через scan code
            native_scan_code = event.nativeScanCode()
            
            # Scan codes для Numpad (Windows)
            numpad_scan_codes = {
                82: "Numpad0", 79: "Numpad1", 80: "Numpad2", 81: "Numpad3",
                75: "Numpad4", 76: "Numpad5", 77: "Numpad6", 71: "Numpad7",
                72: "Numpad8", 73: "Numpad9", 83: "NumpadDecimal",
                78: "NumpadPlus", 74: "NumpadMinus", 55: "NumpadMultiply",
                53: "NumpadDivide", 28: "NumpadEnter"
            }
            
            # Если scan code соответствует Numpad, используем специальное название
            if native_scan_code in numpad_scan_codes:
                return numpad_scan_codes[native_scan_code]
            
            # Дополнительная проверка через virtual key
            native_virtual_key = event.nativeVirtualKey()
            numpad_virtual_keys = {
                96: "Numpad0", 97: "Numpad1", 98: "Numpad2", 99: "Numpad3",
                100: "Numpad4", 101: "Numpad5", 102: "Numpad6", 103: "Numpad7",
                104: "Numpad8", 105: "Numpad9", 110: "NumpadDecimal",
                107: "NumpadPlus", 109: "NumpadMinus", 106: "NumpadMultiply",
                111: "NumpadDivide", 13: "NumpadEnter"
            }
            
            if native_virtual_key in numpad_virtual_keys:
                return numpad_virtual_keys[native_virtual_key]
            
            return key_name
            
        except Exception as e:
            print(f"Ошибка определения клавиши: {e}")
            return self.get_key_name(event.key())
        
    def cancel_set_hotkey(self):
        """Отменяет назначение горячей клавиши"""
        self.setting_hotkey = False
        self.releaseKeyboard()
        self.update_interface()
        
    def finish_set_hotkey(self, key_sequence):
        """Завершает назначение горячей клавиши"""
        if self.current_action and key_sequence:
            # Сохраняем в менеджере горячих клавиш
            self.hotkey_manager.set_hotkey(self.current_action, key_sequence)
            
            # Обновляем таблицу
            self.load_hotkeys()
            
            # Сигнализируем об изменении
            self.hotkey_changed.emit(self.current_action, key_sequence)
            
            QMessageBox.information(self, "Успешно", 
                                  f"Горячая клавиша назначена: {key_sequence}")
        
        self.setting_hotkey = False
        self.current_action = None
        self.releaseKeyboard()
        self.update_interface()
    
    def clear_hotkey(self):
        """Очищает выбранную горячую клавишу"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            action_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            if action_id:
                self.hotkey_manager.set_hotkey(action_id, "")
                self.load_hotkeys()
                self.hotkey_changed.emit(action_id, "")
                QMessageBox.information(self, "Успешно", "Горячая клавиша очищена")
    
    def update_interface(self):
        """Обновляет интерфейс после назначения клавиши"""
        for row in range(self.table.rowCount()):
            btn = self.table.cellWidget(row, 2)
            if btn:
                btn.setText("Назначить")
                btn.setEnabled(True)
        
        self.btn_set.setEnabled(True)
        self.btn_clear.setEnabled(True)
    
    def closeEvent(self, event):
        if self.setting_hotkey:
            self.cancel_set_hotkey()
        super().closeEvent(event)
    
    def set_hotkey(self):
        """Обработчик кнопки 'Назначить клавишу'"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            action_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)
            if action_id:
                self.start_set_hotkey(action_id)
    
    def get_key_name(self, key):
        """Преобразует код клавиши в читаемое название"""
        key_mapping = {
            # Функциональные клавиши
            Qt.Key.Key_F1: "F1", Qt.Key.Key_F2: "F2", Qt.Key.Key_F3: "F3",
            Qt.Key.Key_F4: "F4", Qt.Key.Key_F5: "F5", Qt.Key.Key_F6: "F6",
            Qt.Key.Key_F7: "F7", Qt.Key.Key_F8: "F8", Qt.Key.Key_F9: "F9",
            Qt.Key.Key_F10: "F10", Qt.Key.Key_F11: "F11", Qt.Key.Key_F12: "F12",
            
            # Навигационные клавиши
            Qt.Key.Key_Space: "Space", Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Backspace: "Backspace", Qt.Key.Key_Return: "Return",
            Qt.Key.Key_Enter: "Enter", Qt.Key.Key_Delete: "Delete",
            Qt.Key.Key_Insert: "Insert", Qt.Key.Key_Home: "Home",
            Qt.Key.Key_End: "End", Qt.Key.Key_PageUp: "PageUp",
            Qt.Key.Key_PageDown: "PageDown", Qt.Key.Key_Escape: "Esc",
            Qt.Key.Key_Up: "Up", Qt.Key.Key_Down: "Down",
            Qt.Key.Key_Left: "Left", Qt.Key.Key_Right: "Right",
            
            # Буквы
            Qt.Key.Key_A: "A", Qt.Key.Key_B: "B", Qt.Key.Key_C: "C",
            Qt.Key.Key_D: "D", Qt.Key.Key_E: "E", Qt.Key.Key_F: "F",
            Qt.Key.Key_G: "G", Qt.Key.Key_H: "H", Qt.Key.Key_I: "I",
            Qt.Key.Key_J: "J", Qt.Key.Key_K: "K", Qt.Key.Key_L: "L",
            Qt.Key.Key_M: "M", Qt.Key.Key_N: "N", Qt.Key.Key_O: "O",
            Qt.Key.Key_P: "P", Qt.Key.Key_Q: "Q", Qt.Key.Key_R: "R",
            Qt.Key.Key_S: "S", Qt.Key.Key_T: "T", Qt.Key.Key_U: "U",
            Qt.Key.Key_V: "V", Qt.Key.Key_W: "W", Qt.Key.Key_X: "X",
            Qt.Key.Key_Y: "Y", Qt.Key.Key_Z: "Z",
            
            # Цифры (обычные)
            Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2",
            Qt.Key.Key_3: "3", Qt.Key.Key_4: "4", Qt.Key.Key_5: "5",
            Qt.Key.Key_6: "6", Qt.Key.Key_7: "7", Qt.Key.Key_8: "8",
            Qt.Key.Key_9: "9",
            
            # Символы
            Qt.Key.Key_Minus: "-", Qt.Key.Key_Equal: "=",
            Qt.Key.Key_BracketLeft: "[", Qt.Key.Key_BracketRight: "]",
            Qt.Key.Key_Semicolon: ";", Qt.Key.Key_Apostrophe: "'",
            Qt.Key.Key_Backslash: "\\", Qt.Key.Key_Comma: ",",
            Qt.Key.Key_Period: ".", Qt.Key.Key_Slash: "/",
            Qt.Key.Key_Agrave: "`",
            
            # Дополнительные клавиши
            Qt.Key.Key_CapsLock: "CapsLock", Qt.Key.Key_NumLock: "NumLock",
            Qt.Key.Key_ScrollLock: "ScrollLock", Qt.Key.Key_Pause: "Pause",
            Qt.Key.Key_Print: "Print", Qt.Key.Key_Menu: "Menu",
        }
        
        return key_mapping.get(key, "")