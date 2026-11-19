
import numpy as np
import pytest

from boleto_extractor.core.exceptions import BarcodeReadingError
from boleto_extractor.infrastructure.barcode.zxing_barcode_reader import (
    ZXingBarcodeReader,
)


@pytest.fixture
def leitor() -> ZXingBarcodeReader:
    return ZXingBarcodeReader()


def test_deve_retornar_tupla_vazia_quando_nao_encontrar_codigo(
    leitor: ZXingBarcodeReader,
) -> None:
    imagem = np.full((500, 800, 3), 255, dtype=np.uint8)

    resultado = leitor.ler(imagem)

    assert resultado == ()


def test_nao_deve_aceitar_imagem_vazia(
    leitor: ZXingBarcodeReader,
) -> None:
    imagem = np.array([], dtype=np.uint8)

    with pytest.raises(BarcodeReadingError):
        leitor.ler(imagem)


def test_nao_deve_aceitar_imagem_com_tipo_invalido(
    leitor: ZXingBarcodeReader,
) -> None:
    imagem = np.zeros((100, 100, 3), dtype=np.float32)

    with pytest.raises(BarcodeReadingError):
        leitor.ler(imagem)


def test_nao_deve_aceitar_imagem_sem_tres_canais(
    leitor: ZXingBarcodeReader,
) -> None:
    imagem = np.zeros((100, 100), dtype=np.uint8)

    with pytest.raises(BarcodeReadingError):
        leitor.ler(imagem)
