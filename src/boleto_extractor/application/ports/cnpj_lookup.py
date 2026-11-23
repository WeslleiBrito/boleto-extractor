from typing import Protocol

from boleto_extractor.domain.entities.beneficiario import DadosEmpresa


class CnpjLookup(Protocol):
    """Consulta dados de um CNPJ. Retorna None em qualquer falha, sem lançar exceção."""

    def consultar(self, cnpj: str) -> DadosEmpresa | None:
        ...
