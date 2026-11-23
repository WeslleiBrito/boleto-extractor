from dataclasses import replace
from pathlib import Path

from boleto_extractor.application.ports.barcode_reader import BarcodeReader
from boleto_extractor.application.ports.cnpj_lookup import CnpjLookup
from boleto_extractor.application.ports.document_loader import DocumentLoader
from boleto_extractor.application.ports.text_extractor import TextExtractor
from boleto_extractor.application.services.arrecadacao.barcode_to_digitable_line import (
    BarcodeToDigitableLine as ArrecadacaoConverter,
)
from boleto_extractor.application.services.beneficiario_extractor import BeneficiarioExtractor
from boleto_extractor.application.services.boleto_parser import BoletoParser
from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine as CobrancaConverter,
)
from boleto_extractor.application.services.code_normalizer import CodeNormalizer
from boleto_extractor.core.exceptions import BoletoExtractorError, BoletoValidationError
from boleto_extractor.domain.entities.beneficiario import Beneficiario
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
        text_extractor: TextExtractor | None = None,
        cnpj_lookup: CnpjLookup | None = None,
        beneficiario_extractor: BeneficiarioExtractor | None = None,
    ) -> None:
        self._loader = loader
        self._reader = reader
        self._cobranca = cobranca or CobrancaConverter()
        self._arrecadacao = arrecadacao or ArrecadacaoConverter()
        self._parser = parser or BoletoParser()
        self._normalizer = CodeNormalizer(self._cobranca, self._arrecadacao)
        self._text_extractor = text_extractor
        self._cnpj_lookup = cnpj_lookup
        self._benef_extractor = beneficiario_extractor or BeneficiarioExtractor()

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

        return tuple(self._enriquecer(arquivo, resultados))

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

    # ---------------- Beneficiário ----------------
    def _enriquecer(
        self, arquivo: Path, resultados: list[ExtractionResult]
    ) -> list[ExtractionResult]:
        """Anexa o beneficiário. Qualquer falha mantém o resultado original."""
        if self._text_extractor is None:
            return resultados
        if not any(r.status == ExtractionStatus.SUCCESS for r in resultados):
            return resultados

        try:
            paginas = self._text_extractor.extrair_paginas(arquivo)
        except Exception:
            return resultados
        if not any(paginas):
            return resultados

        texto_total = "\n".join(paginas)
        saida: list[ExtractionResult] = []
        for r in resultados:
            texto = texto_total
            if r.pagina and 0 < r.pagina <= len(paginas) and paginas[r.pagina - 1]:
                texto = paginas[r.pagina - 1]
            saida.append(self._com_beneficiario(r, texto))
        return saida

    def _com_beneficiario(self, resultado: ExtractionResult, texto: str) -> ExtractionResult:
        if resultado.status != ExtractionStatus.SUCCESS or resultado.boleto is None:
            return resultado
        try:
            achado = self._benef_extractor.extrair(texto, self._raiz_cnpj(resultado.boleto))
            if achado is None:
                return resultado

            empresa = None
            if achado.tipo == "CNPJ" and self._cnpj_lookup is not None:
                empresa = self._cnpj_lookup.consultar(achado.documento)

            return replace(
                resultado,
                beneficiario=Beneficiario(
                    documento=achado.documento,
                    tipo=achado.tipo,
                    empresa=empresa,
                    confirmado_pelo_codigo=achado.confirmado_pelo_codigo,
                ),
            )
        except Exception:
            return resultado

    @staticmethod
    def _raiz_cnpj(boleto: Boleto) -> str | None:
        """Arrecadação segmento 6: posições 16-23 trazem a raiz do CNPJ."""
        if boleto.tipo != BoletoType.ARRECADACAO or not boleto.codigo_barras:
            return None
        if boleto.codigo_barras[1] != "6":
            return None
        return boleto.codigo_barras[15:23]

    # ---------------- Boleto ----------------
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
