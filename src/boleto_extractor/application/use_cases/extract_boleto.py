from pathlib import Path

from boleto_extractor.application.ports.barcode_reader import BarcodeReader
from boleto_extractor.application.ports.document_loader import DocumentLoader
from boleto_extractor.application.services.arrecadacao.barcode_to_digitable_line import (
    BarcodeToDigitableLine as ArrecadacaoConverter,
)
from boleto_extractor.application.services.boleto_parser import BoletoParser
from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine as CobrancaConverter,
)
from boleto_extractor.application.services.code_normalizer import CodeNormalizer
from boleto_extractor.core.exceptions import BoletoExtractorError, BoletoValidationError
from boleto_extractor.domain.entities.boleto import Boleto
from boleto_extractor.domain.entities.extraction_result import ExtractionResult
from boleto_extractor.domain.enums.boleto_type import BoletoType
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus

ORIGEM_MANUAL = Path("Leitor de código")


class ExtractBoletoUseCase:
    """Extrai boletos de documentos ou de códigos digitados/bipados."""

    def __init__(
        self,
        loader: DocumentLoader,
        reader: BarcodeReader,
        cobranca: CobrancaConverter | None = None,
        arrecadacao: ArrecadacaoConverter | None = None,
        parser: BoletoParser | None = None,
    ) -> None:
        self._loader = loader
        self._reader = reader
        self._cobranca = cobranca or CobrancaConverter()
        self._arrecadacao = arrecadacao or ArrecadacaoConverter()
        self._parser = parser or BoletoParser()
        self._normalizer = CodeNormalizer(self._cobranca, self._arrecadacao)

    def executar(self, arquivo: Path) -> tuple[ExtractionResult, ...]:
        resultados: list[ExtractionResult] = []
        vistos: set[str] = set()

        try:
            for pagina, imagem in enumerate(self._loader.carregar(arquivo), start=1):
                for leitura in self._reader.ler(imagem):
                    codigo = "".join(c for c in leitura.valor if c.isdigit())

                    if len(codigo) != 44 or codigo in vistos:
                        continue
                    vistos.add(codigo)

                    resultados.append(self._processar(arquivo, pagina, codigo))

        except BoletoExtractorError as exc:
            resultados.append(
                ExtractionResult(
                    arquivo=arquivo,
                    status=ExtractionStatus.ERROR,
                    mensagens=(str(exc),),
                )
            )

        if not resultados:
            resultados.append(
                ExtractionResult(
                    arquivo=arquivo,
                    status=ExtractionStatus.REVIEW,
                    mensagens=("Nenhum código de barras encontrado.",),
                )
            )

        return tuple(resultados)

    def executar_codigo(self, texto: str, origem: Path = ORIGEM_MANUAL) -> ExtractionResult:
        """Processa um código vindo do leitor USB ou digitado (44, 47 ou 48 dígitos)."""
        try:
            codigo = self._normalizer.para_codigo_barras(texto)
        except BoletoValidationError as exc:
            return ExtractionResult(
                arquivo=origem,
                status=ExtractionStatus.INVALID,
                mensagens=(str(exc),),
            )

        return self._processar(origem, None, codigo)

    def _processar(self, arquivo: Path, pagina: int | None, codigo: str) -> ExtractionResult:
        try:
            boleto = self._montar_boleto(codigo)
        except BoletoValidationError as exc:
            return ExtractionResult(
                arquivo=arquivo,
                status=ExtractionStatus.INVALID,
                mensagens=(str(exc),),
                pagina=pagina,
            )

        return ExtractionResult(
            arquivo=arquivo,
            status=ExtractionStatus.SUCCESS,
            boleto=boleto,
            confianca=1.0,
            mensagens=boleto.detalhes.observacoes if boleto.detalhes else (),
            pagina=pagina,
        )

    def _montar_boleto(self, codigo: str) -> Boleto:
        if codigo.startswith("8"):
            return Boleto(
                tipo=BoletoType.ARRECADACAO,
                codigo_barras=codigo,
                linha_digitavel=self._arrecadacao.converter(codigo),
                detalhes=self._parser.arrecadacao(codigo),
            )

        return Boleto(
            tipo=BoletoType.BANK_SLIP,
            codigo_barras=codigo,
            linha_digitavel=self._cobranca.converter(codigo),
            detalhes=self._parser.cobranca(codigo),
        )
