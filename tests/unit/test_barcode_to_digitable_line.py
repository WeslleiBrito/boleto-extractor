
import pytest

from boleto_extractor.application.services.arrecadacao.barcode_to_digitable_line import (
    BarcodeToDigitableLine,
)
from boleto_extractor.core.exceptions import BoletoValidationError


@pytest.fixture
def converter() -> BarcodeToDigitableLine:
    return BarcodeToDigitableLine()


def test_converter_codigo_arrecadacao_modulo_10(
    converter: BarcodeToDigitableLine,
) -> None:
    codigo = "82680000001820100478209729700310261000000000"

    resultado = converter.converter(codigo)

    esperado = (
        "826800000018"
        "820100478206"
        "972970031027"
        "610000000006"
    )

    assert resultado == esperado


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
