import re
from dataclasses import fields, is_dataclass
from typing import Any

import pytest

from boleto_extractor.presentation.formatting import formatar_linha
from boleto_extractor.presentation.themes.catalog import (
    CLARO,
    ESCURO,
    SYSTEM_ID,
    THEMES,
    resolve_theme,
)

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _cores(obj: Any) -> list[str]:
    valores: list[str] = []
    for campo in fields(obj):
        valor = getattr(obj, campo.name)
        if is_dataclass(valor):
            valores.extend(_cores(valor))
        elif isinstance(valor, str) and valor.startswith("#"):
            valores.append(valor)
    return valores


@pytest.mark.parametrize("tema", THEMES.values(), ids=lambda t: t.id)
def test_todas_as_cores_devem_ser_hex_validas(tema: Any) -> None:
    assert all(HEX.match(cor) for cor in _cores(tema))


def test_ids_nao_podem_conflitar_com_sistema() -> None:
    assert SYSTEM_ID not in THEMES


def test_sistema_escuro_resolve_para_tema_escuro() -> None:
    assert resolve_theme(SYSTEM_ID, sistema_escuro=True) is ESCURO
    assert resolve_theme(SYSTEM_ID, sistema_escuro=False) is CLARO


def test_tema_inexistente_cai_no_sistema() -> None:
    assert resolve_theme("nao_existe", sistema_escuro=False) is CLARO


def test_tema_deve_ser_serializavel_para_qml() -> None:
    dados = THEMES["laranja_preto"].to_qml()
    assert dados["button"]["background"] == "#FF7A00"
    assert dados["table"]["headerFont"]["weight"] == 700


def test_formatar_linha_cobranca() -> None:
    linha = "23790123456000000000123456789012199990000010000"
    assert formatar_linha(linha) == (
        "23790.12345 60000.000001 23456.789012 1 99990000010000"
    )


def test_formatar_linha_arrecadacao() -> None:
    linha = "826800000018820100478206972970031027610000000006"
    assert formatar_linha(linha) == (
        "82680000001-8 82010047820-6 97297003102-7 61000000000-6"
    )
