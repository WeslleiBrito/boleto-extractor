from __future__ import annotations

import logging
from typing import Any, Protocol

log = logging.getLogger(__name__)


class CnpjLookup(Protocol):
    def consultar(self, cnpj: str) -> Any | None: ...


class FallbackCnpjLookup:
    """Tenta cada fonte em ordem; a primeira que responder vence."""

    def __init__(self, *fontes: CnpjLookup) -> None:
        self._fontes = fontes

    def consultar(self, cnpj: str) -> Any | None:
        for fonte in self._fontes:
            if hasattr(fonte, "ativo") and not fonte.ativo():
                continue
            try:
                resultado = fonte.consultar(cnpj)
                if resultado:
                    return resultado
            except Exception as exc:  # uma fonte falhar não derruba a extração
                log.warning("Fonte %s falhou para %s: %s", type(fonte).__name__, cnpj, exc)
        return None

    def __getattr__(self, nome: str):
        # Repassa outros métodos (ex.: fechar sessão) para a fonte principal
        return getattr(self._fontes[0], nome)
