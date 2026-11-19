
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BarcodeReading:
    valor: str
    formato: str


class BarcodeReader(Protocol):

    def ler(self, imagem: Path) -> tuple[BarcodeReading, ...]:
        ...
