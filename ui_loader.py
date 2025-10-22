from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QWidget

def carregar_ui(caminho_ui: str) -> QWidget:
    loader = QUiLoader()
    file = QFile(caminho_ui)
    file.open(QFile.ReadOnly)
    widget = loader.load(file)
    file.close()
    return widget
