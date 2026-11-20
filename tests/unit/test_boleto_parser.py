from datetime import date
from decimal import Decimal

from boleto_extractor.application.services.boleto_parser import BoletoParser

HOJE = date(2026, 11, 20)


def _mod11(numero: str) -> int:
    soma, peso = 0, 2
    for d in reversed(numero):
        soma += int(d) * peso
        peso = 2 if peso == 9 else peso + 1
    r = 11 - soma % 11
    return 1 if r in (0, 10, 11) else r


def montar_cobranca(
    banco: str = "237", fator: str = "1000", valor: str = "0000015050", livre: str = "1" * 25
) -> str:
    sem_dv = banco + "9" + fator + valor + livre
    return sem_dv[:4] + str(_mod11(sem_dv)) + sem_dv[4:]


parser = BoletoParser(referencia=lambda: HOJE)


def test_cobranca_valor_banco_e_vencimento_novo_ciclo() -> None:
    d = parser.cobranca(montar_cobranca())
    assert d.valor == Decimal("150.50")
    assert d.banco_nome == "Bradesco"
    assert d.vencimento == date(2025, 2, 22)


def test_cobranca_fator_9999_usa_ciclo_antigo_quando_mais_proximo() -> None:
    d = parser.cobranca(montar_cobranca(fator="9999"))
    assert d.vencimento == date(2025, 2, 21)


def test_cobranca_fator_proximo_de_hoje() -> None:
    fator = str(1000 + (HOJE - date(2025, 2, 22)).days)
    assert parser.cobranca(montar_cobranca(fator=fator)).vencimento == HOJE


def test_cobranca_sem_vencimento_e_valor_zero() -> None:
    d = parser.cobranca(montar_cobranca(fator="0000", valor="0" * 10))
    assert d.vencimento is None
    assert d.valor is None
    assert len(d.observacoes) == 2


def test_arrecadacao_saneamento() -> None:
    d = parser.arrecadacao("82680000001820100478209729700310261000000000")
    assert d.segmento == "Saneamento"
    assert d.valor == Decimal("182.01")
    assert d.empresa_id == "0047"
    assert d.vencimento is None


def test_arrecadacao_vencimento_estimado() -> None:
    codigo = "8560" + "00000010000" + "1234" + "20261215" + "0" * 17
    d = parser.arrecadacao(codigo)
    assert d.vencimento == date(2026, 12, 15)
    assert d.vencimento_estimado
    assert d.valor == Decimal("100.00")
