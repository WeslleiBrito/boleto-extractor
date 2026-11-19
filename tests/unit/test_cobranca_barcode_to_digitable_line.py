
import pytest

from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine,
)
from boleto_extractor.core.exceptions import BoletoValidationError


@pytest.fixture
def conversor() -> BarcodeToDigitableLine:
    return BarcodeToDigitableLine()


def test_converter_boleto_bancario(
    conversor: BarcodeToDigitableLine,
) -> None:
    codigo = "34194846500000055001090154206270937160950000"

    resultado = conversor.converter(codigo)

    esperado = (
        "3419109016"
        "54206270933"
        "71609500005"
        "4"
        "84650000005500"
    )

    assert resultado == esperado
    assert len(resultado) == 47


def test_rejeitar_codigo_com_dv_geral_invalido(
    conversor: BarcodeToDigitableLine,
) -> None:
    codigo = "34193846500000055001090154206270937160950000"

    with pytest.raises(BoletoValidationError):
        conversor.converter(codigo)


def test_rejeitar_codigo_com_tamanho_invalido(
    conversor: BarcodeToDigitableLine,
) -> None:
    with pytest.raises(BoletoValidationError):
        conversor.converter("341948465")


def test_rejeitar_codigo_nao_numerico(
    conversor: BarcodeToDigitableLine,
) -> None:
    codigo = "3419484650000005500109015420627093716095000X"

    with pytest.raises(BoletoValidationError):
        conversor.converter(codigo)
