from pathlib import Path

from boleto_extractor.application.ports.barcode_reader import BarcodeReader
from boleto_extractor.application.ports.document_loader import DocumentLoader
from boleto_extractor.application.services.arrecadacao.barcode_to_digitable_line import (
    BarcodeToDigitableLine as ArrecadacaoConverter,
)
from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine as CobrancaConverter,
)
from boleto_extractor.core.exceptions import BoletoExtractorError, BoletoValidationError
from boleto_extractor.domain.entities.boleto import Boleto
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.boleto_type import BoletoType
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus


class ExtractBoletoUseCase:
    """Orquestra: carregar documento -> ler códigos -> identificar tipo -> converter."""

    def __init__(
        self,
        loader: DocumentLoader,
        reader: BarcodeReader,
        cobranca: CobrancaConverter | None = None,
        arrecadacao: ArrecadacaoConverter | None = None,
    ) -> None:
        self._loader = loader
        self._reader = reader
        self._cobranca = cobranca or CobrancaConverter()
        self._arrecadacao = arrecadacao or ArrecadacaoConverter()

    def executar(self, arquivo: Path) -> ExtractionResult:
        mensagens: list[str] = []

        try:
            for numero_pagina, pagina in enumerate(self._loader.carregar(arquivo), start=1):
                for leitura in self._reader.ler(pagina):
                    codigo = "".join(c for c in leitura.valor if c.isdigit())

                    if len(codigo) != 44:
                        continue

                    try:
                        boleto = self._montar_boleto(codigo)
                    except BoletoValidationError as exc:
                        mensagens.append(f"Página {numero_pagina}: {exc}")
                        continue

                    return ExtractionResult(
                        arquivo=arquivo,
                        status=ExtractionStatus.SUCCESS,
                        boleto=boleto,
                        confianca=1.0,
                        mensagens=(f"Encontrado na página {numero_pagina}.",),
                    )

        except BoletoExtractorError as exc:
            return ExtractionResult(
                arquivo=arquivo,
                status=ExtractionStatus.ERROR,
                mensagens=(str(exc),),
            )

        if mensagens:
            return ExtractionResult(
                arquivo=arquivo,
                status=ExtractionStatus.INVALID,
                mensagens=tuple(mensagens),
            )

        return ExtractionResult(
            arquivo=arquivo,
            status=ExtractionStatus.REVIEW,
            mensagens=("Nenhum código de barras encontrado.",),
        )

    def _montar_boleto(self, codigo: str) -> Boleto:
        if codigo.startswith("8"):
            return Boleto(
                tipo=BoletoType.ARRECADACAO,
                codigo_barras=codigo,
                linha_digitavel=self._arrecadacao.converter(codigo),
            )

        return Boleto(
            tipo=BoletoType.BANK_SLIP,
            codigo_barras=codigo,
            linha_digitavel=self._cobranca.converter(codigo),
        )
