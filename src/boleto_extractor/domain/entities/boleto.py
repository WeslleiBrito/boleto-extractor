from dataclasses import dataclass

from boleto_extractor.domain.entities.boleto_details import BoletoDetails
from boleto_extractor.domain.enums.boleto_type import BoletoType


@dataclass(frozen=True, slots=True)
class Boleto:
    tipo: BoletoType
    linha_digitavel: str | None = None
    codigo_barras: str | None = None
    detalhes: BoletoDetails | None = None

    def __post_init__(self) -> None:
        if not self.linha_digitavel and not self.codigo_barras:
            raise ValueError(
                "O boleto precisa possuir linha digitável ou código de barras."
            )

        if self.linha_digitavel and not self.linha_digitavel.isdigit():
            raise ValueError("A linha digitável deve conter somente números.")

        if self.codigo_barras and not self.codigo_barras.isdigit():
            raise ValueError("O código de barras deve conter somente números.")
