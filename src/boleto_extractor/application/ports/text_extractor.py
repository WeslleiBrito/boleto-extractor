from pathlib import Path
from typing import Protocol


class TextExtractor(Protocol):
    """Contrato para extração de texto por página. Nunca deve lançar exceção."""

    def extrair_paginas(self, arquivo: Path) -> tuple[str, ...]:
        ...
