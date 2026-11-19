
import pytest

from boleto_extractor.domain.entities.boleto import Boleto
from boleto_extractor.domain.enums.boleto_type import BoletoType


def test_deve_criar_boleto_com_linha_digitavel() -> None:
    boleto = Boleto(
        tipo=BoletoType.BANK_SLIP,
        linha_digitavel="12345678901234567890123456789012345678901234567",
    )

    assert boleto.tipo == BoletoType.BANK_SLIP
    assert boleto.linha_digitavel is not None


def test_nao_deve_criar_boleto_sem_codigo() -> None:
    with pytest.raises(ValueError):
        Boleto(tipo=BoletoType.BANK_SLIP)


def test_nao_deve_aceitar_letras_na_linha_digitavel() -> None:
    with pytest.raises(ValueError):
        Boleto(
            tipo=BoletoType.BANK_SLIP,
            linha_digitavel="123ABC",
        )
