from dataclasses import dataclass
from typing import Protocol

from boleto_extractor.core.types import ImageArray


@dataclass(frozen=True, slots=True)
class BarcodeReading:
    valor: str
    formato: str


class BarcodeReader(Protocol):
    """Contrato para leitores de código de barras."""

    def ler(self, imagem: ImageArray) -> tuple[BarcodeReading, ...]:
        ...
