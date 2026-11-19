
from pathlib import Path

import cv2
import numpy as np
import pymupdf
import pytest

from boleto_extractor.core.exceptions import DocumentLoadError
from boleto_extractor.infrastructure.pdf.local_document_loader import (
    LocalDocumentLoader,
)


def test_deve_carregar_imagem_png(tmp_path: Path) -> None:
    arquivo = tmp_path / "boleto.png"

    imagem_original = np.zeros((200, 300, 3), dtype=np.uint8)

    sucesso, buffer = cv2.imencode(".png", imagem_original)

    assert sucesso

    buffer.tofile(str(arquivo))

    loader = LocalDocumentLoader()

    paginas = tuple(loader.carregar(arquivo))

    assert len(paginas) == 1
    assert paginas[0].shape == (200, 300, 3)
    assert paginas[0].dtype == np.uint8


def test_deve_carregar_pdf_com_duas_paginas(tmp_path: Path) -> None:
    arquivo = tmp_path / "boleto.pdf"

    documento = pymupdf.open()

    documento.new_page(width=300, height=200)
    documento.new_page(width=300, height=200)

    documento.save(arquivo)
    documento.close()

    loader = LocalDocumentLoader(dpi=72)

    paginas = tuple(loader.carregar(arquivo))

    assert len(paginas) == 2
    assert paginas[0].shape == (200, 300, 3)


def test_deve_rejeitar_arquivo_inexistente(tmp_path: Path) -> None:
    arquivo = tmp_path / "inexistente.pdf"

    loader = LocalDocumentLoader()

    with pytest.raises(DocumentLoadError):
        tuple(loader.carregar(arquivo))


def test_deve_rejeitar_formato_nao_suportado(tmp_path: Path) -> None:
    arquivo = tmp_path / "documento.txt"
    arquivo.write_text("teste")

    loader = LocalDocumentLoader()

    with pytest.raises(DocumentLoadError):
        tuple(loader.carregar(arquivo))
