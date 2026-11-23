from boleto_extractor.application.services.beneficiario_extractor import BeneficiarioExtractor
from boleto_extractor.application.services.documento_validator import cnpj_valido, cpf_valido


def test_validadores() -> None:
    assert cnpj_valido("11.222.333/0001-81")
    assert not cnpj_valido("11.222.333/0001-80")
    assert cnpj_valido("12ABC34501DE35")  # alfanumérico
    assert cpf_valido("529.982.247-25")


def test_separa_beneficiario_do_pagador() -> None:
    texto = "Pagador: Fulano CPF 529.982.247-25\nBeneficiário: ACME LTDA 11.222.333/0001-81"
    achado = BeneficiarioExtractor().extrair(texto)
    assert achado is not None and achado.documento == "11222333000181"


def test_raiz_do_codigo_tem_prioridade() -> None:
    texto = "Beneficiário 11.444.777/0001-61  Outro 11.222.333/0001-81"
    achado = BeneficiarioExtractor().extrair(texto, raiz_cnpj="11222333")
    assert achado is not None and achado.confirmado_pelo_codigo
