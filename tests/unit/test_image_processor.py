
import numpy as np
import pytest

from boleto_extractor.core.exceptions import DocumentLoadError
from boleto_extractor.infrastructure.image.image_processor import ImageProcessor


@pytest.fixture
def imagem() -> np.ndarray:
    return np.full((1000, 1500, 3), 255, dtype=np.uint8)


def test_deve_validar_imagem(imagem: np.ndarray) -> None:
    processor = ImageProcessor()

    processor.validar(imagem)


def test_deve_redimensionar_imagem(imagem: np.ndarray) -> None:
    processor = ImageProcessor()

    resultado = processor.redimensionar(
        imagem,
        largura_maxima=1000,
    )

    assert resultado.shape == (666, 1000, 3)


def test_deve_converter_para_escala_cinza(
    imagem: np.ndarray,
) -> None:
    processor = ImageProcessor()

    resultado = processor.escala_cinza(imagem)

    assert resultado.ndim == 2
    assert resultado.dtype == np.uint8


def test_deve_binarizar_imagem(imagem: np.ndarray) -> None:
    processor = ImageProcessor()

    resultado = processor.binarizar(imagem)

    assert resultado.ndim == 2
    assert set(np.unique(resultado)).issubset({0, 255})


def test_nao_deve_aceitar_imagem_vazia() -> None:
    processor = ImageProcessor()

    imagem = np.array([], dtype=np.uint8)

    with pytest.raises(DocumentLoadError):
        processor.validar(imagem)
