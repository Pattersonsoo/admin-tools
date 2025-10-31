from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def set_dark_theme(app):
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(37, 37, 37))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    app.setPalette(palette)
