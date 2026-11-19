
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from boleto_extractor.core.types import ImageArray


class DocumentLoader(Protocol):
    """Contrato para carregamento de documentos."""

    def carregar(self, arquivo: Path) -> Iterator[ImageArray]:
        """
        Carrega um documento e disponibiliza suas páginas como imagens.

        Cada página é disponibilizada individualmente na memória.
        """
        ...
