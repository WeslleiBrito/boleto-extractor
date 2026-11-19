
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OCRText:
    texto: str
    confianca: float
    coordenadas: tuple[tuple[float, float], ...]


class OCREngine(Protocol):

    def reconhecer(self, imagem: Path) -> tuple[OCRText, ...]:
        ...
