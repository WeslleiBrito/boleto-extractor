
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class DesktopApplication:

    def __init__(self) -> None:
        self._application = QGuiApplication([])
        self._engine = QQmlApplicationEngine()

    def executar(self) -> int:
        self._application.setApplicationName("Extrator de Boletos")

        qml_path = Path(__file__).parent / "qml" / "Main.qml"

        self._engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))

        if not self._engine.rootObjects():
            return 1

        return self._application.exec()
