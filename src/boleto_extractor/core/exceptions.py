
class BoletoExtractorError(Exception):
    """Exceção base da aplicação."""


class DocumentLoadError(BoletoExtractorError):
    """Falha ao carregar um documento."""


class OCRProcessingError(BoletoExtractorError):
    """Falha durante o reconhecimento óptico."""


class BarcodeReadingError(BoletoExtractorError):
    """Falha durante a leitura do código de barras."""


class BoletoValidationError(BoletoExtractorError):
    """Falha durante a validação do boleto."""
