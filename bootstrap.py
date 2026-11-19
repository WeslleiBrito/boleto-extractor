
from boleto_extractor.presentation.app import DesktopApplication


def run() -> int:
    application = DesktopApplication()
    return application.executar()
