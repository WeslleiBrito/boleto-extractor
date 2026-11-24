import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.config import settings as app_config
from boleto_extractor.infrastructure.barcode.zxing_barcode_reader import ZXingBarcodeReader
from boleto_extractor.infrastructure.cnpj.bigquery_cnpj_client import BigQueryCnpjClient
from boleto_extractor.infrastructure.cnpj.fallback_cnpj_lookup import FallbackCnpjLookup
from boleto_extractor.infrastructure.cnpj.opencnpj_client import OpenCnpjClient
from boleto_extractor.infrastructure.erp.erp_escrita_repository import ErpEscritaRepository
from boleto_extractor.infrastructure.erp.erp_parcela_repository import ErpParcelaRepository
from boleto_extractor.infrastructure.pdf.local_document_loader import LocalDocumentLoader
from boleto_extractor.infrastructure.pdf.pymupdf_text_extractor import PyMuPdfTextExtractor
from boleto_extractor.presentation.themes.theme_manager import ThemeManager
from boleto_extractor.presentation.viewmodels.main_viewmodel import MainViewModel
from boleto_extractor.presentation.viewmodels.settings_viewmodel import SettingsViewModel


class DesktopApplication:
    def __init__(self) -> None:
        QCoreApplication.setOrganizationName("BoletoExtractor")
        QCoreApplication.setApplicationName(app_config.app_name)
        QQuickStyle.setStyle("Basic")  # permite personalização total dos controles

        self._application = QGuiApplication(sys.argv)
        self._engine = QQmlApplicationEngine()

        # Settings primeiro: os serviços leem a configuração a cada consulta
        self._settings = SettingsViewModel(self._application)

        cnpj_lookup = FallbackCnpjLookup(
            OpenCnpjClient(),
            BigQueryCnpjClient(self._settings.valores),
        )

        use_case = ExtractBoletoUseCase(
            LocalDocumentLoader(),
            ZXingBarcodeReader(),
            text_extractor=PyMuPdfTextExtractor(),
            cnpj_lookup=cnpj_lookup,
        )

        # Repositório ERP: config e senha (tela ou cofre do Windows) lidas a cada conexão
        repositorio = ErpParcelaRepository(
            self._settings.valores,
            self._settings.senha_mysql,
        )

        # Escrita: grava SOMENTE pagar_parcelas.pagparc_obs, usando a mesma conexão configurada
        escrita = ErpEscritaRepository(repositorio.conectar)

        self._theme = ThemeManager(self._application)
        self._viewmodel = MainViewModel(
            use_case,
            repositorio=repositorio,
            erp_ativo=lambda: bool(self._settings.dbAtivo),
            escrita=escrita,
        )

        # Qualquer mudança nas configurações atualiza o estado do ERP na tela
        self._settings.alterado.connect(self._viewmodel.atualizarErp)

        contexto = self._engine.rootContext()
        contexto.setContextProperty("Theme", self._theme)
        contexto.setContextProperty("viewModel", self._viewmodel)
        contexto.setContextProperty("settings", self._settings)
        contexto.setContextProperty("appVersion", app_config.version)

    def executar(self) -> int:
        qml_path = Path(__file__).parent / "qml" / "Main.qml"
        self._engine.load(QUrl.fromLocalFile(str(qml_path.resolve())))

        if not self._engine.rootObjects():
            return 1

        codigo = self._application.exec()

        # Destrói o QML antes dos view models (evita avisos "null" ao fechar)
        del self._engine
        return codigo
