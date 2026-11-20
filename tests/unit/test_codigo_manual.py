from datetime import date

import pytest

from boleto_extractor.application.services.boleto_parser import BoletoParser
from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine as CobrancaConverter,
)
from boleto_extractor.application.services.code_normalizer import CodeNormalizer
from boleto_extractor.application.use_cases.extract_boleto import ExtractBoletoUseCase
from boleto_extractor.core.exceptions import BoletoValidationError
from boleto_extractor.domain.enums.extraction_status import ExtractionStatus
from boleto_extractor.presentation.formatting import formatar_linha
from tests.unit.test_extract_boleto_use_case import FakeLoader, FakeReader
from tests.unit.test_boleto_parser import montar_cobranca

ARRECADACAO = "82680000001820100478209729700310261000000000"
ARRECADACAO_LINHA = "826800000018820100478206972970031027610000000006"
COBRANCA = montar_cobranca()
COBRANCA_LINHA = CobrancaConverter().converter(COBRANCA)

normalizer = CodeNormalizer()


def test_codigo_de_barras_passa_direto() -> None:
    assert normalizer.para_codigo_barras(ARRECADACAO) == ARRECADACAO


def test_linha_arrecadacao_formatada_vira_codigo() -> None:
    assert normalizer.para_codigo_barras(formatar_linha(ARRECADACAO_LINHA)) == ARRECADACAO


def test_linha_cobranca_vira_codigo() -> None:
    assert normalizer.para_codigo_barras(formatar_linha(COBRANCA_LINHA)) == COBRANCA


def test_dv_de_campo_errado_e_recusado() -> None:
    errada = COBRANCA_LINHA[:9] + str((int(COBRANCA_LINHA[9]) + 1) % 10) + COBRANCA_LINHA[10:]
    with pytest.raises(BoletoValidationError):
        normalizer.para_codigo_barras(errada)


@pytest.mark.parametrize("texto", ["", "123", "9" * 50])
def test_tamanho_invalido(texto: str) -> None:
    with pytest.raises(BoletoValidationError):
        normalizer.para_codigo_barras(texto)


def _caso() -> ExtractBoletoUseCase:
    return ExtractBoletoUseCase(
        FakeLoader(), FakeReader(), parser=BoletoParser(lambda: date(2026, 11, 20))
    )


def test_use_case_aceita_linha_digitavel() -> None:
    r = _caso().executar_codigo(ARRECADACAO_LINHA)
    assert r.status == ExtractionStatus.SUCCESS
    assert r.boleto is not None and r.boleto.codigo_barras == ARRECADACAO
    assert r.pagina is None


def test_use_case_marca_invalido_sem_lancar_excecao() -> None:
    assert _caso().executar_codigo("12345").status == ExtractionStatus.INVALID
