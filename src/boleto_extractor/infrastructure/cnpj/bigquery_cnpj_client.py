from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Any, Callable, Iterable

TABELA_PADRAO = "opencnpj-bigquery.public.receita"
_PADRAO_CNPJ = re.compile(r"^[A-Z0-9]{12}\d{2}$")


def normalizar_cnpj(valor: str | None) -> str:
    """Remove máscara e aceita CNPJ numérico ou alfanumérico (Receita, jul/2026)."""
    limpo = re.sub(r"[^A-Z0-9]", "", (valor or "").upper())
    return limpo if _PADRAO_CNPJ.match(limpo) else ""


class LimiteExcedido(RuntimeError):
    def __init__(self, gb: float, limite: int) -> None:
        super().__init__(
            f"Consulta estimada em {gb:.2f} GB, acima do limite de {limite} GB. "
            f"Aumente o limite para pelo menos {int(gb) + 1} GB."
        )
        self.gb = gb


@dataclass(frozen=True)
class DadosCnpjBigQuery:
    cnpj: str
    razao_social: str
    nome_fantasia: str
    situacao: str
    municipio: str = ""
    uf: str = ""
    cnae_principal: str = ""
    fonte: str = "BigQuery"


class BigQueryCnpjClient:
    """Consulta CNPJ na base pública OpenCNPJ via BigQuery."""

    def __init__(self, obter_config: Callable[[], dict[str, Any]]) -> None:
        self._obter_config = obter_config
        self._cliente = None
        self._assinatura: tuple | None = None
        self._cache: dict[str, DadosCnpjBigQuery | None] = {}
        self._lock = threading.Lock()
        self.ultimo_gb: float = 0.0

    # ---------------- Público ----------------
    def ativo(self) -> bool:
        cfg = self._obter_config()
        return bool(cfg.get("bq_ativo") and cfg.get("bq_credencial"))

    def consultar(self, cnpj: str) -> DadosCnpjBigQuery | None:
        cnpj = normalizar_cnpj(cnpj)
        if not cnpj:
            return None
        return self.consultar_lote([cnpj]).get(cnpj)

    def consultar_lote(self, cnpjs: Iterable[str]) -> dict[str, DadosCnpjBigQuery | None]:
        """Uma única consulta para vários CNPJs."""
        limpos = {c for c in (normalizar_cnpj(x) for x in cnpjs) if c}
        if not limpos or not self.ativo():
            return {}

        with self._lock:
            faltando = sorted(c for c in limpos if c not in self._cache)
            if faltando:
                encontrados = self._consultar_bq(faltando)
                for c in faltando:
                    self._cache[c] = encontrados.get(c)
            return {c: self._cache[c] for c in limpos}

    # ---------------- Interno ----------------
    @staticmethod
    def _tabela(cfg: dict[str, Any]) -> str:
        tabela = (cfg.get("bq_tabela") or TABELA_PADRAO).strip().strip("`")
        if not re.fullmatch(r"[\w\-]+\.[\w\-]+\.[\w\-]+", tabela):
            raise ValueError(f"Nome de tabela inválido: {tabela}")
        return tabela

    @staticmethod
    def _limite_gb(cfg: dict[str, Any]) -> int:
        return int(cfg.get("bq_limite_gb") or 5)

    def _cliente_bq(self, cfg: dict[str, Any]):
        from google.cloud import bigquery
        from google.oauth2 import service_account

        assinatura = (cfg["bq_credencial"], cfg.get("bq_projeto"), self._tabela(cfg))
        if self._cliente is None or assinatura != self._assinatura:
            cred = service_account.Credentials.from_service_account_file(cfg["bq_credencial"])
            self._cliente = bigquery.Client(
                credentials=cred, project=cfg.get("bq_projeto") or cred.project_id
            )
            self._assinatura = assinatura
            self._cache.clear()
        return self._cliente

    def _estimar_gb(self, cliente, sql: str, params: list) -> float:
        """Dry-run: calcula os bytes sem executar e sem cobrar."""
        from google.cloud import bigquery

        job = cliente.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=params, dry_run=True, use_query_cache=False
            ),
        )
        return (job.total_bytes_processed or 0) / 1024**3

    def _consultar_bq(self, cnpjs: list[str]) -> dict[str, DadosCnpjBigQuery]:
        from google.cloud import bigquery

        cfg = self._obter_config()
        cliente = self._cliente_bq(cfg)

        sql = f"""
            SELECT cnpj, razao_social, nome_fantasia, situacao_cadastral,
                   uf, municipio, cnae_principal
            FROM `{self._tabela(cfg)}`
            WHERE cnpj IN UNNEST(@cnpjs)
        """
        params = [bigquery.ArrayQueryParameter("cnpjs", "STRING", cnpjs)]

        limite = self._limite_gb(cfg)
        self.ultimo_gb = self._estimar_gb(cliente, sql, params)
        if self.ultimo_gb > limite:
            raise LimiteExcedido(self.ultimo_gb, limite)

        job_config = bigquery.QueryJobConfig(
            query_parameters=params,
            maximum_bytes_billed=max(1, limite) * 1024**3,
            use_query_cache=True,
        )
        resultado: dict[str, DadosCnpjBigQuery] = {}
        for r in cliente.query(sql, job_config=job_config).result():
            cnpj = normalizar_cnpj(r.cnpj)
            if not cnpj or cnpj in resultado:
                continue
            resultado[cnpj] = DadosCnpjBigQuery(
                cnpj=cnpj,
                razao_social=(r.razao_social or "").strip(),
                nome_fantasia=(r.nome_fantasia or "").strip(),
                situacao=(r.situacao_cadastral or "").strip().upper(),
                municipio=(r.municipio or "").strip(),
                uf=(r.uf or "").strip().upper(),
                cnae_principal=(r.cnae_principal or "").strip(),
            )
        return resultado
