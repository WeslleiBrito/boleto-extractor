from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BoletoDetails:
    """Informações decodificadas a partir do código de barras."""

    valor: Decimal | None = None
    vencimento: date | None = None
    vencimento_estimado: bool = False
    banco_codigo: str | None = None
    banco_nome: str | None = None
    segmento: str | None = None
    empresa_id: str | None = None
    campo_livre: str = ""
    observacoes: tuple[str, ...] = ()

    @property
    def emissor(self) -> str:
        if self.banco_nome:
            return self.banco_nome
        if self.segmento:
            return self.segmento
        return self.banco_codigo or ""
