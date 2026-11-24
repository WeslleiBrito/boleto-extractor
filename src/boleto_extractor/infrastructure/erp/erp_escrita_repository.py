# boleto_extractor/infrastructure/erp/erp_escrita_repository.py
"""
Escrita no ERP restrita a pagar_parcelas.pagparc_obs.
Fornecedor ausente é apenas LOCALIZADO (por CNPJ) e registrado no texto da observação.
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger(__name__)

MARCA_INI = "[SYNC-BOLETO]"
MARCA_FIM = "[/SYNC-BOLETO]"
_RE_BLOCO = re.compile(re.escape(MARCA_INI) + r".*?" + re.escape(MARCA_FIM) + r"\n?", re.DOTALL)
_CNPJ_SQL = (
    "REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(f.forn_cnpj,''),'.',''),'/',''),'-',''),' ','')"
)


def so_digitos(valor: str | None) -> str:
    return re.sub(r"\D", "", valor or "")


def _latin1(texto: str) -> str:
    return texto.encode("latin-1", errors="replace").decode("latin-1")


@dataclass(frozen=True, slots=True)
class Fornecedor:
    codigo: int
    nome: str
    criterio: str  # "CNPJ exato" | "mesma raiz de CNPJ"


@dataclass(frozen=True, slots=True)
class ResultadoObservacao:
    pagparc_cod: int
    ok: bool
    fornecedor: Fornecedor | None = None
    fornecedor_ausente: bool = False
    erro: str = ""


class ErpEscritaRepository:
    def __init__(self, conexao_factory: Callable[[], object]) -> None:
        """conexao_factory: retorna conexão DB-API (pymysql / mysql-connector, paramstyle %s)."""
        self._factory = conexao_factory
        self._cache: dict[str, Fornecedor | None] = {}

    # ---------------- Fornecedor (somente leitura) ----------------
    def _buscar_fornecedor(self, cur, cnpj: str) -> Fornecedor | None:
        cnpj = so_digitos(cnpj)
        if len(cnpj) != 14:
            return None
        if cnpj in self._cache:
            return self._cache[cnpj]

        cur.execute(
            f"""SELECT f.forn_cod, f.forn_nome FROM fornecedor f
                 WHERE {_CNPJ_SQL} = %s
                 ORDER BY (f.forn_ativo = 'S') DESC, f.forn_cod LIMIT 1""",
            (cnpj,),
        )
        row = cur.fetchone()
        forn = Fornecedor(int(row[0]), row[1] or "", "CNPJ exato") if row else None

        if forn is None:
            cur.execute(
                f"""SELECT f.forn_cod, f.forn_nome FROM fornecedor f
                     WHERE LEFT({_CNPJ_SQL}, 8) = %s
                     ORDER BY (f.forn_ativo = 'S') DESC,
                              (SUBSTRING({_CNPJ_SQL}, 9, 4) = '0001') DESC,
                              f.forn_cod LIMIT 1""",
                (cnpj[:8],),
            )
            row = cur.fetchone()
            forn = Fornecedor(int(row[0]), row[1] or "", "mesma raiz de CNPJ") if row else None

        self._cache[cnpj] = forn
        return forn

    # ---------------- Observação ----------------
    @staticmethod
    def mesclar(obs_atual: str | None, bloco: str) -> str:
        base = _RE_BLOCO.sub("", obs_atual or "").rstrip()
        novo = f"{MARCA_INI}\n{bloco.strip()}\n{MARCA_FIM}"
        return f"{base}\n{novo}" if base else novo

    def gravar_observacao(self, pagparc_cod: int, bloco: str, cnpj: str | None) -> ResultadoObservacao:
        conn = self._factory()
        cur = conn.cursor()
        try:
            cur.execute(
                """SELECT pp.pagparc_obs, pp.pagparc_fornecedor, p.pag_fornecedor
                     FROM pagar_parcelas pp
                LEFT JOIN pagar p ON p.pag_cod = pp.pagparc_conta
                    WHERE pp.pagparc_cod = %s
                      FOR UPDATE""",
                (pagparc_cod,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return ResultadoObservacao(pagparc_cod, False, erro="Parcela não encontrada")

            obs_atual, forn_parc, forn_pagar = row
            ausente = not forn_parc and not forn_pagar
            forn = None
            if ausente:
                forn = self._buscar_fornecedor(cur, cnpj or "")
                if forn:
                    bloco += (f"\nFornecedor sugerido: {forn.codigo} - {forn.nome} "
                              f"({forn.criterio}) — vincular manualmente")
                elif so_digitos(cnpj):
                    bloco += f"\nFornecedor NÃO cadastrado para o CNPJ {so_digitos(cnpj)}"

            cur.execute(
                "UPDATE pagar_parcelas SET pagparc_obs = %s WHERE pagparc_cod = %s",
                (_latin1(self.mesclar(obs_atual, bloco)), pagparc_cod),
            )
            conn.commit()
            return ResultadoObservacao(pagparc_cod, True, forn, ausente)
        except Exception as exc:  # noqa: BLE001
            conn.rollback()
            log.exception("Falha ao gravar observação da parcela %s", pagparc_cod)
            return ResultadoObservacao(pagparc_cod, False, erro=str(exc))
        finally:
            cur.close()
            conn.close()
