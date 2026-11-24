from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from enum import Enum

from boleto_extractor.infrastructure.erp.erp_parcela_repository import ParcelaErp

_TOL = Decimal("0.01")


class StatusSincronizacao(str, Enum):
    ENCONTRADO = "encontrado"
    JA_PAGO = "ja_pago"
    DATA_DIVERGENTE = "data_divergente"
    VALOR_DIVERGENTE = "valor_divergente"
    DOC_INEXISTENTE = "doc_inexistente"
    NAO_ENCONTRADO = "nao_encontrado"
    DUPLICADO = "duplicado"


ROTULOS = {
    StatusSincronizacao.ENCONTRADO: "Encontrado",
    StatusSincronizacao.JA_PAGO: "Já pago",
    StatusSincronizacao.DATA_DIVERGENTE: "Data divergente",
    StatusSincronizacao.VALOR_DIVERGENTE: "Valor divergente",
    StatusSincronizacao.DOC_INEXISTENTE: "Documento inexistente",
    StatusSincronizacao.NAO_ENCONTRADO: "Não encontrado",
    StatusSincronizacao.DUPLICADO: "Duplicado",
}

# Conferência do CNPJ do boleto x fornecedor do ERP
CNPJ_CONFERE = "confere"
CNPJ_RAIZ = "raiz"
CNPJ_DIVERGE = "diverge"
CNPJ_SEM_FORNECEDOR = "sem_fornecedor"
CNPJ_SEM_BOLETO = "sem_cnpj_boleto"
CNPJ_ORIGEM_ERP = "origem_erp"

ROTULOS_CNPJ = {
    CNPJ_CONFERE: "✔ CNPJ confere",
    CNPJ_RAIZ: "≈ Mesma raiz (filial/matriz)",
    CNPJ_DIVERGE: "⚠ CNPJ diverge do boleto",
    CNPJ_SEM_FORNECEDOR: "⚠ Parcela sem fornecedor",
    CNPJ_SEM_BOLETO: "Boleto sem CNPJ para conferir",
    CNPJ_ORIGEM_ERP: "🔗 Beneficiário preenchido pelo fornecedor do ERP",
}


@dataclass(frozen=True, slots=True)
class ItemSincronizacao:
    chave: str          # identificador da linha
    documento: int      # pagparc_documento / NF
    vencimento: date
    valor: Decimal
    cnpj: str = ""      # CNPJ/CPF do beneficiário (dígitos)


@dataclass(frozen=True, slots=True)
class ResultadoSincronizacao:
    chave: str
    status: StatusSincronizacao
    parcela: ParcelaErp | None
    detalhe: str
    conferencia_cnpj: str = ""


def _so_digitos(v: str | None) -> str:
    return re.sub(r"\D", "", v or "")


def formatar_documento(doc: str) -> str:
    d = _so_digitos(doc)
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return d


def conferir_cnpj(cnpj_boleto: str, parcela: ParcelaErp | None) -> str:
    if parcela is None:
        return ""
    if not parcela.tem_fornecedor:
        return CNPJ_SEM_FORNECEDOR
    a, b = _so_digitos(cnpj_boleto), _so_digitos(parcela.fornecedor_cnpj)
    if not a:
        return CNPJ_SEM_BOLETO
    if a == b:
        return CNPJ_CONFERE
    if len(a) == 14 and len(b) == 14 and a[:8] == b[:8]:
        return CNPJ_RAIZ
    return CNPJ_DIVERGE


def com_origem_erp(r: ResultadoSincronizacao) -> ResultadoSincronizacao:
    """Troca a conferência por 'origem ERP' (beneficiário veio do próprio fornecedor)."""
    antigo = ROTULOS_CNPJ.get(r.conferencia_cnpj, "")
    linhas = [l for l in r.detalhe.split("\n") if not antigo or l != antigo]
    linhas.append(ROTULOS_CNPJ[CNPJ_ORIGEM_ERP])
    return replace(r, detalhe="\n".join(linhas), conferencia_cnpj=CNPJ_ORIGEM_ERP)


def descrever_fornecedor(p: ParcelaErp | None) -> str:
    if p is None or not p.tem_fornecedor:
        return ""
    cnpj = formatar_documento(p.fornecedor_cnpj)
    return f"{p.fornecedor_cod} - {p.fornecedor_nome}" + (f" ({cnpj})" if cnpj else "")


def _br(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "--"


def _moeda(v: Decimal) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pago(p: ParcelaErp) -> str:
    return " (paga)" if p.pago else ""


def _valor_confere(p: ParcelaErp, valor: Decimal) -> bool:
    return abs(p.valor_documento - valor) <= _TOL or abs(p.saldo - valor) <= _TOL


def _abertas_primeiro(parcelas: list[ParcelaErp]) -> list[ParcelaErp]:
    return sorted(parcelas, key=lambda p: p.pago)  # estável: mantém a ordem original


def _com_fornecedor(it: ItemSincronizacao, status: StatusSincronizacao,
                    p: ParcelaErp, texto: str) -> ResultadoSincronizacao:
    conf = conferir_cnpj(it.cnpj, p)
    partes = [texto]
    forn = descrever_fornecedor(p)
    if forn:
        partes.append(f"Fornecedor: {forn}")
    if conf:
        partes.append(ROTULOS_CNPJ[conf])
    return ResultadoSincronizacao(it.chave, status, p, "\n".join(partes), conf)


def sincronizar(itens: list[ItemSincronizacao],
                parcelas_por_documento: dict[int, list[ParcelaErp]]) -> list[ResultadoSincronizacao]:
    usadas: set[int] = set()
    saida: list[ResultadoSincronizacao] = []

    for it in itens:
        parcelas = parcelas_por_documento.get(it.documento, [])
        if not parcelas:
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.DOC_INEXISTENTE, None,
                f"Documento {it.documento} não existe no ERP"))
            continue

        exatas = [p for p in parcelas if p.vencimento == it.vencimento and _valor_confere(p, it.valor)]
        livres = [p for p in exatas if p.cod not in usadas]

        if livres:
            escolhida = _abertas_primeiro(livres)[0]
            usadas.add(escolhida.cod)
            if escolhida.pago:
                saida.append(_com_fornecedor(
                    it, StatusSincronizacao.JA_PAGO, escolhida, "Parcela já baixada no ERP"))
            else:
                saida.append(_com_fornecedor(
                    it, StatusSincronizacao.ENCONTRADO, escolhida, f"Saldo {_moeda(escolhida.saldo)}"))
            continue

        if exatas:
            saida.append(_com_fornecedor(
                it, StatusSincronizacao.DUPLICADO, exatas[0], "Parcela já usada por outro boleto do lote"))
            continue

        mesmo_valor = _abertas_primeiro([p for p in parcelas if _valor_confere(p, it.valor)])
        if mesmo_valor:
            datas = ", ".join(f"{_br(p.vencimento)}{_pago(p)}" for p in mesmo_valor[:6])
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.DATA_DIVERGENTE, None,
                f"Vencimentos com esse valor: {datas}"))
            continue

        mesma_data = _abertas_primeiro([p for p in parcelas if p.vencimento == it.vencimento])
        if mesma_data:
            valores = ", ".join(f"{_moeda(p.valor_documento)}{_pago(p)}" for p in mesma_data[:4])
            saida.append(ResultadoSincronizacao(
                it.chave, StatusSincronizacao.VALOR_DIVERGENTE, None,
                f"Valor no ERP: {valores}"))
            continue

        saida.append(ResultadoSincronizacao(
            it.chave, StatusSincronizacao.NAO_ENCONTRADO, None,
            f"{len(parcelas)} parcela(s) no documento, nenhuma confere"))
    return saida
