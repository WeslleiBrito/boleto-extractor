from collections.abc import Iterator
from datetime import date
from pathlib import Path

import numpy as np

from boleto_extractor.application.ports.barcode_reader import BarcodeReading
from boleto_extractor.application.services.boleto_parser import BoletoParser
from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.exceptions import DocumentLoadError
from boleto_extractor.core.types import ImageArray
from boleto_extractor.domain.enums.boleto_type import BoletoType
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from tests.unit.test_boleto_parser import montar_cobranca

ARQUIVO = Path("boleto.pdf")
ARRECADACAO = "82680000001820100478209729700310261000000000"
COBRANCA = montar_cobranca()


class FakeLoader:
    def __init__(self, paginas: int = 1, erro: bool = False) -> None:
        self._paginas = paginas
        self._erro = erro

    def carregar(self, arquivo: Path) -> Iterator[ImageArray]:
        if self._erro:
            raise DocumentLoadError("Falha simulada.")
        for _ in range(self._paginas):
            yield np.zeros((10, 10, 3), dtype=np.uint8)


class FakeReader:
    """Cada chamada a ler() devolve os códigos da próxima página."""

    def __init__(self, *paginas: tuple[str, ...]) -> None:
        self._paginas = list(paginas)

    def ler(self, imagem: ImageArray) -> tuple[BarcodeReading, ...]:
        valores = self._paginas.pop(0) if self._paginas else ()
        return tuple(BarcodeReading(valor=v, formato="ITF") for v in valores)


def _caso(loader: FakeLoader, reader: FakeReader) -> ExtractBoletoUseCase:
    return ExtractBoletoUseCase(loader, reader, parser=BoletoParser(lambda: date(2026, 11, 20)))


def test_deve_extrair_boleto_de_arrecadacao_com_detalhes() -> None:
    (r,) = _caso(FakeLoader(), FakeReader((ARRECADACAO,))).executar(ARQUIVO)

    assert r.status == ExtractionStatus.SUCCESS
    assert r.boleto is not None and r.boleto.detalhes is not None
    assert r.boleto.tipo == BoletoType.ARRECADACAO
    assert r.boleto.linha_digitavel == "826800000018820100478206972970031027610000000006"
    assert r.pagina == 1


def test_deve_extrair_todos_os_boletos_do_pdf() -> None:
    resultados = _caso(
        FakeLoader(paginas=3), FakeReader((ARRECADACAO,), (), (COBRANCA,))
    ).executar(ARQUIVO)

    assert [r.status for r in resultados] == [ExtractionStatus.SUCCESS] * 2
    assert [r.pagina for r in resultados] == [1, 3]
    assert resultados[1].boleto is not None
    assert resultados[1].boleto.tipo == BoletoType.BANK_SLIP


def test_nao_deve_duplicar_mesmo_codigo() -> None:
    resultados = _caso(
        FakeLoader(paginas=2), FakeReader((ARRECADACAO, ARRECADACAO), (ARRECADACAO,))
    ).executar(ARQUIVO)

    assert len(resultados) == 1


def test_deve_marcar_revisao_quando_nao_encontrar_codigo() -> None:
    (r,) = _caso(FakeLoader(), FakeReader(())).executar(ARQUIVO)
    assert r.status == ExtractionStatus.REVIEW


def test_invalido_nao_impede_os_demais() -> None:
    ruim = "82600000001820100478209729700310261000000000"
    resultados = _caso(FakeLoader(), FakeReader((ruim, ARRECADACAO))).executar(ARQUIVO)

    assert [r.status for r in resultados] == [ExtractionStatus.INVALID, ExtractionStatus.SUCCESS]


def test_deve_retornar_erro_quando_documento_falhar() -> None:
    (r,) = _caso(FakeLoader(erro=True), FakeReader(())).executar(ARQUIVO)
    assert r.status == ExtractionStatus.ERROR


def test_deve_ignorar_leituras_que_nao_tem_44_digitos() -> None:
    (r,) = _caso(FakeLoader(), FakeReader(("123", ARRECADACAO))).executar(ARQUIVO)
    assert r.status == ExtractionStatus.SUCCESS
