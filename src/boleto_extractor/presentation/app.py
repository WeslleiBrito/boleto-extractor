import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.config import settings
from boleto_extractor.infrastructure.barcode.zxing_barcode_reader import ZXingBarcodeReader
from boleto_extractor.infrastructure.pdf.local_document_loader import LocalDocumentLoader
from boleto_extractor.presentation.themes.theme_manager import ThemeManager
from boleto_extractor.presentation.viewmodels.main_viewmodel import MainViewModel


class DesktopApplication:
    def __init__(self) -> None:
        QCoreApplication.setOrganizationName("BoletoExtractor")
        QCoreApplication.setApplicationName(settings.app_name)
        QQuickStyle.setStyle("Basic")  # permite personalização total dos controles

        self._application = QGuiApplication(sys.argv)
        self._engine = QQmlApplicationEngine()

        use_case = ExtractBoletoUseCase(LocalDocumentLoader(), ZXingBarcodeReader())
        self._theme = ThemeManager(self._application)
        self._viewmodel = MainViewModel(use_case)

        contexto = self._engine.rootContext()
        contexto.setContextProperty("Theme", self._theme)
        contexto.setContextProperty("viewModel", self._viewmodel)
        contexto.setContextProperty("appVersion", settings.version)

    def executar(self) -> int:
        qml_path = Path(__file__).parent / "qml" / "Main.qml"
        self._engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))

        if not self._engine.rootObjects():
            return 1

        return self._application.exec()
