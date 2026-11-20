import pytest

from boleto_extractor.application.services.arrecadacao.barcode_to_digitable_line import (
    BarcodeToDigitableLine,
)
from boleto_extractor.core.exceptions import BoletoValidationError


CODIGO_ARRECADACAO = "82680000001820100478209729700310261000000000"

LINHA_ARRECADACAO = (
    "826800000018"
    "820100478206"
    "972970031027"
    "610000000006"
)


@pytest.fixture
def converter() -> BarcodeToDigitableLine:
    return BarcodeToDigitableLine()


def _remover_dvs_dos_blocos(linha: str) -> str:
    """Remove o DV de cada um dos 4 blocos de 12 dígitos."""
    return "".join(linha[i:i + 11] for i in range(0, 48, 12))


def test_converter_codigo_arrecadacao_modulo_10(
    converter: BarcodeToDigitableLine,
) -> None:
    resultado = converter.converter(CODIGO_ARRECADACAO)

    assert resultado == LINHA_ARRECADACAO


def test_linha_digitavel_deve_ter_48_digitos(
    converter: BarcodeToDigitableLine,
) -> None:
    resultado = converter.converter(CODIGO_ARRECADACAO)

    assert len(resultado) == 48
    assert resultado.isdigit()


def test_round_trip_arrecadacao(
    converter: BarcodeToDigitableLine,
) -> None:
    linha = converter.converter(CODIGO_ARRECADACAO)

    codigo_reconstruido = _remover_dvs_dos_blocos(linha)

    assert codigo_reconstruido == CODIGO_ARRECADACAO


def test_rejeitar_codigo_com_tamanho_invalido(
    converter: BarcodeToDigitableLine,
) -> None:
    with pytest.raises(BoletoValidationError):
        converter.converter("82680000001")


def test_rejeitar_codigo_com_dv_geral_invalido(
    converter: BarcodeToDigitableLine,
) -> None:
    codigo = "82600000001820100478209729700310261000000000"

    with pytest.raises(BoletoValidationError):
        converter.converter(codigo)


def test_rejeitar_codigo_nao_numerico(
    converter: BarcodeToDigitableLine,
) -> None:
    codigo = "8268000000182010047820972970031026100000000X"

    with pytest.raises(BoletoValidationError):
        converter.converter(codigo)
