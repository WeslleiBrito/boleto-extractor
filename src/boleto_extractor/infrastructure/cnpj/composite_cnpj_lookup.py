"""Lookup de CNPJ composto: tenta o OpenCNPJ primeiro e usa o BigQuery como reserva.
O cliente BigQuery pode ser trocado em tempo de execução (via configurações)."""
from __future__ import annotations

import logging
import threading

from boleto_extractor.application.ports.cnpj_lookup import CnpjLookup
from boleto_extractor.domain.entities.beneficiario import DadosEmpresa

log = logging.getLogger(__name__)


class CompositeCnpjLookup:
    """Implementa o Protocol CnpjLookup. Nunca lança exceção: retorna None em falha."""

    def __init__(self, primario: CnpjLookup, bigquery: CnpjLookup | None = None) -> None:
        self._primario = primario
        self._bigquery = bigquery
        self._lock = threading.Lock()  # set_bigquery roda na thread da UI; consultar, em workers
        self._cache: dict[str, DadosEmpresa] = {}

    def set_bigquery(self, cliente: CnpjLookup | None) -> None:
        with self._lock:
            self._bigquery = cliente
        log.info("BigQuery %s.", "ativado" if cliente else "desativado")

    def consultar(self, cnpj: str) -> DadosEmpresa | None:
        cnpj = "".join(c for c in cnpj if c.isdigit())
        if not cnpj:
            return None

        with self._lock:
            if cnpj in self._cache:
                return self._cache[cnpj]
            bigquery = self._bigquery

        for nome, fonte in (("OpenCNPJ", self._primario), ("BigQuery", bigquery)):
            if fonte is None:
                continue
            if nome == "BigQuery" and not getattr(fonte, "disponivel", True):
                continue
            try:
                dados = fonte.consultar(cnpj)
            except Exception as exc:  # noqa: BLE001 - contrato: nunca lançar
                log.warning("%s falhou para %s: %s", nome, cnpj, exc)
                dados = None
            if dados is not None:
                with self._lock:
                    self._cache[cnpj] = dados
                return dados

        return None
